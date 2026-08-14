#!/usr/bin/env python3
"""Run the D43 fixed-route package by explicit resumable phases."""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

import yaml

from safety_stl.fixed_route_quick_turn import (
    DEFAULT_PROTOCOL, build_config, derive_task_budgets, evaluate_cell, git_commit,
    load_contract, read_mapping, run_cell, sha256_file, write_json,
)

ROOT = Path(__file__).resolve().parents[1]


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("dry-run", "preflight", "task-control", "cost-cells", "evaluate", "plot", "all"), default="dry-run")
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--output-root", type=Path, default=ROOT / "results/fixed_route_v1/quick_turn")
    return parser.parse_args(argv)


def _read(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _summary(output: Path, condition: str, transitions: int, preflight: bool = False) -> Dict[str, Any]:
    leaf = "preflight" if preflight else f"reported-{transitions}"
    path = output / condition / leaf / "manifest.json"
    if not path.is_file():
        raise FileNotFoundError(f"missing completed cell: {path}")
    value = _read(path)
    if value.get("status") != "success":
        raise RuntimeError(f"cell is not successful: {path}")
    return dict(value["summary"])


def _reported_attempt_seconds(output: Path) -> float:
    total = 0.0
    for path in output.glob("*/reported-*/attempts/attempt-*/manifest.json"):
        value = _read(path)
        total += float(value.get("elapsed_seconds", 0.0))
    return total


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    protocol_path, output = args.protocol.resolve(), args.output_root.resolve()
    protocol, scenario, rule_path = load_contract(protocol_path)
    training = protocol["training"]
    conditions = list(training["condition_order"])
    manifest_path = output / "run_manifest.json"
    state: Dict[str, Any] = {
        "schema_version": 1, "status": "running", "phase": args.phase,
        "command": [sys.executable, *sys.argv],
        "condition_order": conditions,
        "aggregate_training_wall_clock_limit_minutes": int(training["aggregate_training_wall_clock_limit_minutes"]),
        "protocol": str(protocol_path), "protocol_sha256": sha256_file(protocol_path),
        "scenario_sha256": sha256_file(scenario), "rule_sha256": sha256_file(rule_path),
        "git_commit": git_commit(), "started_at_unix": time.time(),
    }
    output.mkdir(parents=True, exist_ok=True); write_json(manifest_path, state)
    try:
        if args.phase == "dry-run":
            configs = {}
            for condition in conditions:
                cfg = build_config(protocol, scenario, rule_path, condition, 10_000, 0.0, output / "dry_run" / condition, update_iters=1)
                configs[condition] = {"environment_id": str(cfg.env_id), "epochs": int(cfg.train_cfgs.epochs), "vector_env_nums": int(cfg.train_cfgs.vector_env_nums), "rule": str(cfg.env_cfgs.rule_config_path), "scenario": str(cfg.env_cfgs.scenario_config_path)}
            state.update({"status": "success", "dry_run_configs": configs})
            write_json(manifest_path, state); print(json.dumps(state, indent=2)); return 0

        if args.phase in {"preflight", "all"}:
            preflights = [run_cell(protocol_path, condition, int(training["preflight_transitions_per_condition"]), 0.0, output, preflight=True) for condition in conditions]
            minimum_tps = min(float(row["transitions_per_second"]) for row in preflights)
            capacity = float(training["throughput_capacity_fraction"]) * 60 * int(training["aggregate_training_wall_clock_limit_minutes"]) * minimum_tps / 3
            granularity = int(training["transition_granularity"])
            effective = min(int(training["target_transitions_per_condition"]), int(capacity)) // granularity * granularity
            if effective < int(training["minimum_transitions_per_condition"]):
                raise RuntimeError("preflight throughput cannot fit the declared 50k minimum")
            write_json(output / "preflight_summary.json", {"preflights": preflights, "minimum_tps": minimum_tps, "effective_transitions_per_condition": effective})
            (output / "effective_protocol.yaml").write_text(
                yaml.safe_dump(
                    {
                        "source_protocol": str(protocol_path),
                        "source_protocol_sha256": sha256_file(protocol_path),
                        "effective_transitions_per_condition": effective,
                        "training_seed": int(training["training_seed"]),
                        "stochastic_evaluation_seeds": list(range(29173, 29193)),
                        "deterministic_trajectory_seed": 39173,
                        "transition_selection_uses_policy_outcomes": False,
                    },
                    sort_keys=True,
                ),
                encoding="utf-8",
            )
        preflight_path = output / "preflight_summary.json"
        if args.phase != "preflight":
            if not preflight_path.is_file():
                raise FileNotFoundError("run the three-condition preflight first")
            effective = int(_read(preflight_path)["effective_transitions_per_condition"])
            effective_contract = {
                "source_protocol": str(protocol_path),
                "source_protocol_sha256": sha256_file(protocol_path),
                "effective_transitions_per_condition": effective,
                "training_seed": int(training["training_seed"]),
                "stochastic_evaluation_seeds": list(range(29173, 29193)),
                "deterministic_trajectory_seed": 39173,
                "transition_selection_uses_policy_outcomes": False,
            }
            (output / "effective_protocol.yaml").write_text(
                yaml.safe_dump(effective_contract, sort_keys=True),
                encoding="utf-8",
            )
        else:
            state.update({"status": "success", "completed_at_unix": time.time()}); write_json(manifest_path, state); return 0

        evaluation_seeds = list(range(29173, 29193))
        if args.phase in {"task-control", "all"}:
            task = run_cell(protocol_path, "task_only", effective, 0.0, output)
            if _reported_attempt_seconds(output) >= 60 * int(training["aggregate_training_wall_clock_limit_minutes"]):
                raise RuntimeError("aggregate reported training cap reached after task-only")
            _, episodes, trajectories = evaluate_cell(protocol_path, task, output / "task_control_evaluation", deterministic=False, seeds=evaluation_seeds, trajectories=True)
            budgets = derive_task_budgets(episodes, trajectories, read_mapping(rule_path))
            budgets.update({"evaluation_seeds": evaluation_seeds, "task_checkpoint_sha256": sha256_file(Path(task["checkpoint"]))})
            write_json(output / "task_control_budgets.json", budgets)
        budget_path = output / "task_control_budgets.json"
        if args.phase in {"cost-cells", "all"}:
            if not budget_path.is_file():
                raise FileNotFoundError("task-only evaluation must freeze budgets before cost cells")
            budgets = _read(budget_path)["cost_limit"]
            task = _summary(output, "task_only", effective)
            elapsed = _reported_attempt_seconds(output)
            if elapsed >= 60 * int(training["aggregate_training_wall_clock_limit_minutes"]):
                raise RuntimeError("aggregate reported training cap already exhausted")
            native = run_cell(protocol_path, "native_safety", effective, float(budgets["native_cost_per_episode"]), output)
            elapsed = _reported_attempt_seconds(output)
            if elapsed >= 60 * int(training["aggregate_training_wall_clock_limit_minutes"]):
                raise RuntimeError("aggregate reported training cap reached before STL cell")
            dense = run_cell(protocol_path, "stl_dense_safety", effective, float(budgets["c1_surrogate_mass_per_episode"]), output)
            elapsed = _reported_attempt_seconds(output)
            if elapsed > 60 * int(training["aggregate_training_wall_clock_limit_minutes"]):
                raise RuntimeError("aggregate reported training exceeded 30 minutes")
            write_json(output / "training_summary.json", {"effective_transitions_per_condition": effective, "aggregate_training_seconds": elapsed, "cells": [task, native, dense]})
        if args.phase in {"evaluate", "all"}:
            for condition in conditions:
                trained = _summary(output, condition, effective)
                evaluate_cell(protocol_path, trained, output / "evaluation" / condition / "stochastic", deterministic=False, seeds=evaluation_seeds, trajectories=False)
                evaluate_cell(protocol_path, trained, output / "evaluation" / condition / "deterministic", deterministic=True, seeds=[39173], trajectories=True)
        if args.phase in {"plot", "all"}:
            subprocess.run([sys.executable, str(ROOT / "scripts/plot_fixed_route_quick_turn.py"), "--output-root", str(output)], cwd=ROOT, check=True)
        state.update({"status": "success", "effective_transitions_per_condition": effective, "completed_at_unix": time.time()}); write_json(manifest_path, state)
        print(json.dumps(state, indent=2, sort_keys=True)); return 0
    except BaseException as error:
        state.update({"status": "failed", "error_type": type(error).__name__, "error": str(error), "stopped_at_unix": time.time()}); write_json(manifest_path, state); raise


if __name__ == "__main__":
    raise SystemExit(main())
