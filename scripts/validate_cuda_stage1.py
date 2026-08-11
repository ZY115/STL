#!/usr/bin/env python3
"""Validate CUDA from PyTorch through the Stage I PPOLag positive-cost path."""

from __future__ import annotations

import argparse
import copy
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence

import torch
import yaml
from omnisafe.envs.core import make

from run_omnisafe_integration_smoke import git_revision, run_ppo_update, sha256_file
from run_on_policy_positive_cost_sanity import evaluate_acceptance
from safety_stl.omnisafe_env import STL_COST_ENV_ID


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPOSITORY_ROOT / "configs" / "cuda_validation.yaml"
DEFAULT_OUTPUT = REPOSITORY_ROOT / "results" / "cuda_validation"


def load_mapping(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle)
    if not isinstance(loaded, Mapping):
        raise ValueError(f"expected a YAML mapping: {path}")
    return dict(loaded)


def installed_version(distribution: str) -> str:
    try:
        return metadata.version(distribution)
    except metadata.PackageNotFoundError:
        return "not-installed"


def driver_record() -> Dict[str, str]:
    query = (
        "name,uuid,driver_version,memory.total,memory.free,compute_mode,temperature.gpu"
    )
    completed = subprocess.run(
        ["nvidia-smi", f"--query-gpu={query}", "--format=csv,noheader,nounits"],
        check=True,
        capture_output=True,
        text=True,
    )
    values = [value.strip() for value in completed.stdout.strip().split(",")]
    keys = (
        "name",
        "uuid",
        "driver_version",
        "memory_total_mib",
        "memory_free_mib",
        "compute_mode",
        "temperature_c",
    )
    if len(values) != len(keys):
        raise RuntimeError(f"unexpected nvidia-smi output: {completed.stdout!r}")
    return dict(zip(keys, values))


def matrix_check(config: Mapping[str, Any], device: torch.device) -> Dict[str, Any]:
    torch.manual_seed(int(config["seed"]))
    torch.cuda.manual_seed_all(int(config["seed"]))
    shape = tuple(int(value) for value in config["shape"])
    left = torch.randn(shape, dtype=torch.float32)
    right = torch.randn(shape, dtype=torch.float32)
    cpu_result = left @ right
    with torch.no_grad():
        cuda_result = (left.to(device) @ right.to(device)).cpu()
    maximum_difference = float((cpu_result - cuda_result).abs().max())
    tolerance = float(config["maximum_cpu_gpu_absolute_difference"])
    return {
        "shape": list(shape),
        "maximum_cpu_gpu_absolute_difference": maximum_difference,
        "declared_tolerance": tolerance,
        "within_tolerance": maximum_difference <= tolerance,
    }


