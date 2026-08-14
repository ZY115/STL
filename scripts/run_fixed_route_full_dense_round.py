#!/usr/bin/env python3
"""Run one authorized 1M x three-condition fixed-route C1 dense round."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

import yaml

from safety_stl.fixed_route_quick_turn import (
    build_config,
    derive_task_budgets,
    evaluate_cell,
    git_commit,
    load_contract,
    read_mapping,
    run_cell,
    sha256_file,
    write_json,
)

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/fixed_route_v1/full_dense_round.yaml"
OVERRIDE = ROOT / "configs/fixed_route_v1/d41_full_dense_admin_override.yaml"
OUTPUT = ROOT / "results/fixed_route_v1/full_dense_round"
PROTOCOL_ID = "fixed_route_v1_full_dense_round"
AUTHORITY = "D47"


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--phase",
        choices=("dry-run", "preflight", "task-control", "cost-cells", "evaluate", "all", "status"),
        default="dry-run",
    )
    parser.add_argument("--protocol", type=Path, default=PROTOCOL)
    parser.add_argument("--output-root", type=Path, default=OUTPUT)
    return parser.parse_args(argv)


def _read(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _summary(output: Path, condition: str, transitions: int, *, preflight: bool = False) -> Dict[str, Any]:
    leaf = "preflight" if preflight else f"reported-{transitions}"
    path = output / condition / leaf / "manifest.json"
    if not path.is_file():
        raise FileNotFoundError(f"missing cell manifest: {path}")
    value = _read(path)
    if value.get("status") != "success":
        raise RuntimeError(f"cell is not successful: {path}")
    return dict(value["summary"])


def _run(protocol_path: Path, condition: str, transitions: int, cost_limit: float, output: Path, *, preflight: bool = False) -> Dict[str, Any]:
    return run_cell(
        protocol_path,
        condition,
        transitions,
        cost_limit,
        output,
        preflight=preflight,
        override_path=OVERRIDE,
        expected_protocol_id=PROTOCOL_ID,
        expected_authority=AUTHORITY,
    )


def _evaluate(protocol_path: Path, training: Dict[str, Any], output: Path, *, deterministic: bool, seeds: Sequence[int], trajectories: bool) -> Any:
    return evaluate_cell(
        protocol_path,
        training,
        output,
        deterministic=deterministic,
        seeds=seeds,
        trajectories=trajectories,
        expected_protocol_id=PROTOCOL_ID,
        expected_authority=AUTHORITY,
    )


def _kernel_tail() -> str:
    result = subprocess.run(
        ["journalctl", "-k", "-n", "40", "--no-pager"],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    protocol_path = args.protocol.resolve()
    output = args.output_root.resolve()
    protocol, scenario, rule_path = load_contract(
        protocol_path,
        expected_protocol_id=PROTOCOL_ID,
        expected_authority=AUTHORITY,
    )
    training = protocol["training"]
    conditions = list(training["condition_order"])
    transitions = int(training["transitions_per_condition"])
    evaluation = protocol["evaluation"]
    stochastic_seeds = list(
        range(
            int(evaluation["stochastic_seed_start"]),
            int(evaluation["stochastic_seed_start"])
            + int(evaluation["stochastic_summary_episodes_per_condition"]),
        ),
    )
    deterministic_seed = int(evaluation["deterministic_trajectory_seed"])
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / "run_manifest.json"

    if args.phase == "status":
        value = _read(manifest_path) if manifest_path.is_file() else {"status": "not_started"}
        print(json.dumps(value, indent=2, sort_keys=True))
        return 0

    state: Dict[str, Any] = {
        "schema_version": 1,
        "status": "running",
        "phase": args.phase,
        "command": [sys.executable, *sys.argv],
        "pid": int(__import__("os").getpid()),
        "protocol": str(protocol_path),
        "protocol_sha256": sha256_file(protocol_path),
        "scenario_sha256": sha256_file(scenario),
        "rule_sha256": sha256_file(rule_path),
        "override": str(OVERRIDE),
        "override_sha256": sha256_file(OVERRIDE),
        "git_commit": git_commit(),
        "training_seed": int(training["training_seed"]),
        "transitions_per_condition": transitions,
        "condition_order": conditions,
        "started_at_unix": time.time(),
    }
    write_json(manifest_path, state)
    effective = {
        "source_protocol": str(protocol_path),
        "source_protocol_sha256": sha256_file(protocol_path),
        "training_seed": int(training["training_seed"]),
        "transitions_per_condition": transitions,
        "stochastic_evaluation_seeds": stochastic_seeds,
        "deterministic_trajectory_seed": deterministic_seed,
        "learner_cost": "C1 causal dense surrogate",
        "gold_evaluation_truth": "binary bounded-recovery events",
    }
    (output / "effective_protocol.yaml").write_text(
        yaml.safe_dump(effective, sort_keys=True),
        encoding="utf-8",
    )

    try:
        if args.phase == "dry-run":
            configs = {}
            for condition in conditions:
                cfg = build_config(
                    protocol,
                    scenario,
                    rule_path,
                    condition,
                    10_000,
                    0.0,
                    output / "dry_run" / condition,
                    update_iters=1,
                )
                configs[condition] = {
                    "environment_id": str(cfg.env_id),
                    "epochs": int(cfg.train_cfgs.epochs),
                    "vector_env_nums": int(cfg.train_cfgs.vector_env_nums),
                    "update_iters": int(cfg.algo_cfgs.update_iters),
                    "rule": str(cfg.env_cfgs.rule_config_path),
                    "scenario": str(cfg.env_cfgs.scenario_config_path),
                }
            state.update({"status": "success", "dry_run_configs": configs})
            write_json(manifest_path, state)
            print(json.dumps(state, indent=2, sort_keys=True))
            return 0

        if args.phase in {"preflight", "all"}:
            preflights = [
                _run(
                    protocol_path,
                    condition,
                    int(training["preflight_transitions_per_condition"]),
                    0.0,
                    output,
                    preflight=True,
                )
                for condition in conditions
            ]
            dense = next(row for row in preflights if row["condition_id"] == "stl_dense_safety")
            if not dense["dense_exceeds_binary_event_cost"]:
                raise RuntimeError(
                    "C1 startup gate failed: dense cost did not strictly exceed binary event cost",
                )
            write_json(
                output / "preflight_summary.json",
                {
                    "status": "passed",
                    "preflights": preflights,
                    "c1_not_binary_only": True,
                    "c1_evidence": dense["last_epoch_cost_metrics"],
                    "kernel_tail_at_gate": _kernel_tail(),
                },
            )
        if args.phase == "preflight":
            state.update({"status": "success", "completed_at_unix": time.time()})
            write_json(manifest_path, state)
            return 0
        if not (output / "preflight_summary.json").is_file():
            raise FileNotFoundError("the three-condition C1 preflight must pass first")

        if args.phase in {"task-control", "all"}:
            task = _run(protocol_path, "task_only", transitions, 0.0, output)
            _, episodes, trajectories = _evaluate(
                protocol_path,
                task,
                output / "evaluation" / "task_only" / "stochastic",
                deterministic=False,
                seeds=stochastic_seeds,
                trajectories=True,
            )
            budgets = derive_task_budgets(episodes, trajectories, read_mapping(rule_path))
            budgets.update(
                {
                    "evaluation_seeds": stochastic_seeds,
                    "task_checkpoint_sha256": sha256_file(Path(task["checkpoint"])),
                    "protocol_sha256": sha256_file(protocol_path),
                },
            )
            write_json(output / "task_control_budgets.json", budgets)
        if args.phase == "task-control":
            state.update({"status": "success", "completed_at_unix": time.time()})
            write_json(manifest_path, state)
            return 0

        budget_path = output / "task_control_budgets.json"
        if args.phase in {"cost-cells", "all"}:
            if not budget_path.is_file():
                raise FileNotFoundError("task-only evaluation must freeze separate budgets first")
            limits = _read(budget_path)["cost_limit"]
            native = _run(
                protocol_path,
                "native_safety",
                transitions,
                float(limits["native_cost_per_episode"]),
                output,
            )
            dense = _run(
                protocol_path,
                "stl_dense_safety",
                transitions,
                float(limits["c1_surrogate_mass_per_episode"]),
                output,
            )
            task = _summary(output, "task_only", transitions)
            write_json(
                output / "training_summary.json",
                {
                    "status": "training_complete",
                    "transitions_per_condition": transitions,
                    "cells": [task, native, dense],
                },
            )
        if args.phase == "cost-cells":
            state.update({"status": "success", "completed_at_unix": time.time()})
            write_json(manifest_path, state)
            return 0

        if args.phase in {"evaluate", "all"}:
            for condition in conditions:
                trained = _summary(output, condition, transitions)
                stochastic_output = output / "evaluation" / condition / "stochastic"
                if condition != "task_only" or not (stochastic_output / "summary.json").is_file():
                    _evaluate(
                        protocol_path,
                        trained,
                        stochastic_output,
                        deterministic=False,
                        seeds=stochastic_seeds,
                        trajectories=False,
                    )
                _evaluate(
                    protocol_path,
                    trained,
                    output / "evaluation" / condition / "deterministic",
                    deterministic=True,
                    seeds=[deterministic_seed],
                    trajectories=True,
                )

        state.update({"status": "success", "completed_at_unix": time.time()})
        write_json(manifest_path, state)
        print(json.dumps(state, indent=2, sort_keys=True))
        return 0
    except BaseException as error:
        state.update(
            {
                "status": "failed",
                "error_type": type(error).__name__,
                "error": str(error),
                "stopped_at_unix": time.time(),
            },
        )
        write_json(manifest_path, state)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
