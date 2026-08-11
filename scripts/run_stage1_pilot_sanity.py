#!/usr/bin/env python3
"""Run the frozen Stage I protocol's three-condition small-budget sanity gate."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import re
import subprocess
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

import omnisafe
import torch

from safety_stl.evaluation import evaluate_checkpoint, write_evaluation_outputs
from safety_stl.pilot_protocol import (
    compose_omnisafe_config,
    load_and_validate_pilot,
    load_yaml_mapping,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPOSITORY_ROOT / "configs" / "stage1_pilot_sanity.yaml"
DEFAULT_OUTPUT = REPOSITORY_ROOT / "results" / "pilot_sanity"
CONDITION_ORDER = ("task_only", "native_cost", "gold_stl_cost")


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


def resolve_repository_path(value: str) -> Path:
    path = (REPOSITORY_ROOT / value).resolve()
    path.relative_to(REPOSITORY_ROOT)
    return path


def read_progress_rows(path: Path) -> List[Dict[str, float]]:
    with path.open(newline="", encoding="utf-8") as handle:
        raw_rows = list(csv.DictReader(handle))
    rows: List[Dict[str, float]] = []
    for raw in raw_rows:
        row = {
            key: float(value)
            for key, value in raw.items()
            if key is not None and value not in (None, "")
        }
        rows.append(row)
    return rows


def final_checkpoint(run_dir: Path) -> Path:
    candidates = []
    for path in (run_dir / "torch_save").glob("epoch-*.pt"):
        match = re.fullmatch(r"epoch-(\d+)\.pt", path.name)
        if match:
            candidates.append((int(match.group(1)), path))
    if not candidates:
        raise AssertionError(f"no epoch checkpoint found under {run_dir}")
    return max(candidates)[1]


def routing_checks(condition: str, rows: Sequence[Mapping[str, float]]) -> Dict[str, bool]:
    if condition == "task_only":
        routing = all(
            math.isclose(row["Metrics/SelectedAlgorithmCost"], 0.0, abs_tol=1e-9)
            for row in rows
        )
    elif condition == "native_cost":
        routing = all(
            math.isclose(
                row["Metrics/SelectedAlgorithmCost"],
                row["Metrics/NativeCost"],
                rel_tol=0.0,
                abs_tol=1e-9,
            )
            for row in rows
        )
    elif condition == "gold_stl_cost":
        routing = all(
            math.isclose(
                row["Metrics/SelectedAlgorithmCost"],
                row["Metrics/STLCost"],
                rel_tol=0.0,
                abs_tol=1e-9,
            )
            for row in rows
        )
    else:  # pragma: no cover - guarded by protocol validation
        raise ValueError(f"unknown condition: {condition}")
    return {
        "selected_cost_routing_exact_every_epoch": routing,
        "positive_native_cost_observed": any(row["Metrics/NativeCost"] > 0 for row in rows),
        "positive_stl_cost_observed": any(row["Metrics/STLCost"] > 0 for row in rows),
    }


def train_condition(resolved: Mapping[str, Any], expected_epochs: int) -> Dict[str, Any]:
    custom_cfgs = dict(resolved["custom_cfgs"])
    agent = omnisafe.Agent(
        str(resolved["algorithm"]),
        str(resolved["environment_id"]),
        custom_cfgs=custom_cfgs,
    )
    observation_shape = list(agent.agent._env.observation_space.shape)  # pylint: disable=protected-access
    result = agent.learn()
    run_dir = Path(agent.agent.logger.log_dir).resolve()
    progress_path = run_dir / "progress.csv"
    rows = read_progress_rows(progress_path)
    checkpoint_path = final_checkpoint(run_dir)
    required_metrics = {
        "TotalEnvSteps",
        "Metrics/NativeCost",
        "Metrics/STLCost",
        "Metrics/SelectedAlgorithmCost",
        "Metrics/STLTriggers",
        "Metrics/STLDeadlineViolations",
        "Metrics/STLTerminalUnresolved",
        "Metrics/LagrangeMultiplier",
    }
    general_checks = {
        "expected_epoch_rows": len(rows) == expected_epochs,
        "declared_transition_count": bool(rows)
        and rows[-1].get("TotalEnvSteps")
        == float(custom_cfgs["train_cfgs"]["total_steps"]),
        "augmented_observation_dimension": observation_shape == [63],
        "required_metrics_present_every_epoch": all(required_metrics.issubset(row) for row in rows),
        "all_training_metrics_finite": all(
            math.isfinite(value) for row in rows for value in row.values()
        ),
        "final_checkpoint_written": checkpoint_path.is_file(),
    }
    routing = routing_checks(str(resolved["condition"]), rows)
    if not all(general_checks.values()) or not routing["selected_cost_routing_exact_every_epoch"]:
        raise AssertionError(
            f"{resolved['condition']} training sanity failed: {general_checks}, {routing}",
        )
    return {
        "condition": str(resolved["condition"]),
        "environment_id": str(resolved["environment_id"]),
        "declared_cost_limit": float(custom_cfgs["lagrange_cfgs"]["cost_limit"]),
        "training_device": str(custom_cfgs["train_cfgs"]["device"]),
        "run_dir": str(run_dir),
        "progress_path": str(progress_path),
        "progress_sha256": sha256_file(progress_path),
        "progress_rows": rows,
        "checkpoint": checkpoint_path.name,
        "checkpoint_path": str(checkpoint_path),
        "checkpoint_sha256": sha256_file(checkpoint_path),
        "learn_return": {
            "mean_episode_return": float(result[0]),
            "mean_selected_episode_cost": float(result[1]),
            "mean_episode_length": float(result[2]),
        },
        "checks": {**general_checks, **routing},
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
    sanity = load_yaml_mapping(config_path)
    if sanity.get("status") != "engineering_only_not_pilot_result":
        raise ValueError("sanity config must state that it is not a pilot result")
    protocol_path = resolve_repository_path(str(sanity["protocol_config"]))
    condition_paths = [
        resolve_repository_path(str(value)) for value in sanity["condition_configs"]
    ]
    protocol, conditions = load_and_validate_pilot(protocol_path, condition_paths)
    expected_order = list(sanity["acceptance"]["exact_condition_order"])
    if expected_order != list(CONDITION_ORDER):
        raise ValueError("sanity condition order does not match the frozen gate")

    overrides = dict(sanity["sanity_training_overrides"])
    if not bool(overrides["seed_is_excluded_from_pilot_analysis"]):
        raise ValueError("engineering sanity seed must be excluded from pilot inference")
    steps_per_epoch = int(overrides["steps_per_epoch"])
    vector_env_nums = int(overrides["vector_env_nums"])
    episode_horizon = int(protocol["omnisafe"]["env_cfgs"]["max_episode_steps"])
    if steps_per_epoch % vector_env_nums:
        raise ValueError("sanity steps_per_epoch must divide across vector environments")
    per_vector_steps = steps_per_epoch // vector_env_nums
    if per_vector_steps % episode_horizon:
        raise ValueError("sanity rollout slots must contain complete episode horizons")
    if per_vector_steps != int(overrides["per_vector_steps_per_epoch"]):
        raise ValueError("declared per-vector sanity rollout length is inconsistent")
    total_steps = int(overrides["total_steps"])
    if total_steps % steps_per_epoch:
        raise ValueError("sanity total_steps must be a whole number of epochs")
    expected_epochs = total_steps // steps_per_epoch

    training: Dict[str, Dict[str, Any]] = {}
    for condition in CONDITION_ORDER:
        resolved = compose_omnisafe_config(
            protocol,
            conditions[condition],
            seed=int(overrides["seed"]),
            log_dir=output_dir / "omnisafe_runs" / condition,
            overrides=overrides,
        )
        training[condition] = train_condition(resolved, expected_epochs)

    if not training["native_cost"]["checks"]["positive_native_cost_observed"]:
        raise AssertionError("native-cost sanity did not observe a positive native cost")
    if not training["gold_stl_cost"]["checks"]["positive_stl_cost_observed"]:
        raise AssertionError("gold-STL sanity did not observe a positive STL event cost")

    evaluation_cfg = sanity["sanity_evaluation"]
    evaluation_seeds = list(
        range(
            int(evaluation_cfg["episode_seed_start"]),
            int(evaluation_cfg["episode_seed_start"])
            + int(evaluation_cfg["paired_episode_count"]),
        ),
    )
    evaluations: Dict[str, Dict[str, Any]] = {}
    for condition in CONDITION_ORDER:
        train_result = training[condition]
        eval_summary, episodes, trajectories = evaluate_checkpoint(
            Path(train_result["run_dir"]),
            str(train_result["checkpoint"]),
            evaluation_seeds,
            max_episode_steps=int(evaluation_cfg["episode_horizon"]),
            deterministic=True,
            save_trajectories=False,
        )
        output_paths = write_evaluation_outputs(
            output_dir / "evaluation" / condition,
            eval_summary,
            episodes,
            trajectories,
        )
        evaluations[condition] = {"summary": eval_summary, "outputs": output_paths}

    max_rtamt_difference = max(
        float(result["summary"]["aggregate"]["rtamt_max_robustness_difference"])
        for result in evaluations.values()
    )
    gate_checks = {
        "frozen_protocol_validated": True,
        "three_conditions_completed": set(training) == set(CONDITION_ORDER),
        "full_episode_rollout_alignment": per_vector_steps % episode_horizon == 0,
        "all_training_checks_passed": all(
            all(
                value
                for name, value in result["checks"].items()
                if name not in {"positive_native_cost_observed", "positive_stl_cost_observed"}
            )
            for result in training.values()
        ),
        "native_condition_observed_positive_native_cost": training["native_cost"]["checks"][
            "positive_native_cost_observed"
        ],
        "stl_condition_observed_positive_stl_cost": training["gold_stl_cost"]["checks"][
            "positive_stl_cost_observed"
        ],
        "paired_evaluation_seeds_identical": all(
            result["summary"]["episode_seeds"] == evaluation_seeds
            for result in evaluations.values()
        ),
        "deterministic_policy_mode_identical": all(
            result["summary"]["deterministic_policy"] for result in evaluations.values()
        ),
        "all_training_runs_use_cuda0": all(
            result["training_device"] == "cuda:0" for result in training.values()
        ),
        "all_online_direct_oracle_agree": all(
            result["summary"]["aggregate"]["all_online_oracle_agree"]
            for result in evaluations.values()
        ),
        "rtamt_within_tolerance": max_rtamt_difference
        <= float(sanity["acceptance"]["require_rtamt_max_difference_at_most"]),
    }
    gate_passed = all(gate_checks.values())
    summary = {
        "schema_version": 1,
        "milestone": str(sanity["milestone"]),
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": str(sanity["scope_note"]),
        "full_1m_runs_started": False,
        "full_1m_runs_authorized_by_this_gate": False,
        "repository": {
            "git_head_before_milestone_commit": git_revision(),
            "sanity_config": str(config_path.relative_to(REPOSITORY_ROOT)),
            "sanity_config_sha256": sha256_file(config_path),
            "protocol_config": str(protocol_path.relative_to(REPOSITORY_ROOT)),
            "protocol_config_sha256": sha256_file(protocol_path),
            "condition_config_sha256": {
                path.stem: sha256_file(path) for path in condition_paths
            },
        },
        "platform": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "torch_cuda_build": torch.version.cuda,
            "cuda_available": torch.cuda.is_available(),
            "omnisafe": installed_version("omnisafe"),
            "safety_gymnasium": installed_version("safety-gymnasium"),
            "rtamt": installed_version("rtamt"),
        },
        "sanity_scale": {
            "training_seed": int(overrides["seed"]),
            "seed_excluded_from_pilot_analysis": True,
            "transitions_per_condition": total_steps,
            "epochs": expected_epochs,
            "steps_per_epoch": steps_per_epoch,
            "vector_env_nums": vector_env_nums,
            "per_vector_steps_per_epoch": per_vector_steps,
            "paired_evaluation_seeds": evaluation_seeds,
        },
        "training": training,
        "evaluation": evaluations,
        "max_rtamt_robustness_difference": max_rtamt_difference,
        "checks": gate_checks,
        "gate_passed": gate_passed,
    }
    summary_path = output_dir / "summary.json"
    with summary_path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps({"summary": str(summary_path), "gate_passed": gate_passed}))
    if not gate_passed:
        raise AssertionError(f"three-condition pilot sanity gate failed: {gate_checks}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
