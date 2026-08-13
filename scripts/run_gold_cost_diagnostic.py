#!/usr/bin/env python3
"""Train one frozen D38 Gold learner-cost diagnostic cell."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional, Sequence

from safety_stl.gold_diagnostic_runner import run_diagnostic_cell


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--condition", required=True)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--output-root", type=Path, default=Path("results/stage2_gold_diagnostic"))
    parser.add_argument(
        "--protocol",
        type=Path,
        default=Path("configs/stage2_gold_diagnostic/protocol.yaml"),
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    summary = run_diagnostic_cell(
        args.condition,
        args.seed,
        args.output_root,
        protocol_path=args.protocol,
        dry_run=args.dry_run,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
