"""Focused tests for the frozen Stage I paired hierarchical analysis."""

from __future__ import annotations

import random
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List

from safety_stl.pilot_analysis import (
    aggregate_condition,
    draw_hierarchical_sample,
    goal_noninferiority,
    load_complete_matrix,
    paired_hierarchical_bootstrap,
    primary_comparison,
)
from safety_stl.pilot_protocol import load_yaml_mapping


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = load_yaml_mapping(REPOSITORY_ROOT / "configs" / "stage1_pilot" / "protocol.yaml")


def synthetic_records() -> List[Dict[str, Any]]:
    records = []
    for condition_index, condition in enumerate(
        ("task_only", "native_cost", "gold_stl_cost"),
    ):
        for training_seed in (1101, 2202):
            for evaluation_seed in (10000, 10001, 10002):
                missed = int((condition_index + training_seed + evaluation_seed) % 3 == 0)
                records.append(
                    {
                        "condition": condition,
                        "training_seed": training_seed,
                        "evaluation_seed": evaluation_seed,
                        "episode_return": float(condition_index + evaluation_seed % 2),
                        "native_cost_total": float(condition_index),
                        "gold_stl_cost_total": float(missed),
                        "goal_events": int(evaluation_seed % 2 == 0),
                        "goal_success": evaluation_seed % 2 == 0,
                        "episode_length": 1000,
                        "minimum_distance": 0.2,
                        "trigger_count": 1,
                        "recovery_count": 1 - missed,
                        "late_recovery_count": 0,
                        "deadline_violation_count": missed,
                        "terminal_unresolved_count": 0,
                        "completed_window_count": 1,
                        "online_oracle_agreement": True,
                        "rtamt_max_robustness_difference": 0.0,
                    },
                )
    return records


class PilotAnalysisTests(unittest.TestCase):
    def test_zero_trigger_and_zero_task_baseline_remain_distinct(self) -> None:
        no_trigger = aggregate_condition(
            [
                {
                    "trigger_count": 0,
                    "deadline_violation_count": 0,
                    "terminal_unresolved_count": 0,
                    "native_cost_total": 0,
                    "gold_stl_cost_total": 0,
                    "episode_return": 1,
                    "goal_success": True,
                    "goal_events": 1,
                    "episode_length": 1000,
                    "online_oracle_agreement": True,
                    "rtamt_max_robustness_difference": 0,
                },
            ],
        )
        self.assertIsNone(no_trigger["missed_obligation_rate_per_trigger"])

        task = {"missed_obligation_rate_per_trigger": 0.0}
        gold = {"missed_obligation_rate_per_trigger": 0.0}
        comparison = primary_comparison(task, gold)
        self.assertTrue(comparison["task_only_baseline_rate_is_zero"])
        self.assertEqual(comparison["absolute_reduction_task_minus_gold"], 0.0)
        self.assertIsNone(comparison["relative_reduction"])
        self.assertIsNone(comparison["relative_target_met"])

    def test_hierarchical_draw_keeps_episodes_inside_source_seed(self) -> None:
        evaluation = {1101: [11, 12], 2202: [21, 22]}
        draws = draw_hierarchical_sample([1101, 2202], evaluation, random.Random(7))
        self.assertEqual(len(draws), 2)
        for draw in draws:
            self.assertTrue(set(draw.evaluation_seeds).issubset(evaluation[draw.source_training_seed]))

    def test_bootstrap_is_deterministic_and_paired(self) -> None:
        records = synthetic_records()
        first = paired_hierarchical_bootstrap(
            records,
            training_seeds=[1101, 2202],
            replicates=50,
            rng_seed=12345,
        )
        second = paired_hierarchical_bootstrap(
            records,
            training_seeds=[1101, 2202],
            replicates=50,
            rng_seed=12345,
        )
        self.assertEqual(first["primary_rows"], second["primary_rows"])

    def test_goal_noninferiority_sign_and_margin(self) -> None:
        passing = goal_noninferiority(
            0.80,
            0.72,
            margin=0.10,
            confidence_interval={"lower": -0.09, "upper": 0.01},
        )
        self.assertAlmostEqual(passing["difference_gold_minus_task"], -0.08)
        self.assertTrue(passing["point_estimate_noninferior"])
        self.assertTrue(passing["confidence_interval_supports_noninferiority"])
        failing = goal_noninferiority(
            0.80,
            0.69,
            margin=0.10,
            confidence_interval={"lower": -0.12, "upper": -0.01},
        )
        self.assertFalse(failing["point_estimate_noninferior"])
        self.assertFalse(failing["confidence_interval_supports_noninferiority"])

    def test_incomplete_matrix_analysis_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "requires all 15 jobs"):
                load_complete_matrix(Path(temporary), PROTOCOL)


if __name__ == "__main__":
    unittest.main()
