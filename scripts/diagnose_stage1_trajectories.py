#!/usr/bin/env python3
"""Replay the frozen pilot checkpoints and write post-pilot diagnostics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from safety_stl.trajectory_diagnosis import run_diagnosis


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/post_pilot_diagnosis"),
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    summary = run_diagnosis(args.output_dir)
    print(
        json.dumps(
            {
                "output_dir": str(args.output_dir),
                "checkpoint_count": summary["matrix"]["checkpoint_count"],
                "episode_count": summary["matrix"]["episode_count"],
                "no_training": True,
            },
            sort_keys=True,
        ),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
