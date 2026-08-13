#!/usr/bin/env python3
"""Build the fixed 60-episode Stage II real-policy corpus from spatial replay."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional, Sequence

from safety_stl.stage2_benchmark import validate_benchmark_contract
from safety_stl.stage2_real_corpus import extract_real_policy_corpus


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--spatial-root",
        type=Path,
        default=Path("results/post_pilot_spatial_diagnosis"),
    )
    parser.add_argument(
        "--benchmark-root",
        type=Path,
        default=Path("benchmarks/stage2_v0"),
    )
    parser.add_argument(
        "--include-held-out-labels",
        action="store_true",
        help="Fails unless every held-out specification has independent approval.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    contract = validate_benchmark_contract(args.benchmark_root)
    manifest = extract_real_policy_corpus(
        args.spatial_root / "full_geometry.csv.gz",
        Path("results/stage1_pilot/analysis/episode_records.csv"),
        contract["specifications"],
        args.benchmark_root / "generated",
        include_held_out_labels=args.include_held_out_labels,
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
