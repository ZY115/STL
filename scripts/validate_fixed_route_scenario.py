#!/usr/bin/env python3
"""Validate and summarize the controlled fixed-route scenario without MuJoCo."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MODULE_ROOT = REPOSITORY_ROOT / "src" / "safety_stl"
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))

from fixed_route import load_fixed_route_scenario  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=REPOSITORY_ROOT / "configs" / "fixed_route_v1" / "scenario.yaml",
    )
    options = parser.parse_args()
    scenario = load_fixed_route_scenario(options.config)
    print(json.dumps(scenario.as_dict(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
