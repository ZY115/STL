#!/usr/bin/env python3
"""Freeze D38 C0/C1 limits from all matched task-control evaluations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import yaml

from safety_stl.gold_diagnostic import derive_task_control_budgets, sha256_file


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--protocol",
        type=Path,
        default=Path("configs/stage2_gold_diagnostic/protocol.yaml"),
    )
    parser.add_argument(
        "--results-root",
        type=Path,
        default=Path("results/stage2_gold_diagnostic"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("configs/stage2_gold_diagnostic/budgets.json"),
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    protocol_path = args.protocol.resolve()
    with protocol_path.open("r", encoding="utf-8") as handle:
        protocol = yaml.safe_load(handle)
    rows: List[Dict[str, Any]] = []
    sources = []
    for training_seed in protocol["training_seeds"]:
        cell = args.results_root.resolve() / "task_only_control" / f"seed-{training_seed}"
        manifest_path = cell / "manifest.json"
        manifest = json.load(manifest_path.open("r", encoding="utf-8"))
        if manifest.get("status") != "success":
            raise RuntimeError(f"task control is not complete: {manifest_path}")
        trajectory_record = manifest["summary"]["evaluation"]["artifacts"]["trajectories"]
        trajectory_path = Path(trajectory_record["path"])
        if sha256_file(trajectory_path) != trajectory_record["sha256"]:
            raise RuntimeError(f"task-control trajectory hash mismatch: {trajectory_path}")
        with trajectory_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                row = json.loads(line)
                row["training_seed"] = int(training_seed)
                rows.append(row)
        sources.append(
            {
                "training_seed": int(training_seed),
                "manifest": str(manifest_path),
                "manifest_sha256": sha256_file(manifest_path),
                "trajectories": str(trajectory_path),
                "trajectories_sha256": sha256_file(trajectory_path),
            },
        )
    expected_evaluation_seeds = list(
        range(
            int(protocol["scale"]["screening_evaluation_seed_start"]),
            int(protocol["scale"]["screening_evaluation_seed_start"])
            + int(protocol["scale"]["screening_evaluation_episodes_per_seed"]),
        ),
    )
    observed_evaluation_seeds = sorted({int(row["evaluation_seed"]) for row in rows})
    if observed_evaluation_seeds != expected_evaluation_seeds:
        raise RuntimeError("task-control evaluations do not use the frozen screening seeds")
    result = {
        "schema_version": 1,
        "authority": "D38/D40",
        "status": "frozen_before_gold_diagnostic_training",
        "protocol": {"path": str(protocol_path), "sha256": sha256_file(protocol_path)},
        "sources": sources,
        **derive_task_control_budgets(rows),
    }
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
