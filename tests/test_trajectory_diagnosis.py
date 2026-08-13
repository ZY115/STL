"""Unit tests for post-pilot mechanism summaries."""

from __future__ import annotations

import unittest

from safety_stl.trajectory_diagnosis import effect_decomposition, summarize_condition


class TrajectoryDiagnosisTests(unittest.TestCase):
    def test_condition_summary_keeps_entry_and_recovery_separate(self) -> None:
        rows = [
            {
                "trigger_count": 4,
                "recovery_count": 3,
                "deadline_violation_count": 1,
                "terminal_unresolved_count": 0,
                "episode_length": 100,
                "positive_cost_step_count": 1,
                "on_time_recovery_latency_sum": 30,
                "deadline_violation_delay_sum": 79,
                "terminal_unresolved_delay_sum": 0,
                "episode_return": 2,
                "native_cost_total": 5,
                "goal_success": True,
            },
            {
                "trigger_count": 2,
                "recovery_count": 1,
                "deadline_violation_count": 0,
                "terminal_unresolved_count": 1,
                "episode_length": 100,
                "positive_cost_step_count": 1,
                "on_time_recovery_latency_sum": 20,
                "deadline_violation_delay_sum": 0,
                "terminal_unresolved_delay_sum": 15,
                "episode_return": 4,
                "native_cost_total": 7,
                "goal_success": False,
            },
        ]
        result = summarize_condition(rows)
        self.assertEqual(result["trigger_count"], 6)
        self.assertAlmostEqual(result["triggers_per_episode"], 3.0)
        self.assertAlmostEqual(result["on_time_recovery_rate_per_trigger"], 4 / 6)
        self.assertAlmostEqual(result["missed_obligation_rate_per_trigger"], 2 / 6)
        self.assertAlmostEqual(result["mean_on_time_recovery_latency_steps"], 12.5)
        self.assertAlmostEqual(result["positive_cost_frequency_per_action_step"], 0.01)

    def test_effect_decomposition_reports_both_mechanisms(self) -> None:
        summaries = {
            "task_only": {
                "triggers_per_episode": 5.0,
                "on_time_recovery_rate_per_trigger": 0.8,
                "missed_obligation_rate_per_trigger": 0.2,
            },
            "native_cost": {
                "triggers_per_episode": 4.0,
                "on_time_recovery_rate_per_trigger": 0.7,
                "missed_obligation_rate_per_trigger": 0.3,
            },
            "gold_stl_cost": {
                "triggers_per_episode": 5.0,
                "on_time_recovery_rate_per_trigger": 0.75,
                "missed_obligation_rate_per_trigger": 0.25,
            },
        }
        result = effect_decomposition(summaries)
        self.assertAlmostEqual(
            result["native_cost"]["relative_trigger_frequency_change_vs_task"],
            -0.2,
        )
        self.assertAlmostEqual(
            result["gold_stl_cost"]["absolute_missed_rate_change_vs_task"],
            0.05,
        )


if __name__ == "__main__":
    unittest.main()
