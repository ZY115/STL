"""Tests for the common Stage I checkpoint-evaluation oracle."""

from __future__ import annotations

import unittest

from safety_stl.evaluation import summarize_episodes, verify_gold_oracle


class EvaluationTests(unittest.TestCase):
    def test_online_trace_is_checked_against_direct_oracle_and_rtamt(self) -> None:
        rows = [
            {
                "sample_index": 0,
                "distance": 0.29,
                "warning_trigger": True,
                "recovery": False,
                "late_recovery": False,
                "deadline_violation": False,
                "terminal_unresolved": False,
                "stl_cost": 0,
                "terminated": False,
                "truncated": False,
            },
            {
                "sample_index": 1,
                "distance": 0.40,
                "warning_trigger": False,
                "recovery": False,
                "late_recovery": False,
                "deadline_violation": False,
                "terminal_unresolved": False,
                "stl_cost": 0,
                "terminated": False,
                "truncated": False,
            },
            {
                "sample_index": 2,
                "distance": 0.50,
                "warning_trigger": False,
                "recovery": True,
                "late_recovery": False,
                "deadline_violation": False,
                "terminal_unresolved": False,
                "stl_cost": 0,
                "terminated": False,
                "truncated": False,
            },
            {
                "sample_index": 3,
                "distance": 0.60,
                "warning_trigger": False,
                "recovery": False,
                "late_recovery": False,
                "deadline_violation": False,
                "terminal_unresolved": False,
                "stl_cost": 0,
                "terminated": False,
                "truncated": True,
            },
        ]
        result = verify_gold_oracle(
            rows,
            d_warn=0.30,
            d_safe=0.50,
            deadline_steps=3,
            tolerance=1e-9,
        )
        self.assertTrue(result["agreement"])
        self.assertEqual(result["trigger_count"], 1)
        self.assertEqual(result["recovery_count"], 1)
        self.assertEqual(result["completed_window_count"], 1)
        self.assertEqual(result["rtamt_max_robustness_difference"], 0.0)

    def test_summary_uses_pooled_trigger_denominators(self) -> None:
        base = {
            "episode_return": 1.0,
            "native_cost_total": 2.0,
            "gold_stl_cost_total": 1,
            "goal_events": 1,
            "goal_success": True,
            "episode_length": 1000,
            "minimum_distance": 0.2,
            "recovery_count": 1,
            "terminal_unresolved_count": 0,
            "online_oracle_agreement": True,
            "completed_window_count": 1,
            "rtamt_max_robustness_difference": 0.0,
        }
        episodes = [
            {**base, "trigger_count": 2, "deadline_violation_count": 1},
            {
                **base,
                "goal_events": 0,
                "goal_success": False,
                "trigger_count": 1,
                "recovery_count": 0,
                "deadline_violation_count": 1,
            },
        ]
        summary = summarize_episodes(episodes)
        self.assertEqual(summary["pooled_counts"]["triggers"], 3)
        self.assertAlmostEqual(summary["pooled_rates_per_trigger"]["deadline_violation"], 2 / 3)
        self.assertAlmostEqual(
            summary["pooled_rates_per_trigger"]["missed_recovery_obligation"],
            2 / 3,
        )
        self.assertEqual(summary["pooled_rates_per_trigger"]["terminal_unresolved"], 0.0)
        self.assertEqual(summary["goal_success_rate"], 0.5)


if __name__ == "__main__":
    unittest.main()
