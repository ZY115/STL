#!/usr/bin/env python3
"""Evaluate an OmniSafe checkpoint with the common Stage I gold STL oracle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from safety_stl.evaluation import evaluate_checkpoint, write_evaluation_outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--checkpoint", default="epoch-1.pt")
    parser.add_argument("--episodes", type=int, default=10)
    parser.add_argument("--seed-start", type=int, default=9000)
    parser.add_argument("--max-episode-steps", type=int, default=1000)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--stochastic", action="store_true")
    parser.add_argument("--save-trajectories", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.episodes <= 0:
        raise ValueError("--episodes must be positive")
    seeds = list(range(args.seed_start, args.seed_start + args.episodes))
    summary, episodes, trajectories = evaluate_checkpoint(
        args.run_dir,
        args.checkpoint,
        seeds,
        max_episode_steps=args.max_episode_steps,
        deterministic=not args.stochastic,
        save_trajectories=args.save_trajectories,
    )
    paths = write_evaluation_outputs(args.output_dir, summary, episodes, trajectories)
    print(json.dumps({"outputs": paths, "gold_oracle_agreement": True}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
