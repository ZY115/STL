"""Authoritative synthetic boundary tests from the normative specification."""

from __future__ import annotations

import unittest

from safety_stl.monitor import BoundedRecoveryMonitor, MonitorState


D_WARN = 0.30
D_SAFE = 0.50
K = 3


class MonitorBoundaryTests(unittest.TestCase):
    def monitor(self) -> BoundedRecoveryMonitor:
        return BoundedRecoveryMonitor(D_WARN, D_SAFE, K)

    def test_always_above_warning_is_vacuous(self) -> None:
        monitor = self.monitor()
        outputs = [monitor.reset(0.40)] + [monitor.step(0.40) for _ in range(5)]
        self.assertFalse(any(output.stl_warning_trigger for output in outputs))
        self.assertEqual(sum(output.stl_cost for output in outputs), 0)

    def test_reset_inside_warning_triggers_at_zero(self) -> None:
        monitor = self.monitor()
        output = monitor.reset(0.29)
        self.assertTrue(output.stl_warning_trigger)
        self.assertEqual(output.stl_trigger_step, 0)
        self.assertEqual(output.stl_deadline_step, K)
        self.assertEqual(monitor.policy_state(), (1.0, 0.0, 1.0))

    def test_warning_equality_does_not_trigger(self) -> None:
        output = self.monitor().reset(D_WARN)
        self.assertFalse(output.stl_unsafe)
        self.assertFalse(output.stl_warning_trigger)

    def test_safe_equality_recovers(self) -> None:
        monitor = self.monitor()
        monitor.reset(0.29)
        output = monitor.step(D_SAFE)
        self.assertTrue(output.stl_safe)
        self.assertTrue(output.stl_recovery)
        self.assertEqual(output.stl_cost, 0)

    def test_recovery_one_step_after_trigger(self) -> None:
        monitor = self.monitor()
        monitor.reset(0.29)
        output = monitor.step(0.60)
        self.assertTrue(output.stl_recovery)
        self.assertEqual(output.sample_index, 1)

    def test_recovery_exactly_on_deadline(self) -> None:
        monitor = self.monitor()
        monitor.reset(0.29)
        monitor.step(0.40)
        monitor.step(0.40)
        output = monitor.step(0.50)
        self.assertEqual(output.sample_index, K)
        self.assertTrue(output.stl_recovery)
        self.assertFalse(output.stl_deadline_violation)

    def test_first_recovery_after_deadline_is_late(self) -> None:
        monitor = self.monitor()
        monitor.reset(0.29)
        monitor.step(0.40)
        monitor.step(0.40)
        violation = monitor.step(0.40)
        recovery = monitor.step(0.50)
        self.assertTrue(violation.stl_deadline_violation)
        self.assertEqual(violation.stl_cost, 1)
        self.assertTrue(recovery.stl_late_recovery)
        self.assertEqual(recovery.stl_cost, 0)

    def test_remaining_unsafe_after_deadline_emits_one_violation(self) -> None:
        monitor = self.monitor()
        outputs = [monitor.reset(0.29)] + [monitor.step(0.29) for _ in range(8)]
        self.assertEqual(sum(output.stl_deadline_violation for output in outputs), 1)
        self.assertEqual(sum(output.stl_cost for output in outputs), 1)
        self.assertEqual(monitor.deadline_violation_count, 1)

    def test_hysteresis_band_keeps_obligation_pending(self) -> None:
        monitor = self.monitor()
        monitor.reset(0.29)
        output = monitor.step(0.40)
        self.assertEqual(output.stl_status, MonitorState.PENDING.value)
        self.assertFalse(output.stl_recovery)

    def test_reentry_while_pending_does_not_retrigger(self) -> None:
        monitor = self.monitor()
        outputs = [monitor.reset(0.29), monitor.step(0.40), monitor.step(0.29)]
        self.assertEqual(sum(output.stl_warning_trigger for output in outputs), 1)
        self.assertEqual(monitor.trigger_count, 1)

    def test_recover_then_enter_again_creates_two_episodes(self) -> None:
        monitor = self.monitor()
        outputs = [monitor.reset(0.29), monitor.step(0.50), monitor.step(0.29)]
        self.assertEqual(sum(output.stl_warning_trigger for output in outputs), 2)
        self.assertEqual(monitor.trigger_count, 2)
        self.assertEqual(outputs[-1].stl_episode_id, 2)

    def test_truncate_before_deadline_is_unresolved_cost(self) -> None:
        monitor = self.monitor()
        monitor.reset(0.29)
        output = monitor.step(0.40, truncated=True)
        self.assertTrue(output.stl_terminal_unresolved)
        self.assertFalse(output.stl_deadline_violation)
        self.assertEqual(output.stl_cost, 1)
        with self.assertRaises(RuntimeError):
            monitor.step(0.40)

    def test_terminate_on_deadline_has_no_duplicate_unresolved(self) -> None:
        monitor = self.monitor()
        monitor.reset(0.29)
        monitor.step(0.40)
        monitor.step(0.40)
        output = monitor.step(0.40, terminated=True)
        self.assertTrue(output.stl_deadline_violation)
        self.assertFalse(output.stl_terminal_unresolved)
        self.assertEqual(output.stl_cost, 1)

    def test_recover_on_final_sample_before_truncation(self) -> None:
        monitor = self.monitor()
        monitor.reset(0.29)
        output = monitor.step(0.50, truncated=True)
        self.assertTrue(output.stl_recovery)
        self.assertFalse(output.stl_terminal_unresolved)
        self.assertEqual(output.stl_cost, 0)

    def test_vectorized_environments_are_independent(self) -> None:
        first = self.monitor()
        second = self.monitor()
        first.reset(0.29)
        second.reset(0.60)
        first.step(0.40)
        second.step(0.60)
        self.assertEqual(first.state, MonitorState.PENDING)
        self.assertEqual(second.state, MonitorState.INACTIVE)
        self.assertEqual(first.trigger_count, 1)
        self.assertEqual(second.trigger_count, 0)

    def test_reset_clears_prior_state_and_counters(self) -> None:
        monitor = self.monitor()
        monitor.reset(0.29)
        monitor.step(0.40, truncated=True)
        output = monitor.reset(0.60)
        self.assertEqual(output.sample_index, 0)
        self.assertEqual(monitor.state, MonitorState.INACTIVE)
        self.assertEqual(monitor.trigger_count, 0)
        self.assertEqual(monitor.unresolved_count, 0)

    def test_invalid_parameters_and_terminal_flags(self) -> None:
        with self.assertRaises(ValueError):
            BoundedRecoveryMonitor(0.2, 0.5, 3)
        with self.assertRaises(ValueError):
            BoundedRecoveryMonitor(0.5, 0.5, 3)
        with self.assertRaises(ValueError):
            BoundedRecoveryMonitor(0.3, 0.5, 0)
        monitor = self.monitor()
        monitor.reset(0.60)
        with self.assertRaises(ValueError):
            monitor.step(0.60, terminated=True, truncated=True)


if __name__ == "__main__":
    unittest.main()
