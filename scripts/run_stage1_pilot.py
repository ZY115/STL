#!/usr/bin/env python3
"""Run, resume, or inspect the frozen Stage I 15-job pilot matrix."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence

from safety_stl.pilot_protocol import load_and_validate_pilot, load_yaml_mapping
from safety_stl.pilot_runner import (
    CONDITION_ORDER,
    dry_run_manifest,
    enumerate_pilot_jobs,
    execute_job,
    write_json_atomic,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = REPOSITORY_ROOT / "configs" / "stage1_pilot" / "protocol.yaml"
OVERLAY_PATHS = {
    condition: REPOSITORY_ROOT / "configs" / "stage1_pilot" / f"{condition}.yaml"
    for condition in CONDITION_ORDER
}
DEFAULT_OUTPUT = REPOSITORY_ROOT / "results" / "stage1_pilot"


def resolve_repository_path(value: str) -> Path:
    path = (REPOSITORY_ROOT / value).resolve()
    path.relative_to(REPOSITORY_ROOT)
    return path


def load_preflight(path: Path, protocol: Mapping[str, Any]) -> Dict[str, Any]:
    config = load_yaml_mapping(path)
    if config.get("status") != "excluded_engineering_preflight_not_for_inference":
        raise ValueError("preflight must be explicitly excluded from pilot inference")
    if config.get("condition") != "gold_stl_cost" or int(config.get("seed")) != 20260811:
        raise ValueError("the authorized preflight is fixed to gold_stl_cost seed 20260811")
    overrides = dict(config["training_overrides"])
    frozen_train = protocol["omnisafe"]["train_cfgs"]
    frozen_algo = protocol["omnisafe"]["algo_cfgs"]
    exact = {
        "total_steps": int(overrides["total_steps"]) == 100_000,
        "vector_env_nums": int(overrides["vector_env_nums"])
        == int(frozen_train["vector_env_nums"])
        == 10,
        "steps_per_epoch": int(overrides["steps_per_epoch"])
        == int(frozen_algo["steps_per_epoch"])
        == 10_000,
        "update_iters": int(overrides["update_iters"]) == int(frozen_algo["update_iters"]),
        "batch_size": int(overrides["batch_size"]) == int(frozen_algo["batch_size"]),
    }
    if not all(exact.values()):
        raise ValueError(f"preflight is not exact-scale apart from its bounded budget: {exact}")
    evaluation = dict(config["evaluation"])
    if int(evaluation["paired_episode_count"]) != 10:
        raise ValueError("preflight requires exactly 10 excluded evaluation episodes")
    return config


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=PROTOCOL_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--condition", action="append", choices=CONDITION_ORDER)
    parser.add_argument("--seed", type=int, action="append")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--dry-run-output", type=Path)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--train-only", action="store_true")
    parser.add_argument("--evaluate-only", action="store_true")
    parser.add_argument(
        "--preflight",
        type=Path,
        help="run only the bounded excluded engineering preflight declared by this config",
    )
    parser.add_argument(
        "--authorized-full-pilot",
        action="store_true",
        help="required compute gate for any non-preflight pilot training",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    protocol_path = args.protocol.resolve()
    condition_paths = [OVERLAY_PATHS[name] for name in CONDITION_ORDER]
    protocol, conditions = load_and_validate_pilot(protocol_path, condition_paths)
    training_seeds = [int(seed) for seed in protocol["matched_design"]["training_seeds"]]
    output_root = args.output_dir.resolve()
    episode_horizon = int(protocol["matched_design"]["episode_horizon"])
    evaluation_start = int(protocol["matched_design"]["evaluation_seed_start"])
    evaluation_count = int(
        protocol["matched_design"]["evaluation_episodes_per_training_seed_and_condition"],
    )
    overrides = None

    if args.preflight:
        if args.condition or args.seed:
            raise ValueError("preflight condition and seed come only from its fixed config")
        preflight_path = args.preflight.resolve()
        preflight = load_preflight(preflight_path, protocol)
        jobs = enumerate_pilot_jobs(
            [int(preflight["seed"])],
            conditions=[str(preflight["condition"])],
        )
        overrides = dict(preflight["training_overrides"])
        evaluation_cfg = preflight["evaluation"]
        evaluation_start = int(evaluation_cfg["episode_seed_start"])
        evaluation_count = int(evaluation_cfg["paired_episode_count"])
        output_root = args.output_dir.resolve()
    else:
        jobs = enumerate_pilot_jobs(
            training_seeds,
            conditions=args.condition,
            seeds=args.seed,
        )

    evaluation_seeds = list(range(evaluation_start, evaluation_start + evaluation_count))
    if args.dry_run:
        plan = dry_run_manifest(
            jobs=jobs,
            repository_root=REPOSITORY_ROOT,
            output_root=output_root,
            protocol=protocol,
            conditions=conditions,
            protocol_path=protocol_path,
            overlay_paths=OVERLAY_PATHS,
            evaluation_seeds=evaluation_seeds,
        )
        target = args.dry_run_output
        if target:
            write_json_atomic(target.resolve(), plan)
        print(json.dumps(plan, indent=2, sort_keys=True))
        return 0

    if not args.preflight and not args.authorized_full_pilot:
        raise PermissionError(
            "full pilot compute is not authorized; use --dry-run or obtain owner approval "
            "before adding --authorized-full-pilot",
        )
    if args.preflight and args.authorized_full_pilot:
        raise ValueError("the preflight does not use the full-pilot authorization flag")

    results = []
    for job in jobs:
        result = execute_job(
            job=job,
            repository_root=REPOSITORY_ROOT,
            output_root=output_root,
            protocol=protocol,
            overlay=conditions[job.condition],
            protocol_path=protocol_path,
            overlay_path=OVERLAY_PATHS[job.condition],
            evaluation_seeds=evaluation_seeds,
            episode_horizon=episode_horizon,
            resume=args.resume,
            train_only=args.train_only,
            evaluate_only=args.evaluate_only,
            overrides=overrides,
        )
        results.append({"job_id": result["job_id"], "action": result["action"]})
        print(json.dumps(results[-1], sort_keys=True), flush=True)
    print(json.dumps({"completed": results, "job_count": len(results)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
