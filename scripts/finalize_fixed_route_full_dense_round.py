#!/usr/bin/env python3
"""Validate completed D47 artifacts and finish fixed-checkpoint evaluation."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from safety_stl.fixed_route_quick_turn import (
    cost_routing_diagnostics,
    evaluate_cell,
    load_contract,
    read_mapping,
    sha256_file,
    write_json,
)

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/fixed_route_v1/full_dense_round.yaml"
OUTPUT = ROOT / "results/fixed_route_v1/full_dense_round"
PROTOCOL_ID = "fixed_route_v1_full_dense_round"
AUTHORITY = "D47"


def _csv(path: Path) -> List[Dict[str, float]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [
            {key: float(value) for key, value in row.items() if value != ""}
            for row in csv.DictReader(handle)
        ]


def _training_artifact(
    output: Path,
    protocol: Mapping[str, Any],
    condition: str,
) -> Dict[str, Any]:
    transitions = int(protocol["training"]["transitions_per_condition"])
    manifest_path = output / condition / f"reported-{transitions}" / "manifest.json"
    manifest = read_mapping(manifest_path)
    attempt = Path(str(manifest["attempt_dir"]))
    run_dirs = [path.parent for path in (attempt / "training").glob("*/seed-*/progress.csv")]
    if len(run_dirs) != 1:
        raise RuntimeError(f"expected one run directory for {condition}, found {run_dirs}")
    run_dir = run_dirs[0].resolve()
    progress = run_dir / "progress.csv"
    rows = _csv(progress)
    checkpoint = run_dir / "torch_save" / "epoch-100.pt"
    selected = str(protocol["conditions"][condition]["selected_learner_cost"])
    route_field: Optional[str] = {
        "identically_zero": None,
        "native_hazard_cost": "Metrics/NativeCost",
        "c1_causal_dense_surrogate": "Metrics/STLDenseCost",
    }[selected]
    routing = cost_routing_diagnostics(rows, route_field)
    checks = {
        "progress_has_100_epochs": len(rows) == 100,
        "final_total_env_steps_is_1m": bool(rows) and int(rows[-1]["TotalEnvSteps"]) == transitions,
        "all_progress_values_finite": all(
            math.isfinite(value) for row in rows for value in row.values()
        ),
        "cost_routing_within_declared_float_tolerance": bool(routing["passed"]),
        "final_checkpoint_exists": checkpoint.is_file(),
    }
    if not all(checks.values()):
        raise RuntimeError(f"completed-artifact validation failed for {condition}: {checks}")
    return {
        "condition_id": condition,
        "original_manifest": str(manifest_path.resolve()),
        "original_manifest_status": str(manifest["status"]),
        "attempt_dir": str(attempt.resolve()),
        "run_dir": str(run_dir),
        "progress": str(progress),
        "progress_sha256": sha256_file(progress),
        "checkpoint": str(checkpoint),
        "checkpoint_sha256": sha256_file(checkpoint),
        "transitions": transitions,
        "cost_limit": float(manifest["cost_limit"]),
        "checks": checks,
        "routing_diagnostics": routing,
    }


def _valid_existing_evaluation(
    path: Path,
    *,
    checkpoint_sha256: str,
    seeds: Sequence[int],
    deterministic: bool,
) -> bool:
    summary_path = path / "summary.json"
    episodes_path = path / "episodes.csv"
    if not summary_path.is_file() or not episodes_path.is_file():
        return False
    summary = read_mapping(summary_path)
    return (
        summary.get("checkpoint_sha256") == checkpoint_sha256
        and summary.get("episode_seeds") == list(seeds)
        and bool(summary.get("deterministic_policy")) == deterministic
        and int(summary.get("aggregate", {}).get("episode_count", -1)) == len(seeds)
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=PROTOCOL)
    parser.add_argument("--output-root", type=Path, default=OUTPUT)
    options = parser.parse_args(argv)
    protocol_path, output = options.protocol.resolve(), options.output_root.resolve()
    protocol, scenario, rule = load_contract(
        protocol_path,
        expected_protocol_id=PROTOCOL_ID,
        expected_authority=AUTHORITY,
    )
    conditions = list(protocol["training"]["condition_order"])
    cells = [_training_artifact(output, protocol, condition) for condition in conditions]
    validation = {
        "schema_version": 1,
        "status": "validated_complete_after_logger_tolerance_correction",
        "protocol": str(protocol_path),
        "protocol_sha256": sha256_file(protocol_path),
        "scenario_sha256": sha256_file(scenario),
        "rule_sha256": sha256_file(rule),
        "adoption_scope": "completed checkpoints only; original failed manifest retained",
        "validator_correction": {
            "reason": "independent float32 logger accumulators can differ by a few ULPs",
            "relative_tolerance": 1e-7,
            "absolute_tolerance": 1e-6,
        },
        "cells": cells,
    }
    write_json(output / "validated_training_completion.json", validation)
    write_json(
        output / "training_summary.json",
        {
            "status": "validated_training_complete",
            "transitions_per_condition": int(protocol["training"]["transitions_per_condition"]),
            "cells": cells,
        },
    )

    evaluation = protocol["evaluation"]
    stochastic_seeds = list(
        range(
            int(evaluation["stochastic_seed_start"]),
            int(evaluation["stochastic_seed_start"])
            + int(evaluation["stochastic_summary_episodes_per_condition"]),
        ),
    )
    deterministic_seeds = [int(evaluation["deterministic_trajectory_seed"])]
    evaluation_status: Dict[str, Any] = {}
    for cell in cells:
        condition = str(cell["condition_id"])
        training = {"run_dir": cell["run_dir"], "checkpoint": cell["checkpoint"]}
        outputs = {}
        for mode, seeds, deterministic, trajectories in (
            ("stochastic", stochastic_seeds, False, condition == "task_only"),
            ("deterministic", deterministic_seeds, True, True),
        ):
            destination = output / "evaluation" / condition / mode
            if not _valid_existing_evaluation(
                destination,
                checkpoint_sha256=str(cell["checkpoint_sha256"]),
                seeds=seeds,
                deterministic=deterministic,
            ):
                evaluate_cell(
                    protocol_path,
                    training,
                    destination,
                    deterministic=deterministic,
                    seeds=seeds,
                    trajectories=trajectories,
                    expected_protocol_id=PROTOCOL_ID,
                    expected_authority=AUTHORITY,
                )
                outputs[mode] = "generated"
            else:
                outputs[mode] = "reused_hash_and_seed_matched"
        evaluation_status[condition] = outputs
    write_json(
        output / "finalization_summary.json",
        {
            "schema_version": 1,
            "status": "training_validated_and_fixed_checkpoint_evaluation_complete",
            "training_validation": str((output / "validated_training_completion.json").resolve()),
            "evaluation": evaluation_status,
        },
    )
    print(json.dumps(read_mapping(output / "finalization_summary.json"), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
