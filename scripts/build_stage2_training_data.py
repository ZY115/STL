#!/usr/bin/env python3
"""Build frozen leakage-safe Stage II-A synthetic train/validation data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional, Sequence

from safety_stl.stage2_benchmark import validate_benchmark_contract
from safety_stl.stage2_training_data import build_stage2_training_data


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--benchmark-root",
        type=Path,
        default=Path("benchmarks/stage2_v0"),
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    contract = validate_benchmark_contract(args.benchmark_root)
    manifest = build_stage2_training_data(
        contract["specifications"],
        args.benchmark_root / "generated",
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
