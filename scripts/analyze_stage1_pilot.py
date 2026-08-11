#!/usr/bin/env python3
"""Analyze all 15 frozen Stage I final-checkpoint evaluations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from safety_stl.pilot_analysis import analyze_pilot, load_complete_matrix, write_analysis_outputs
from safety_stl.pilot_protocol import load_yaml_mapping


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTOCOL = REPOSITORY_ROOT / "configs" / "stage1_pilot" / "protocol.yaml"
DEFAULT_RESULTS = REPOSITORY_ROOT / "results" / "stage1_pilot"
DEFAULT_OUTPUT = DEFAULT_RESULTS / "analysis"
DEFAULT_ANALYSIS_RNG_SEED = 20260811


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--analysis-rng-seed", type=int, default=DEFAULT_ANALYSIS_RNG_SEED)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    protocol = load_yaml_mapping(args.protocol.resolve())
    episodes, manifests, learning_curves = load_complete_matrix(
        args.results_dir.resolve(),
        protocol,
    )
    analysis = analyze_pilot(
        episodes,
        protocol,
        analysis_rng_seed=args.analysis_rng_seed,
    )
    outputs = write_analysis_outputs(
        args.output_dir.resolve(),
        analysis,
        episodes,
        learning_curves,
    )
    print(
        json.dumps(
            {
                "complete_job_count": len(manifests),
                "episode_record_count": len(episodes),
                "outputs": outputs,
            },
            sort_keys=True,
        ),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
