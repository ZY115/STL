#!/usr/bin/env python3
"""Verify a nonzero STL event cost inside an actual PPOLag rollout."""

from __future__ import annotations

import argparse
import json
import math
import platform
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence

import torch
import yaml

from run_omnisafe_integration_smoke import (
    REPOSITORY_ROOT,
    git_revision,
    run_ppo_update,
    sha256_file,
)


DEFAULT_CONFIG = REPOSITORY_ROOT / "configs" / "on_policy_positive_cost_sanity.yaml"
DEFAULT_OUTPUT = REPOSITORY_ROOT / "results" / "on_policy_sanity"


def installed_version(distribution: str) -> str:
    try:
        return metadata.version(distribution)
    except metadata.PackageNotFoundError:
        return "not-installed"


def load_config(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle)
    if not isinstance(loaded, Mapping):
        raise ValueError("on-policy sanity configuration must be a mapping")
    if loaded.get("status") != "fixed_sanity_configuration_not_main_training":
        raise ValueError("sanity configuration must state that it is not main training")
    if "ppo_lagrangian_sanity" not in loaded or "acceptance" not in loaded:
        raise ValueError("sanity configuration is missing run or acceptance settings")
    return dict(loaded)


def evaluate_acceptance(result: Mapping[str, Any], acceptance: Mapping[str, Any]) -> Dict[str, bool]:
    progress = result["progress"]
    stl_cost = float(progress["Metrics/STLCost"])
    selected_cost = float(progress["Metrics/SelectedAlgorithmCost"])
    trigger_count = float(progress["Metrics/STLTriggers"])
    terminal_events = float(progress["Metrics/STLDeadlineViolations"]) + float(
        progress["Metrics/STLTerminalUnresolved"],
    )
    checks = {
        "positive_mean_stl_cost": stl_cost > 0.0,
        "selected_cost_equals_stl_cost": math.isclose(
            selected_cost,
            stl_cost,
            rel_tol=0.0,
            abs_tol=1e-9,
        ),
        "positive_trigger_count": trigger_count > 0.0,
        "positive_terminal_event_count": terminal_events > 0.0,
        "explicit_cost_limit": math.isfinite(float(result["declared_lagrange_cost_limit"])),
        "rollout_episode_alignment": (
            int(result["rollout_alignment"]["complete_horizons_per_vector_env"]) >= 1
        ),
    }
    required = {
        "positive_mean_stl_cost": bool(acceptance["require_positive_mean_stl_cost"]),
        "selected_cost_equals_stl_cost": bool(
            acceptance["require_selected_cost_equals_stl_cost"],
        ),
        "positive_trigger_count": bool(acceptance["require_positive_trigger_count"]),
        "positive_terminal_event_count": bool(
            acceptance["require_positive_terminal_event_count"],
        ),
        "explicit_cost_limit": bool(acceptance["require_explicit_cost_limit"]),
        "rollout_episode_alignment": bool(
            acceptance["require_rollout_episode_alignment"],
        ),
    }
    return {key: (checks[key] if required[key] else True) for key in checks}


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    config_path = args.config.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    config = load_config(config_path)
    run_result = run_ppo_update(
        config["ppo_lagrangian_sanity"],
        output_dir / "omnisafe_runs",
    )
    checks = evaluate_acceptance(run_result, config["acceptance"])
    if not all(checks.values()):
        raise AssertionError(f"on-policy positive-cost sanity failed: {checks}")
    summary = {
        "schema_version": 1,
        "milestone": str(config["milestone"]),
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": str(config["scope_note"]),
        "repository": {
            "git_head_before_milestone_commit": git_revision(),
            "config_path": str(config_path.relative_to(REPOSITORY_ROOT)),
            "config_sha256": sha256_file(config_path),
        },
        "platform": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "torch_cuda_build": torch.version.cuda,
            "cuda_available": torch.cuda.is_available(),
            "omnisafe": installed_version("omnisafe"),
            "safety_gymnasium": installed_version("safety-gymnasium"),
        },
        "ppo_lagrangian_rollout": run_result,
        "checks": checks,
        "gate_passed": all(checks.values()),
    }
    summary_path = output_dir / "summary.json"
    with summary_path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps({"summary": str(summary_path), "gate_passed": True}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