def wrapper_check(config: Mapping[str, Any], device: torch.device) -> Dict[str, Any]:
    if str(config["environment_id"]) != STL_COST_ENV_ID:
        raise ValueError("CUDA validation must use the fixed Stage I STL environment")
    environment = make(
        STL_COST_ENV_ID,
        num_envs=int(config["vector_env_nums"]),
        device=device,
        max_episode_steps=int(config["max_episode_steps"]),
    )
    try:
        observation, _ = environment.reset(seed=int(config["seed"]))
        action = torch.zeros(
            (int(config["vector_env_nums"]), 2),
            dtype=torch.float32,
            device=device,
        )
        next_observation, reward, selected_cost, _, _, info = environment.step(action)
        devices = {
            "observation": str(observation.device),
            "next_observation": str(next_observation.device),
            "reward": str(reward.device),
            "selected_cost": str(selected_cost.device),
            "native_cost": str(info["native_cost"].device),
            "stl_cost": str(info["stl_cost"].device),
        }
        return {
            "observation_shape": list(observation.shape),
            "tensor_devices": devices,
            "all_tensors_on_declared_cuda_device": all(
                value == str(device) for value in devices.values()
            ),
        }
    finally:
        environment.close()


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    config_path = args.config.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    config = load_mapping(config_path)
    if config.get("status") != "fixed_environment_validation_not_pilot_training":
        raise ValueError("CUDA validation must remain explicitly outside pilot training")

    expected = config["expected"]
    declared_workspace = str(config["cublas_workspace_config"])
    if os.environ.get("CUBLAS_WORKSPACE_CONFIG") != declared_workspace:
        raise RuntimeError(
            "CUDA deterministic training requires "
            f"CUBLAS_WORKSPACE_CONFIG={declared_workspace}",
        )
    device = torch.device(str(config["device"]))
    basic_checks = {
        "cuda_available": torch.cuda.is_available(),
        "torch_version": torch.__version__ == str(expected["torch_version"]),
        "torch_cuda_runtime": torch.version.cuda == str(expected["torch_cuda_runtime"]),
        "deterministic_cublas_workspace": (
            os.environ.get("CUBLAS_WORKSPACE_CONFIG") == declared_workspace
        ),
    }
    if not all(basic_checks.values()):
        raise AssertionError(f"basic CUDA checks failed: {basic_checks}")
    properties = torch.cuda.get_device_properties(device)
    device_checks = {
        "expected_device_name": str(expected["device_name_contains"])
        in torch.cuda.get_device_name(device),
        "expected_compute_capability": list(torch.cuda.get_device_capability(device))
        == list(expected["compute_capability"]),
        "minimum_total_memory": properties.total_memory
        >= int(expected["minimum_total_memory_bytes"]),
    }

    matrix = matrix_check(config["matrix_check"], device)
    wrapper = wrapper_check(config["wrapper_check"], device)

    training_cfg = config["positive_cost_training_check"]
    source_path = (REPOSITORY_ROOT / str(training_cfg["source_config"])).resolve()
    source = load_mapping(source_path)
    run_config = copy.deepcopy(source["ppo_lagrangian_sanity"])
    run_config["train_cfgs"]["device"] = str(training_cfg["device_override"])
    training = run_ppo_update(run_config, output_dir / "on_policy_runs")
    positive_cost_checks = evaluate_acceptance(training, source["acceptance"])

    pip_check = subprocess.run(
        [sys.executable, "-m", "pip", "check"],
        check=False,
        capture_output=True,
        text=True,
    )
    checks = {
        **basic_checks,
        **device_checks,
        "matrix_within_tolerance": bool(matrix["within_tolerance"]),
        "wrapper_tensors_on_cuda": bool(wrapper["all_tensors_on_declared_cuda_device"]),
        "positive_cost_training_gate": all(positive_cost_checks.values()),
        "pip_check": pip_check.returncode == 0,
    }
    summary = {
        "schema_version": 1,
        "milestone": str(config["milestone"]),
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": str(config["scope_note"]),
        "repository": {
            "git_head_before_milestone_commit": git_revision(),
            "config_path": str(config_path.relative_to(REPOSITORY_ROOT)),
            "config_sha256": sha256_file(config_path),
            "source_positive_cost_config": str(source_path.relative_to(REPOSITORY_ROOT)),
            "source_positive_cost_config_sha256": sha256_file(source_path),
            "environment_lock": "environment.stage1.yml",
            "environment_lock_sha256": sha256_file(REPOSITORY_ROOT / "environment.stage1.yml"),
        },
        "platform": {
            "system": platform.platform(),
            "python": platform.python_version(),
            "torch": torch.__version__,
            "torch_cuda_runtime": torch.version.cuda,
            "cublas_workspace_config": os.environ["CUBLAS_WORKSPACE_CONFIG"],
            "cudnn": torch.backends.cudnn.version(),
            "device_count": torch.cuda.device_count(),
            "device_name": torch.cuda.get_device_name(device),
            "compute_capability": list(torch.cuda.get_device_capability(device)),
            "total_memory_bytes": properties.total_memory,
            "driver": driver_record(),
            "omnisafe": installed_version("omnisafe"),
            "safety_gymnasium": installed_version("safety-gymnasium"),
        },
        "matrix_check": matrix,
        "wrapper_check": wrapper,
        "positive_cost_training": training,
        "positive_cost_checks": positive_cost_checks,
        "pip_check_output": pip_check.stdout.strip(),
        "checks": checks,
        "gate_passed": all(checks.values()),
        "full_pilot_started": False,
    }
    summary_path = output_dir / "summary.json"
    with summary_path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps({"summary": str(summary_path), "gate_passed": summary["gate_passed"]}))
    if not summary["gate_passed"]:
        raise AssertionError(f"CUDA validation failed: {checks}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
