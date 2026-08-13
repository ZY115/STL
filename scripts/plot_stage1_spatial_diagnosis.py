#!/usr/bin/env python3
"""Build deterministic figures from a verified Stage I spatial replay."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional, Sequence

from safety_stl.spatial_plotting import build_spatial_figures


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("results/post_pilot_spatial_diagnosis"),
        help="Directory produced by replay_stage1_spatial_trajectories.py.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    manifest = build_spatial_figures(args.output_root)
    print(json.dumps(manifest, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
