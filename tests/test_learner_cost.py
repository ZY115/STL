"""Boundary tests for the frozen D38 C0/C1 learner-cost candidates."""

from __future__ import annotations

import unittest

from safety_stl.learner_cost import GoldLearnerCost, causal_dense_surrogate, gold_learner_cost
from safety_stl.monitor import BoundedRecoveryMonitor


class LearnerCostTests(unittest.TestCase):
    def setUp(self) -> None:
        self.monitor = BoundedRecoveryMonitor(0.45, 0.55, 4)

    def test_inactive_is_zero_and_trigger_is_distance_only(self) -> None:
        inactive = self.monitor.reset(0.60)
        self.assertEqual(causal_dense_surrogate(inactive, 0.45, 0.55), 0.0)
        trigger = self.monitor.step(0.44)
        self.assertAlmostEqual(causal_dense_surrogate(trigger, 0.45, 0.55), 0.5)

    def test_urgency_increases_causally_and_is_bounded(self) -> None:
        self.monitor.reset(0.44)
        costs = [
            causal_dense_surrogate(self.monitor.step(0.50), 0.45, 0.55)
            for _ in range(3)
        ]
        self.assertEqual(costs, sorted(costs))
        self.assertTrue(all(0.0 <= value <= 1.0 for value in costs))

    def test_actual_deadline_and_terminal_miss_emit_one(self) -> None:
        self.monitor.reset(0.44)
        output = None
        for _ in range(4):
            output = self.monitor.step(0.50)
        assert output is not None
        self.assertTrue(output.stl_deadline_violation)
        self.assertEqual(causal_dense_surrogate(output, 0.45, 0.55), 1.0)

        other = BoundedRecoveryMonitor(0.45, 0.55, 4)
        other.reset(0.44)
        terminal = other.step(0.50, truncated=True)
        self.assertTrue(terminal.stl_terminal_unresolved)
        self.assertEqual(causal_dense_surrogate(terminal, 0.45, 0.55), 1.0)

    def test_c0_remains_exact_binary_gold_event(self) -> None:
        trigger = self.monitor.reset(0.44)
        self.assertEqual(
            gold_learner_cost(GoldLearnerCost.C0_BINARY_EVENT, trigger, 0.45, 0.55),
            0.0,
        )


if __name__ == "__main__":
    unittest.main()
