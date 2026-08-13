#!/usr/bin/env python3
"""Validate D43 and calculate its matched transition budget from preflights."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence

import yaml


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTOCOL = REPOSITORY_ROOT / "configs" / "fixed_route_v1" / "quick_turn.yaml"


def load_mapping(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle)
    if not isinstance(loaded, Mapping):
        raise ValueError(f"expected a YAML mapping: {path}")
    return dict(loaded)


def validate_protocol(protocol: Mapping[str, Any]) -> None:
    if protocol.get("protocol_id") != "fixed_route_v1_quick_turn":
        raise ValueError("unexpected quick-turn protocol_id")
    training = protocol["training"]
    expected_conditions = ["task_only", "native_safety", "stl_dense_safety"]
    if list(training["condition_order"]) != expected_conditions:
        raise ValueError("quick-turn condition order changed")
    if set(protocol["conditions"]) != set(expected_conditions):
        raise ValueError("quick-turn condition definitions changed")
    if int(training["aggregate_training_wall_clock_limit_minutes"]) != 30:
        raise ValueError("quick-turn training cap must remain 30 minutes")
    if int(training["target_transitions_per_condition"]) != 150_000:
        raise ValueError("quick-turn target must remain 150k transitions per condition")
    if int(training["minimum_transitions_per_condition"]) != 50_000:
        raise ValueError("quick-turn minimum must remain 50k transitions per condition")
    if not bool(training["transitions_must_match_across_conditions"]):
        raise ValueError("quick-turn transitions must remain matched")
    if float(training["throughput_capacity_fraction"]) != 0.80:
        raise ValueError("quick-turn throughput capacity fraction must remain 0.80")


def effective_transitions(protocol: Mapping[str, Any], throughputs: Sequence[float]) -> int:
    if len(throughputs) != 3 or not all(math.isfinite(value) and value > 0 for value in throughputs):
        raise ValueError("provide three positive finite preflight throughputs")
    training = protocol["training"]
    granularity = int(training["transition_granularity"])
    seconds = 60 * int(training["aggregate_training_wall_clock_limit_minutes"])
    usable = float(training["throughput_capacity_fraction"])
    capacity_per_condition = usable * seconds * min(throughputs) / 3
    bounded = min(int(training["target_transitions_per_condition"]), int(capacity_per_condition))
    return bounded // granularity * granularity


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument(
        "--throughput",
        type=float,
        nargs=3,
        metavar=("TASK", "NATIVE", "STL_DENSE"),
        help="10k-preflight transitions/second for the three conditions",
    )
    options = parser.parse_args()

    protocol = load_mapping(options.protocol)
    validate_protocol(protocol)
    result: Dict[str, Any] = {
        "protocol_id": protocol["protocol_id"],
        "static_validation": "passed",
        "training_cap_minutes": 30,
    }
    if options.throughput is not None:
        transitions = effective_transitions(protocol, options.throughput)
        minimum = int(protocol["training"]["minimum_transitions_per_condition"])
        result.update(
            {
                "preflight_transitions_per_second": list(options.throughput),
                "minimum_preflight_transitions_per_second": min(options.throughput),
                "effective_transitions_per_condition": transitions,
                "training_may_start": transitions >= minimum,
            },
        )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
