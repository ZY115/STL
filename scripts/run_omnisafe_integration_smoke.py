#!/usr/bin/env python3
"""Run the bounded Stage I OmniSafe wrapper/integration completion gate."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import subprocess
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence

import omnisafe
import torch
import yaml
from omnisafe.envs.core import make, support_envs

from safety_stl.omnisafe_env import REGISTERED_ENV_IDS, STL_COST_ENV_ID
from safety_stl.visualization import ScriptedApproachEscapeController


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPOSITORY_ROOT / "configs" / "omnisafe_integration_smoke.yaml"
DEFAULT_OUTPUT = REPOSITORY_ROOT / "results" / "integration_smoke"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def installed_version(distribution: str) -> str:
    try:
        return metadata.version(distribution)
    except metadata.PackageNotFoundError:
        return "not-installed"


def git_revision() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def load_config(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, Mapping):
        raise ValueError("smoke configuration must be a mapping")
    required = {"conditions", "positive_stl_cost_probe", "ppo_lagrangian_smoke"}
    missing = sorted(required - set(config))
    if missing:
        raise ValueError(f"smoke configuration is missing: {', '.join(missing)}")
    return dict(config)


def run_positive_cost_probe(config: Mapping[str, Any]) -> Dict[str, Any]:
    """Use the existing validation controller to force one real positive STL cost."""

    environment_id = str(config["environment_id"])
    environment = make(
        environment_id,
        num_envs=1,
        device=torch.device("cpu"),
        max_episode_steps=int(config["max_episode_steps"]),
    )
    try:
        observation, _ = environment.reset(seed=int(config["seed"]))
        reset_observation_shape = list(observation.shape)
        controller = ScriptedApproachEscapeController(environment.validation_task())
        totals = {
            "reward": 0.0,
            "native_cost": 0.0,
            "stl_cost": 0.0,
            "selected_algorithm_cost": 0.0,
            "warning_triggers": 0,
            "recoveries": 0,
            "deadline_violations": 0,
            "terminal_unresolved": 0,
        }
        final_info: Dict[str, Any] = {}
        terminated = False
        truncated = False
        actions = 0
        while not (terminated or truncated):
            action = torch.as_tensor(
                controller.action(environment.validation_task()),
                dtype=torch.float32,
            )
            observation, reward, selected_cost, term, trunc, info = environment.step(action)
            actions += 1
            terminated = bool(term)
            truncated = bool(trunc)
            totals["reward"] += float(reward)
            totals["native_cost"] += float(info["native_cost"])
            totals["stl_cost"] += float(info["stl_cost"])
            totals["selected_algorithm_cost"] += float(selected_cost)
            totals["warning_triggers"] += int(info["stl_warning_trigger"])
            totals["recoveries"] += int(info["stl_recovery"])
            totals["deadline_violations"] += int(info["stl_deadline_violation"])
            totals["terminal_unresolved"] += int(info["stl_terminal_unresolved"])
            final_info = info
            if actions > int(config["max_episode_steps"]) + 1:
                raise RuntimeError("positive-cost probe did not terminate at its declared horizon")

        expected = {
            "warning_triggers": int(config["expected_warning_triggers"]),
            "terminal_unresolved": int(config["expected_terminal_unresolved"]),
            "stl_cost": float(config["expected_stl_cost"]),
            "selected_algorithm_cost": float(config["expected_selected_algorithm_cost"]),
        }
        checks = {
            key: math.isclose(float(totals[key]), float(value), rel_tol=0.0, abs_tol=1e-9)
            for key, value in expected.items()
        }
        checks["selected_equals_stl"] = math.isclose(
            totals["selected_algorithm_cost"],
            totals["stl_cost"],
            rel_tol=0.0,
            abs_tol=1e-9,
        )
        checks["returned_observation_is_reset_state"] = list(observation[-3:].tolist()) == [
            0.0,
            0.0,
            0.0,
        ]
        checks["final_observation_retains_pending_state"] = bool(
            final_info["final_observation"][-3] == 1.0,
        )
        if not all(checks.values()):
            raise AssertionError(f"positive-cost probe failed: {checks}")
        return {
            "environment_id": environment_id,
            "seed": int(config["seed"]),
            "actions": actions,
            "terminated": terminated,
            "truncated": truncated,
            "reset_observation_shape": reset_observation_shape,
            "returned_observation_shape": list(observation.shape),
            "totals": totals,
            "checks": checks,
        }
    finally:
        environment.close()


def read_progress(progress_path: Path) -> Dict[str, float]:
    with progress_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 1:
        raise AssertionError(f"expected one smoke epoch, found {len(rows)}")
    parsed: Dict[str, float] = {}
    for key, value in rows[0].items():
        if value not in (None, ""):
            parsed[key] = float(value)
    return parsed


def run_ppo_update(config: Mapping[str, Any], runs_dir: Path) -> Dict[str, Any]:
    if "lagrange_cfgs" not in config:
        raise ValueError(
            "PPO-Lagrangian runs must declare lagrange_cfgs explicitly; "
            "the OmniSafe default cost_limit must not be inherited silently",
        )
    lagrange_cfgs = dict(config["lagrange_cfgs"])
    if "cost_limit" not in lagrange_cfgs:
        raise ValueError("lagrange_cfgs.cost_limit must be declared explicitly")
    cost_limit = float(lagrange_cfgs["cost_limit"])
    if not math.isfinite(cost_limit) or cost_limit < 0.0:
        raise ValueError("lagrange_cfgs.cost_limit must be a finite non-negative number")
    vector_env_nums = int(config["train_cfgs"]["vector_env_nums"])
    steps_per_epoch = int(config["algo_cfgs"]["steps_per_epoch"])
    smoke_horizon = int(config["env_cfgs"]["max_episode_steps"])
    if steps_per_epoch % vector_env_nums:
        raise ValueError("steps_per_epoch must be divisible by vector_env_nums")
    steps_per_vector_env = steps_per_epoch // vector_env_nums
    if steps_per_vector_env % smoke_horizon:
        raise ValueError(
            "per-vector rollout length must align with the episode horizon so epoch reset "
            "cannot erase a pending monitor obligation",
        )
    custom = {
        "seed": int(config["seed"]),
        "train_cfgs": dict(config["train_cfgs"]),
        "algo_cfgs": dict(config["algo_cfgs"]),
        "logger_cfgs": {**dict(config["logger_cfgs"]), "log_dir": str(runs_dir)},
        "model_cfgs": dict(config["model_cfgs"]),
        "lagrange_cfgs": lagrange_cfgs,
        "env_cfgs": dict(config["env_cfgs"]),
    }
    agent = omnisafe.Agent(
        str(config["algorithm"]),
        str(config["environment_id"]),
        custom_cfgs=custom,
    )
    observation_shape = list(agent.agent._env.observation_space.shape)  # pylint: disable=protected-access
    result = agent.learn()
    log_dir = Path(agent.agent.logger.log_dir)
    progress_path = log_dir / "progress.csv"
    progress = read_progress(progress_path)
    checkpoint_paths = sorted((log_dir / "torch_save").glob("*.pt"))
    required_progress = {
        "Train/Epoch",
        "Train/StopIter",
        "TotalEnvSteps",
        "Loss/Loss_pi",
        "Loss/Loss_reward_critic",
        "Loss/Loss_cost_critic",
        "Metrics/NativeCost",
        "Metrics/STLCost",
        "Metrics/SelectedAlgorithmCost",
    }
    checks = {
        "one_epoch_written": progress.get("Train/Epoch") == 0.0,
        "one_or_more_update_iterations": progress.get("Train/StopIter", 0.0) >= 1.0,
        "declared_steps_collected": progress.get("TotalEnvSteps")
        == float(config["train_cfgs"]["total_steps"]),
        "augmented_observation_dimension": observation_shape == [63],
        "all_progress_values_finite": all(math.isfinite(value) for value in progress.values()),
        "separate_cost_metrics_present": required_progress.issubset(progress),
        "checkpoint_written": bool(checkpoint_paths),
    }
    if not all(checks.values()):
        raise AssertionError(f"PPO-Lagrangian smoke failed: {checks}")
    return {
        "algorithm": str(config["algorithm"]),
        "environment_id": str(config["environment_id"]),
        "observation_shape": observation_shape,
        "result": {
            "mean_episode_return": float(result[0]),
            "mean_selected_episode_cost": float(result[1]),
            "mean_episode_length": float(result[2]),
        },
        "progress": progress,
        "log_dir": str(log_dir),
        "progress_sha256": sha256_file(progress_path),
        "checkpoint_count": len(checkpoint_paths),
        "declared_lagrange_cost_limit": cost_limit,
        "checks": checks,
        "rollout_alignment": {
            "steps_per_vector_env": steps_per_vector_env,
            "episode_horizon": smoke_horizon,
            "complete_horizons_per_vector_env": steps_per_vector_env // smoke_horizon,
        },
    }


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
    config = load_config(config_path)
    missing_registrations = sorted(set(REGISTERED_ENV_IDS) - set(support_envs()))
    if missing_registrations:
        raise RuntimeError(f"Stage I environments are not registered: {missing_registrations}")

    positive_probe = run_positive_cost_probe(config["positive_stl_cost_probe"])
    ppo_update = run_ppo_update(config["ppo_lagrangian_smoke"], output_dir / "omnisafe_runs")
    summary = {
        "schema_version": 1,
        "milestone": "omnisafe_wrapper_integration_smoke",
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "interface smoke only; not a training result or safety claim",
        "repository": {
            "git_head_before_milestone_commit": git_revision(),
            "config_path": str(config_path.relative_to(REPOSITORY_ROOT)),
            "config_sha256": sha256_file(config_path),
        },
        "platform": {
            "python": platform.python_version(),
            "system": platform.platform(),
            "torch": torch.__version__,
            "torch_cuda_build": torch.version.cuda,
            "cuda_available": torch.cuda.is_available(),
            "omnisafe": installed_version("omnisafe"),
            "safety_gymnasium": installed_version("safety-gymnasium"),
            "gymnasium": installed_version("gymnasium"),
            "mujoco": installed_version("mujoco"),
            "rtamt": installed_version("rtamt"),
        },
        "registered_environment_ids": list(REGISTERED_ENV_IDS),
        "positive_stl_cost_probe": positive_probe,
        "ppo_lagrangian_smoke": ppo_update,
        "gate_passed": all(positive_probe["checks"].values())
        and all(ppo_update["checks"].values()),
    }
    summary_path = output_dir / "summary.json"
    with summary_path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps({"summary": str(summary_path), "gate_passed": summary["gate_passed"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
