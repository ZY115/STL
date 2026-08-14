"""Contracts for the D47 long C1 dense round without launching training."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import yaml

from safety_stl.fixed_route_quick_turn import (
    build_config,
    cost_routing_diagnostics,
    load_contract,
    require_hardware_gate,
)


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/fixed_route_v1/full_dense_round.yaml"


class FixedRouteFullDenseRoundTests(unittest.TestCase):
    def test_float32_logger_ulp_does_not_create_false_routing_failure(self) -> None:
        rows = [
            {
                "Metrics/SelectedAlgorithmCost": 42.27627944946289,
                "Metrics/STLDenseCost": 42.276275634765625,
            },
        ]
        accepted = cost_routing_diagnostics(rows, "Metrics/STLDenseCost")
        self.assertTrue(accepted["passed"])
        self.assertAlmostEqual(accepted["maximum_absolute_error"], 3.814697265625e-6)
        rejected = cost_routing_diagnostics(
            [
                {
                    "Metrics/SelectedAlgorithmCost": 42.286,
                    "Metrics/STLDenseCost": 42.276,
                },
            ],
            "Metrics/STLDenseCost",
        )
        self.assertFalse(rejected["passed"])

    def test_long_contract_is_one_new_matched_seed_and_c1(self) -> None:
        protocol, scenario, rule = load_contract(
            PROTOCOL,
            expected_protocol_id="fixed_route_v1_full_dense_round",
            expected_authority="D47",
        )
        self.assertEqual(protocol["training"]["training_seed"], 12647)
        self.assertEqual(protocol["training"]["transitions_per_condition"], 1_000_000)
        self.assertEqual(protocol["evaluation"]["stochastic_summary_episodes_per_condition"], 100)
        self.assertEqual(
            protocol["conditions"]["stl_dense_safety"]["selected_learner_cost"],
            "c1_causal_dense_surrogate",
        )
        config = build_config(
            protocol,
            scenario,
            rule,
            "stl_dense_safety",
            1_000_000,
            1.0,
            Path("/tmp/fixed-route-full-dense-test"),
        )
        self.assertEqual(config.train_cfgs.epochs, 100)
        self.assertEqual(config.algo_cfgs.update_iters, 40)
        self.assertEqual(str(config.env_id), "Stage2SafetyPointGoal1STLDenseCost-v0")

    def test_long_override_cannot_authorize_quick_turn_or_another_protocol(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            override = root / "override.yaml"
            override.write_text(
                yaml.safe_dump(
                    {
                        "status": "administrator_risk_override",
                        "scope": {"protocol_id": "fixed_route_v1_full_dense_round"},
                        "acknowledgements": {
                            "prior_mce_and_segfault_risk_accepted_for_this_bounded_run": True,
                        },
                    },
                ),
                encoding="utf-8",
            )
            gate = require_hardware_gate(
                root / "missing.json",
                override_path=override,
                protocol_id="fixed_route_v1_full_dense_round",
            )
            self.assertEqual(gate["gate_mode"], "administrator_risk_override")
            with self.assertRaisesRegex(RuntimeError, "D41 blocks training"):
                require_hardware_gate(
                    root / "missing.json",
                    override_path=override,
                    protocol_id="fixed_route_v1_quick_turn",
                )


if __name__ == "__main__":
    unittest.main()
