#!/usr/bin/env python3
"""Run/resume the authorized D38 task-control then C0/C1 matrix."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

from safety_stl.gold_diagnostic_runner import (
    DEFAULT_PROTOCOL,
    load_diagnostic_contract,
    run_diagnostic_cell,
    sha256_file,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--phase",
        choices=("task-controls", "cost-cells", "all"),
        default="all",
        help="Task controls always freeze budgets before any cost cell may run.",
    )
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("results/stage2_gold_diagnostic"),
    )
    return parser.parse_args(argv)


def _write(path: Path, value: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _freeze_budgets(protocol_path: Path, output_root: Path) -> None:
    subprocess.run(
        [
            sys.executable,
            str(REPOSITORY_ROOT / "scripts/derive_gold_diagnostic_budgets.py"),
            "--protocol",
            str(protocol_path),
            "--results-root",
            str(output_root),
        ],
        cwd=str(REPOSITORY_ROOT),
        check=True,
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    protocol_path = args.protocol.resolve()
    output_root = args.output_root.resolve()
    protocol, budgets = load_diagnostic_contract(protocol_path)
    task_condition = "task_only_control"
    cost_conditions = [
        str(row["condition_id"])
        for row in protocol["conditions"]
        if str(row["condition_id"]) != task_condition
    ]
    jobs = []
    if args.phase in {"task-controls", "all"}:
        jobs.extend((task_condition, int(seed)) for seed in protocol["training_seeds"])
    if args.phase == "cost-cells":
        if not budgets:
            raise FileNotFoundError("frozen task-control budgets are required before cost cells")
        jobs.extend(
            (condition, int(seed))
            for condition in cost_conditions
            for seed in protocol["training_seeds"]
        )
    manifest_path = output_root / "matrix_manifest.json"
    state: Dict[str, Any] = {
        "schema_version": 1,
        "status": "running",
        "phase": args.phase,
        "scope": "D38_non_confirmatory_300k_diagnostic_only",
        "protocol": str(protocol_path),
        "protocol_sha256": sha256_file(protocol_path),
        "started_at_unix": time.time(),
        "jobs": [],
    }
    _write(manifest_path, state)
    try:
        for condition, seed in jobs:
            summary = run_diagnostic_cell(
                condition,
                seed,
                output_root,
                protocol_path=protocol_path,
                dry_run=False,
            )
            state["jobs"].append(
                {
                    "condition_id": condition,
                    "seed": seed,
                    "status": "success",
                    "manifest": str(output_root / condition / f"seed-{seed}" / "manifest.json"),
                    "checkpoint": summary["checkpoint"],
                },
            )
            _write(manifest_path, state)
        if args.phase in {"task-controls", "all"}:
            _freeze_budgets(protocol_path, output_root)
            budget_path = REPOSITORY_ROOT / protocol["budget_source"]["path"]
            state["budget"] = {"path": str(budget_path), "sha256": sha256_file(budget_path)}
            _write(manifest_path, state)
        if args.phase == "all":
            # Reloading is mandatory: the cost cells must bind to the budget
            # file frozen from the just-completed matched task controls.
            _, budgets = load_diagnostic_contract(protocol_path)
            if not budgets:
                raise RuntimeError("budget freeze did not produce the D38 contract")
            for condition in cost_conditions:
                for seed_value in protocol["training_seeds"]:
                    seed = int(seed_value)
                    summary = run_diagnostic_cell(
                        condition,
                        seed,
                        output_root,
                        protocol_path=protocol_path,
                        dry_run=False,
                    )
                    state["jobs"].append(
                        {
                            "condition_id": condition,
                            "seed": seed,
                            "status": "success",
                            "manifest": str(
                                output_root / condition / f"seed-{seed}" / "manifest.json"
                            ),
                            "checkpoint": summary["checkpoint"],
                        },
                    )
                    _write(manifest_path, state)
    except BaseException as error:
        state.update(
            {
                "status": "interrupted" if isinstance(error, KeyboardInterrupt) else "failed",
                "stopped_at_unix": time.time(),
                "error_type": type(error).__name__,
                "error": str(error),
            },
        )
        _write(manifest_path, state)
        raise
    state.update({"status": "success", "completed_at_unix": time.time()})
    _write(manifest_path, state)
    print(json.dumps(state, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
