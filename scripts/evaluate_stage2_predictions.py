#!/usr/bin/env python3
"""Evaluate one Stage II baseline prediction JSONL against Gold labels."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from safety_stl.offline_metrics import evaluate_prediction_file


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("predictions", type=Path)
    parser.add_argument("--benchmark-root", type=Path, default=Path("benchmarks/stage2_v0"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    generated = args.benchmark_root / "generated"
    metrics = evaluate_prediction_file(
        args.predictions,
        [generated / "synthetic_trajectories.jsonl", generated / "real_trajectories.jsonl"],
        args.benchmark_root / "specifications.json",
    )
    rendered = json.dumps(metrics, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
