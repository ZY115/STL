#!/usr/bin/env python3
"""Replay all frozen Stage I checkpoints and export diagnostic-only geometry."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional, Sequence

from safety_stl.spatial_diagnosis import run_spatial_replay


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("results/post_pilot_spatial_diagnosis"),
        help="Output directory for compact artifacts and the ignored full geometry table.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    summary = run_spatial_replay(args.output_root)
    print(
        json.dumps(
            {
                "output_root": str(args.output_root),
                "checkpoint_count": summary["matrix"]["checkpoint_count"],
                "episode_count": summary["matrix"]["episode_count"],
                "geometry_row_count": summary["matrix"]["geometry_row_count"],
                "all_replays_match_frozen": summary["matrix"]["all_replays_match_frozen"],
                "no_training": True,
            },
            sort_keys=True,
        ),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
