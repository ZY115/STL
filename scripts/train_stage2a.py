#!/usr/bin/env python3
"""Train or resume one frozen Stage II-A model/seed cell."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional, Sequence

from safety_stl.stage2_training import METHODS, run_stage2a_training


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--method", choices=METHODS, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--output-root", type=Path, default=Path("results/stage2a"))
    parser.add_argument("--config", type=Path, default=Path("configs/stage2_v0/baselines.yaml"))
    parser.add_argument("--benchmark-root", type=Path, default=Path("benchmarks/stage2_v0"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-resume", action="store_true")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    suffix = "dry-run" if args.dry_run else f"seed-{args.seed}"
    output_dir = args.output_root / args.method / suffix
    summary = run_stage2a_training(
        args.method,
        args.seed,
        output_dir,
        config_path=args.config,
        benchmark_root=args.benchmark_root,
        dry_run=args.dry_run,
        resume=not args.no_resume,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
