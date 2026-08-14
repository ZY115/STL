"""Focused contracts for the D43 runner without launching training."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import yaml

from safety_stl.fixed_route_quick_turn import (
    DEFAULT_PROTOCOL,
    build_config,
    derive_task_budgets,
    load_contract,
    require_hardware_gate,
)


class FixedRouteQuickTurnTests(unittest.TestCase):
    def test_contract_and_all_three_configs_bind_fixed_rule(self) -> None:
        protocol, scenario, rule = load_contract(DEFAULT_PROTOCOL)
        self.assertEqual(protocol["training"]["training_seed"], 9173)
        for condition in protocol["training"]["condition_order"]:
            config = build_config(
                protocol,
                scenario,
                rule,
                condition,
                10_000,
                0.0,
                Path("/tmp/fixed-route-unit") / condition,
                update_iters=1,
            )
            self.assertEqual(config.train_cfgs.epochs, 1)
            self.assertEqual(config.train_cfgs.vector_env_nums, 10)
            self.assertFalse(config.env_cfgs.asynchronous)
            self.assertEqual(Path(config.env_cfgs.rule_config_path), rule)

    def test_missing_hardware_gate_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "D41 blocks training"):
                require_hardware_gate(Path(directory) / "missing.json")

    def test_explicit_admin_override_is_scoped_to_d43(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            override = root / "override.yaml"
            override.write_text(
                yaml.safe_dump(
                    {
                        "status": "administrator_risk_override",
                        "scope": {"protocol_id": "fixed_route_v1_quick_turn"},
                        "acknowledgements": {
                            "prior_mce_and_segfault_risk_accepted_for_this_bounded_run": True,
                        },
                    },
                ),
                encoding="utf-8",
            )
            gate = require_hardware_gate(root / "missing.json", override_path=override)
            self.assertEqual(gate["gate_mode"], "administrator_risk_override")

    def test_task_budget_units_are_derived_separately(self) -> None:
        episodes = [
            {"native_cost_total": float(index + 1)}
            for index in range(20)
        ]
        trajectories = []
        for episode in range(20):
            trajectories.append(
                {
                    "episode_index": episode,
                    "evaluation_seed": 29173 + episode,
                    "action_index": 0,
                    "stl_cost": 0,
                    "monitor_state": "pending",
                    "remaining_steps": 25,
                    "distance": 0.24,
                },
            )
        budgets = derive_task_budgets(
            episodes,
            trajectories,
            {"d_warn": 0.25, "d_safe": 0.28, "deadline_steps": 25},
        )
        self.assertEqual(budgets["episode_count"], 20)
        self.assertAlmostEqual(budgets["cost_limit"]["native_cost_per_episode"], 7.35)
        self.assertNotEqual(
            budgets["cost_limit"]["native_cost_per_episode"],
            budgets["cost_limit"]["c1_surrogate_mass_per_episode"],
        )


if __name__ == "__main__":
    unittest.main()
