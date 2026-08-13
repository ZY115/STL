"""Resumable single-cell runner for the frozen D38 Gold-cost matrix."""

from __future__ import annotations

import copy
import csv
import hashlib
import json
import math
import os
import platform
import re
import subprocess
import time
from importlib import metadata
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

import torch
import yaml
from omnisafe.utils.config import Config, check_all_configs, get_default_kwargs_yaml
from omnisafe.utils.tools import recursive_check_config

import safety_stl.omnisafe_env  # noqa: F401  # registers project environments
from safety_stl.diagnostic_algorithm import DiagnosticPPOLag


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROTOCOL = REPOSITORY_ROOT / "configs/stage2_gold_diagnostic/protocol.yaml"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    if not isinstance(value, Mapping):
        raise ValueError(f"configuration must be a mapping: {path}")
    return dict(value)


def _read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, Mapping):
        raise ValueError(f"JSON must be an object: {path}")
    return dict(value)


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(temporary, path)


def _next_attempt_directory(cell_root: Path) -> tuple[int, Path]:
    attempts_root = cell_root / "attempts"
    attempt_numbers = []
    if attempts_root.is_dir():
        for path in attempts_root.iterdir():
            match = re.fullmatch(r"attempt-(\d{4})", path.name)
            if path.is_dir() and match:
                attempt_numbers.append(int(match.group(1)))
    attempt = max(attempt_numbers, default=0) + 1
    return attempt, attempts_root / f"attempt-{attempt:04d}"


def _nested(value: Mapping[str, Any], dotted: str) -> float:
    current: Any = value
    for part in dotted.split("."):
        current = current[part]
    return float(current)


