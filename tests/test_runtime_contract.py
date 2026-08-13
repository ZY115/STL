"""Regression tests for effective OmniSafe semantics used by the pilot."""

from __future__ import annotations

import unittest

import torch
from gymnasium import spaces
from omnisafe.common.buffer.onpolicy_buffer import OnPolicyBuffer

from safety_stl.runtime_contract import inspect_runtime_contract, probe_timeout_cost_bootstrap


class RuntimeContractTests(unittest.TestCase):
    def test_terminal_unresolved_timeout_bootstraps_cost_value(self) -> None:
        probe = probe_timeout_cost_bootstrap()
        self.assertTrue(probe["terminal_unresolved"])
        self.assertTrue(probe["omnisafe_timeout_bootstraps_cost_value"])
        self.assertTrue(probe["semantic_mismatch"])
        self.assertEqual(probe["observed_last_value_c"], 7.0)
        self.assertEqual(probe["project_episode_settlement_requires_last_value_c"], 0.0)

    def test_cost_advantage_is_centered_but_not_zscored(self) -> None:
        buffer = OnPolicyBuffer(
            obs_space=spaces.Box(-1.0, 1.0, shape=(2,)),
            act_space=spaces.Box(-1.0, 1.0, shape=(1,)),
            size=4,
            gamma=0.99,
            lam=0.95,
            lam_c=0.95,
            advantage_estimator="gae",
            standardized_adv_r=True,
            standardized_adv_c=True,
        )
        reward_adv = torch.tensor([1.0, 2.0, 3.0, 4.0])
        cost_adv = torch.tensor([1.0, 3.0, 9.0, 20.0])
        buffer.data["adv_r"].copy_(reward_adv)
        buffer.data["adv_c"].copy_(cost_adv)
        data = buffer.get()
        self.assertAlmostEqual(float(data["adv_r"].mean()), 0.0, places=6)
        self.assertAlmostEqual(float(data["adv_r"].std(unbiased=False)), 1.0, places=5)
        self.assertAlmostEqual(float(data["adv_c"].mean()), 0.0, places=6)
        self.assertTrue(torch.allclose(data["adv_c"], cost_adv - cost_adv.mean()))
        self.assertGreater(float(data["adv_c"].std(unbiased=False)), 1.0)

    def test_declared_and_effective_contract_is_explicit(self) -> None:
        contract = inspect_runtime_contract()
        window = contract["episode_cost_window"]
        self.assertEqual(window["declared_logger_window_lens"], 100)
        self.assertEqual(window["effective_metrics_epcost_window"], 50)
        self.assertFalse(window["declaration_matches_runtime"])
        discount = contract["discount"]
        self.assertFalse(discount["onpolicy_init_reads_cost_gamma"])
        self.assertTrue(discount["onpolicy_init_uses_shared_gamma"])
        self.assertEqual(discount["current_numeric_difference"], 0.0)
        transform = contract["advantage_transform"]
        self.assertTrue(transform["effective_reward_zscore"])
        self.assertTrue(transform["effective_cost_mean_center_only"])
        schedule = contract["optimization_schedule"]
        self.assertEqual(schedule["epoch_count"], 100)
        self.assertEqual(schedule["actor_lr_after_final_scheduler_step"], 0.0)
        self.assertIsNone(schedule["nonzero_lr_floor"])
        self.assertTrue(schedule["lagrange_update_reads_metrics_epcost"])
        self.assertEqual(schedule["lagrange_effective_episode_window"], 50)


if __name__ == "__main__":
    unittest.main()
