#!/usr/bin/env python3
"""Run/resume the frozen nine-cell Stage II-A train/validation-only matrix."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import yaml

from safety_stl.stage2_training import METHODS, sha256_file


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _write_manifest(path: Path, value: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
    temporary.replace(path)


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/stage2_v0/baselines.yaml"))
    parser.add_argument("--benchmark-root", type=Path, default=Path("benchmarks/stage2_v0"))
    parser.add_argument("--output-root", type=Path, default=Path("results/stage2a"))
    parser.add_argument("--methods", nargs="+", choices=METHODS, default=list(METHODS))
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    config_path = args.config.resolve()
    benchmark_root = args.benchmark_root.resolve()
    output_root = args.output_root.resolve()
    with config_path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    seeds = [int(seed) for seed in config["training_protocol"]["model_seeds"]]
    cells = [(method, seed) for method in args.methods for seed in seeds]
    manifest_path = output_root / "train_validation_launcher_manifest.json"
    manifest: Dict[str, Any] = {
        "schema_version": 1,
        "scope": "train_and_validation_only_no_held_out_evaluation",
        "status": "running",
        "config_path": str(config_path),
        "config_sha256": sha256_file(config_path),
        "benchmark_root": str(benchmark_root),
        "started_at_unix": time.time(),
        "python": sys.executable,
        "cells": [],
    }
    _write_manifest(manifest_path, manifest)
    for method, seed in cells:
        command = [
            sys.executable,
            str(REPOSITORY_ROOT / "scripts/train_stage2a.py"),
            "--method",
            method,
            "--seed",
            str(seed),
            "--output-root",
            str(output_root),
            "--config",
            str(config_path),
            "--benchmark-root",
            str(benchmark_root),
        ]
        started = time.time()
        result = subprocess.run(command, cwd=str(REPOSITORY_ROOT), check=False)
        record = {
            "method": method,
            "seed": seed,
            "command": command,
            "started_at_unix": started,
            "completed_at_unix": time.time(),
            "return_code": int(result.returncode),
        }
        manifest["cells"].append(record)
        _write_manifest(manifest_path, manifest)
        if result.returncode:
            manifest["status"] = "failed"
            manifest["failed_cell"] = {"method": method, "seed": seed}
            manifest["completed_at_unix"] = time.time()
            _write_manifest(manifest_path, manifest)
            return int(result.returncode)
    manifest["status"] = "success"
    manifest["completed_at_unix"] = time.time()
    _write_manifest(manifest_path, manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