def load_diagnostic_contract(
    protocol_path: Path = DEFAULT_PROTOCOL,
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    protocol_path = protocol_path.resolve()
    protocol = _read_yaml(protocol_path)
    if protocol.get("authority") != "D38" or protocol.get("status") != "frozen_before_diagnostic_training":
        raise ValueError("Gold diagnostic protocol is not frozen under D38")
    seeds = [int(seed) for seed in protocol["training_seeds"]]
    if len(seeds) != 3 or len(set(seeds)) != 3:
        raise ValueError("D38 requires three distinct diagnostic seeds")
    pilot_seeds = {int(seed) for seed in protocol["seed_guard"]["stage1_pilot_seeds"]}
    if pilot_seeds.intersection(seeds):
        raise ValueError("Gold diagnostic seeds overlap Stage I pilot seeds")
    conditions = list(protocol["conditions"])
    if len(conditions) != 5 or len({row["condition_id"] for row in conditions}) != 5:
        raise ValueError("D38 diagnostic matrix must contain five conditions")
    budget_path = (REPOSITORY_ROOT / protocol["budget_source"]["path"]).resolve()
    budgets = _read_json(budget_path) if budget_path.is_file() else {}
    if budgets and budgets.get("status") != "frozen_before_gold_diagnostic_training":
        raise ValueError("Gold diagnostic budgets have an invalid status")
    return protocol, budgets


def resolve_condition(
    protocol: Mapping[str, Any],
    budgets: Mapping[str, Any],
    condition_id: str,
) -> Dict[str, Any]:
    records = [row for row in protocol["conditions"] if row["condition_id"] == condition_id]
    if len(records) != 1:
        raise ValueError(f"unknown diagnostic condition: {condition_id}")
    result = dict(records[0])
    if "cost_limit_from" in result:
        if not budgets:
            raise FileNotFoundError(
                "run and evaluate all matched task-only controls, then freeze C0/C1 budgets",
            )
        result["cost_limit"] = _nested(budgets, str(result.pop("cost_limit_from")))
    cost_limit = float(result["cost_limit"])
    if not math.isfinite(cost_limit) or cost_limit < 0:
        raise ValueError("diagnostic cost limit must be finite and non-negative")
    return result


def build_omnisafe_config(
    protocol: Mapping[str, Any],
    condition: Mapping[str, Any],
    *,
    seed: int,
    log_dir: Path,
    dry_run: bool,
) -> Config:
    stage1_path = (REPOSITORY_ROOT / protocol["omnisafe"]["source_protocol"]).resolve()
    stage1 = _read_yaml(stage1_path)["omnisafe"]
    custom = {
        "seed": int(seed),
        "train_cfgs": copy.deepcopy(stage1["train_cfgs"]),
        "algo_cfgs": copy.deepcopy(stage1["algo_cfgs"]),
        "logger_cfgs": {**copy.deepcopy(stage1["logger_cfgs"]), "log_dir": str(log_dir)},
        "model_cfgs": copy.deepcopy(stage1["model_cfgs"]),
        "lagrange_cfgs": {
            **copy.deepcopy(stage1["lagrange_cfgs_shared"]),
            "lagrangian_multiplier_init": float(condition["lagrangian_multiplier_init"]),
            "cost_limit": float(condition["cost_limit"]),
        },
        "env_cfgs": copy.deepcopy(stage1["env_cfgs"]),
    }
    override = protocol["omnisafe"]["train_overrides"]
    custom["train_cfgs"]["total_steps"] = 10_000 if dry_run else int(override["total_steps"])
    custom["train_cfgs"]["vector_env_nums"] = int(override["vector_env_nums"])
    custom["algo_cfgs"]["steps_per_epoch"] = int(override["steps_per_epoch"])
    custom["algo_cfgs"]["update_iters"] = 1 if dry_run else int(override["update_iters"])
    custom["algo_cfgs"]["batch_size"] = int(override["batch_size"])
    custom["logger_cfgs"]["save_model_freq"] = 1 if dry_run else int(override["save_model_freq"])

    env_id = str(condition["environment_id"])
    cfgs = get_default_kwargs_yaml("PPOLag", env_id, "on-policy")
    recursive_check_config(custom, cfgs)
    cfgs.recurisve_update(custom)
    cfgs.update({"exp_increment_cfgs": custom})
    cfgs.recurisve_update(
        {
            "exp_name": f"DiagnosticPPOLag-{{{env_id}}}",
            "env_id": env_id,
            "algo": "PPOLag",
        },
    )
    cfgs.train_cfgs.recurisve_update(
        {"epochs": cfgs.train_cfgs.total_steps // cfgs.algo_cfgs.steps_per_epoch},
    )
    check_all_configs(cfgs, "on-policy")
    return cfgs


def _progress(path: Path) -> List[Dict[str, float]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [
            {key: float(value) for key, value in row.items() if value not in (None, "")}
            for row in csv.DictReader(handle)
        ]


def _final_checkpoint(run_dir: Path) -> Path:
    candidates = []
    for path in (run_dir / "torch_save").glob("epoch-*.pt"):
        match = re.fullmatch(r"epoch-(\d+)\.pt", path.name)
        if match:
            candidates.append((int(match.group(1)), path))
    if not candidates:
        raise FileNotFoundError(f"no checkpoint under {run_dir}")
    return max(candidates)[1]


def _git_commit() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(REPOSITORY_ROOT),
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def run_diagnostic_cell(
    condition_id: str,
    seed: int,
    output_dir: Path,
    *,
    protocol_path: Path = DEFAULT_PROTOCOL,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Train one immutable D38 cell; evaluation is a separate gated operation."""

    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    protocol_path = protocol_path.resolve()
    protocol, budgets = load_diagnostic_contract(protocol_path)
    if int(seed) not in [int(value) for value in protocol["training_seeds"]] and not dry_run:
        raise ValueError("seed is outside the frozen D38 list")
    condition = resolve_condition(protocol, budgets, condition_id)
    suffix = "dry-run" if dry_run else f"seed-{seed}"
    cell_root = output_dir.resolve() / condition_id / suffix
    latest_manifest_path = cell_root / "manifest.json"
    if latest_manifest_path.is_file():
        existing = _read_json(latest_manifest_path)
        if existing.get("status") == "success":
            return dict(existing["summary"])
    attempt_number, cell_dir = _next_attempt_directory(cell_root)
    manifest_path = cell_dir / "manifest.json"

    def write_manifest(value: Mapping[str, Any]) -> None:
        _write_json(manifest_path, value)
        _write_json(latest_manifest_path, value)

    budget_path = (REPOSITORY_ROOT / protocol["budget_source"]["path"]).resolve()
    running = {
        "schema_version": 1,
        "status": "running",
        "scope": "D38_bounded_diagnostic_training_no_confirmatory_claim",
        "condition": condition,
        "seed": int(seed),
        "dry_run": bool(dry_run),
        "attempt": attempt_number,
        "attempt_dir": str(cell_dir),
        "git_commit": _git_commit(),
        "protocol_sha256": sha256_file(protocol_path),
        "budget_sha256": sha256_file(budget_path) if budget_path.is_file() else None,
        "runner_sha256": sha256_file(Path(__file__).resolve()),
        "algorithm_sha256": sha256_file(REPOSITORY_ROOT / "src/safety_stl/diagnostic_algorithm.py"),
        "adapter_sha256": sha256_file(REPOSITORY_ROOT / "src/safety_stl/omnisafe_adapter.py"),
        "environment_sha256": sha256_file(REPOSITORY_ROOT / "src/safety_stl/omnisafe_env.py"),
        "started_at_unix": time.time(),
    }
    write_manifest(running)
    started = time.monotonic()
    try:
        cfgs = build_omnisafe_config(
            protocol,
            condition,
            seed=seed,
            log_dir=cell_dir / "training",
            dry_run=dry_run,
        )
        if not torch.cuda.is_available():
            raise RuntimeError("D38 diagnostic requires CUDA")
        torch.cuda.set_device(0)
        torch.cuda.reset_peak_memory_stats(0)
        algorithm = DiagnosticPPOLag(str(condition["environment_id"]), cfgs)
        run_dir = Path(algorithm.logger.log_dir).resolve()
        result = algorithm.learn()
        torch.cuda.synchronize(0)
        elapsed = time.monotonic() - started
        progress_path = run_dir / "progress.csv"
        rows = _progress(progress_path)
        checkpoint = _final_checkpoint(run_dir)
        required = set(protocol["required_epoch_diagnostics"])
        mapping = {
            "positive_cost_step_fraction": "Diagnostics/PositiveCostStepFraction",
            "cost_value_rmse_and_means": "Diagnostics/CostValueRMSE",
            "reward_advantage_std": "Diagnostics/RewardAdvStdRaw",
            "cost_advantage_actor_scale_std": "Diagnostics/CostAdvStdActorScale",
            "actor_reward_gradient_norm": "Diagnostics/ActorRewardGradientNorm",
            "actor_cost_gradient_norm": "Diagnostics/ActorCostGradientNorm",
            "lagrange_multiplier": "Metrics/LagrangeMultiplier",
            "actor_learning_rate": "Train/LR",
            "triggers": "Metrics/STLTriggers",
            "misses": "Metrics/STLDeadlineViolations",
            "goal_events": "Metrics/GoalEvents",
        }
        required_columns = {mapping[name] for name in required}
        learner_cost = str(condition["learner_cost"])
        if learner_cost == "identically_zero":
            routing_exact = all(
                math.isclose(row["Metrics/SelectedAlgorithmCost"], 0.0, abs_tol=1.0e-9)
                for row in rows
            )
        elif learner_cost == "c0_binary_event":
            routing_exact = all(
                math.isclose(
                    row["Metrics/SelectedAlgorithmCost"],
                    row["Metrics/STLCost"],
                    abs_tol=1.0e-9,
                )
                for row in rows
            )
        elif learner_cost == "c1_causal_dense_surrogate":
            routing_exact = all(
                math.isclose(
                    row["Metrics/SelectedAlgorithmCost"],
                    row["Metrics/STLDenseCost"],
                    abs_tol=1.0e-9,
                )
                for row in rows
            )
        else:
            raise ValueError(f"unknown diagnostic learner cost: {learner_cost}")
        checks = {
            "expected_epochs": len(rows) == int(cfgs.train_cfgs.epochs),
            "all_finite": all(math.isfinite(value) for row in rows for value in row.values()),
            "diagnostics_present": all(required_columns.issubset(row) for row in rows),
            "positive_stl_observed": any(row["Metrics/STLCost"] > 0 for row in rows),
            "checkpoint_written": checkpoint.is_file(),
            "lr_floor_respected": all(row["Train/LR"] >= 3.0e-5 - 1.0e-12 for row in rows),
            "selected_cost_routing_exact": routing_exact,
        }
        if not all(checks.values()):
            raise AssertionError(f"Gold diagnostic artifact checks failed: {checks}")
        summary = {
            "condition_id": condition_id,
            "seed": int(seed),
            "dry_run": bool(dry_run),
            "run_dir": str(run_dir),
            "progress": {"path": str(progress_path), "sha256": sha256_file(progress_path)},
            "checkpoint": {"path": str(checkpoint), "sha256": sha256_file(checkpoint)},
            "epochs": len(rows),
            "elapsed_seconds": elapsed,
            "transitions_per_second": int(cfgs.train_cfgs.total_steps) / elapsed,
            "peak_gpu_memory_allocated_bytes": int(torch.cuda.max_memory_allocated(0)),
            "learn_return": [float(value) for value in result],
            "checks": checks,
            "platform": {
                "python": platform.python_version(),
                "torch": torch.__version__,
                "omnisafe": metadata.version("omnisafe"),
            },
        }
        if not dry_run:
            from safety_stl.evaluation import (  # pylint: disable=import-outside-toplevel
                evaluate_checkpoint,
                write_evaluation_outputs,
            )

            count = int(protocol["scale"]["screening_evaluation_episodes_per_seed"])
            seed_start = int(protocol["scale"]["screening_evaluation_seed_start"])
            evaluation_seeds = list(range(seed_start, seed_start + count))
            save_trajectories = str(condition["learner_cost"]) == "identically_zero"
            evaluation_summary, episodes, trajectories = evaluate_checkpoint(
                run_dir,
                checkpoint.name,
                evaluation_seeds,
                max_episode_steps=1000,
                deterministic=True,
                save_trajectories=save_trajectories,
            )
            evaluation_paths = write_evaluation_outputs(
                cell_dir / "evaluation",
                evaluation_summary,
                episodes,
                trajectories,
            )
            summary["evaluation"] = {
                "episode_count": len(episodes),
                "paired_seeds": evaluation_seeds,
                "gold_oracle_agreement": bool(
                    evaluation_summary["aggregate"]["all_online_oracle_agree"],
                ),
                "rtamt_max_robustness_difference": float(
                    evaluation_summary["aggregate"]["rtamt_max_robustness_difference"],
                ),
                "artifacts": {
                    name: {"path": path, "sha256": sha256_file(Path(path))}
                    for name, path in evaluation_paths.items()
                },
            }
    except BaseException as error:
        write_manifest(
            {
                **running,
                "status": "interrupted" if isinstance(error, KeyboardInterrupt) else "failed",
                "failed_at_unix": time.time(),
                "error_type": type(error).__name__,
                "error": str(error),
            },
        )
        raise
    write_manifest(
        {**running, "status": "success", "completed_at_unix": time.time(), "summary": summary},
    )
    return summary


__all__ = [
    "build_omnisafe_config",
    "_next_attempt_directory",
    "load_diagnostic_contract",
    "resolve_condition",
    "run_diagnostic_cell",
]
