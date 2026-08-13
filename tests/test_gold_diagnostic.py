"""Unit checks for separate-unit C0/C1 diagnostic budget derivation."""

from __future__ import annotations

import unittest

from safety_stl.gold_diagnostic import dense_cost_from_evaluation_row, derive_task_control_budgets
from safety_stl.gold_diagnostic_runner import _next_attempt_directory, resolve_condition


def row(**overrides):
    value = {
        "deadline_violation": "0",
        "terminal_unresolved": "0",
        "monitor_state": "pending",
        "remaining_steps": "79",
        "public_lidar_distance": "0.45",
    }
    value.update(overrides)
    return value


class GoldDiagnosticTests(unittest.TestCase):
    def test_attempt_directories_preserve_prior_failure_evidence(self) -> None:
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(_next_attempt_directory(root)[0], 1)
            (root / "attempts/attempt-0001").mkdir(parents=True)
            (root / "attempts/not-an-attempt").mkdir()
            self.assertEqual(_next_attempt_directory(root)[0], 2)

    def test_dense_cost_boundaries(self) -> None:
        self.assertEqual(dense_cost_from_evaluation_row(row(monitor_state="inactive")), 0.0)
        self.assertAlmostEqual(dense_cost_from_evaluation_row(row()), 0.5)
        self.assertEqual(dense_cost_from_evaluation_row(row(deadline_violation="1")), 1.0)
        self.assertEqual(dense_cost_from_evaluation_row(row(terminal_unresolved="1")), 1.0)

    def test_condition_limits_are_resolved_from_separate_units(self) -> None:
        protocol = {
            "conditions": [
                {"condition_id": "c0", "cost_limit_from": "diagnostic_cost_limit.c0"},
                {"condition_id": "c1", "cost_limit_from": "diagnostic_cost_limit.c1"},
            ],
        }
        budgets = {"diagnostic_cost_limit": {"c0": 1.2, "c1": 42.0}}
        self.assertEqual(resolve_condition(protocol, budgets, "c0")["cost_limit"], 1.2)
        self.assertEqual(resolve_condition(protocol, budgets, "c1")["cost_limit"], 42.0)

    def test_budget_derivation_requires_three_by_fifty_paired_episodes(self) -> None:
        rows = []
        for training_seed in (7307, 8419, 9521):
            for evaluation_seed in range(23001, 23051):
                rows.extend(
                    {
                        **row(monitor_state="inactive"),
                        "training_seed": training_seed,
                        "evaluation_seed": evaluation_seed,
                        "action_index": action_index,
                        "stl_cost": int(action_index == 999),
                    }
                    for action_index in range(1000)
                )
        result = derive_task_control_budgets(rows)
        self.assertEqual(result["task_control_episode_count"], 150)
        self.assertEqual(result["paired_evaluation_seeds"], list(range(23001, 23051)))
        self.assertAlmostEqual(result["diagnostic_cost_limit"]["c0_events_per_episode"], 0.7)
        self.assertEqual(result["diagnostic_cost_limit"]["c1_surrogate_mass_per_episode"], 0.0)

        for affected in rows[-1000:]:
            affected["evaluation_seed"] = 99999
        with self.assertRaisesRegex(ValueError, "same paired seeds"):
            derive_task_control_budgets(rows)


if __name__ == "__main__":
    unittest.main()
