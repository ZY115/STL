"""Tests for the owner-approved, pilot-only Stage I protocol."""

from __future__ import annotations

import copy
import unittest
from pathlib import Path

from safety_stl.pilot_protocol import (
    compose_omnisafe_config,
    load_and_validate_pilot,
    load_yaml_mapping,
    validate_protocol,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = REPOSITORY_ROOT / "configs" / "stage1_pilot" / "protocol.yaml"
CONDITION_PATHS = [
    REPOSITORY_ROOT / "configs" / "stage1_pilot" / "task_only.yaml",
    REPOSITORY_ROOT / "configs" / "stage1_pilot" / "native_cost.yaml",
    REPOSITORY_ROOT / "configs" / "stage1_pilot" / "gold_stl_cost.yaml",
]


class PilotProtocolTests(unittest.TestCase):
    def test_frozen_protocol_and_all_condition_overlays_validate(self) -> None:
        protocol, conditions = load_and_validate_pilot(PROTOCOL_PATH, CONDITION_PATHS)
        self.assertEqual(set(conditions), {"task_only", "native_cost", "gold_stl_cost"})
        self.assertEqual(protocol["matched_design"]["uncertainty"]["replicates"], 10000)
        self.assertEqual(
            protocol["primary_safety_metric"]["absolute_reduction_definition"],
            "task_only_rate_minus_gold_stl_rate",
        )
        self.assertEqual(protocol["omnisafe"]["train_cfgs"]["device"], "cuda:0")

    def test_cost_limits_compose_with_different_recorded_units(self) -> None:
        protocol, conditions = load_and_validate_pilot(PROTOCOL_PATH, CONDITION_PATHS)
        limits = {}
        units = {}
        for condition, overlay in conditions.items():
            resolved = compose_omnisafe_config(
                protocol,
                overlay,
                seed=1101,
                log_dir=Path("unused"),
            )
            limits[condition] = resolved["custom_cfgs"]["lagrange_cfgs"]["cost_limit"]
            units[condition] = overlay["cost_semantic_unit"]
        self.assertEqual(limits, {"task_only": 0.0, "native_cost": 25.0, "gold_stl_cost": 0.1})
        self.assertEqual(len(set(units.values())), 3)

    def test_zero_baseline_and_nonfinal_guards_cannot_be_removed(self) -> None:
        protocol = load_yaml_mapping(PROTOCOL_PATH)
        changed = copy.deepcopy(protocol)
        changed["primary_safety_metric"]["if_task_only_baseline_rate_is_zero"] = (
            "report_relative_reduction"
        )
        with self.assertRaises(ValueError):
            validate_protocol(changed)
        changed = copy.deepcopy(protocol)
        changed["status"] = "final_main_study_standard"
        with self.assertRaises(ValueError):
            validate_protocol(changed)


if __name__ == "__main__":
    unittest.main()
