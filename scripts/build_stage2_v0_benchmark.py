#!/usr/bin/env python3
"""Build the Stage II v0 offline benchmark foundation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from safety_stl.stage2_benchmark import BENCHMARK_ROOT, build_benchmark


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=BENCHMARK_ROOT)
    parser.add_argument(
        "--diagnosis-root",
        type=Path,
        default=Path("results/post_pilot_diagnosis"),
    )
    args = parser.parse_args()
    coverage = build_benchmark(args.output_root.resolve(), args.diagnosis_root.resolve())
    print(json.dumps(coverage, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
