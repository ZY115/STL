"""Tests for the reviewable Stage II v0 offline benchmark foundation."""

from __future__ import annotations

import copy
import unittest

from safety_stl.stage2_benchmark import (
    BENCHMARK_ROOT,
    generate_synthetic,
    parameter_contrast_coverage,
    validate_benchmark_contract,
    validate_trajectories,
)


class Stage2BenchmarkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = validate_benchmark_contract(BENCHMARK_ROOT)
        self.records = generate_synthetic(self.contract["specifications"])

    def test_contract_remains_unfrozen_and_uses_public_signal(self) -> None:
        self.assertEqual(self.contract["specification_count"], 5)
        self.assertEqual(self.contract["semantic_pair_split_leakage_count"], 0)
        self.assertEqual(
            self.contract["benchmark"]["draft_split_policy"]["status"],
            "unassigned_pending_o7_review",
        )
        self.assertEqual(len(self.contract["reviews"]), 5)
        self.assertTrue(all(review["status"] == "pending" for review in self.contract["reviews"]))

    def test_all_synthetic_gold_labels_have_three_way_agreement(self) -> None:
        result = validate_trajectories(self.records)
        self.assertEqual(result["trajectory_count"], 55)
        self.assertTrue(result["all_online_oracle_agree"])
        self.assertLessEqual(result["rtamt_max_robustness_difference"], 1e-9)
        self.assertEqual(result["history_pairs_checked"], 5)

    def test_temporal_boundary_cases(self) -> None:
        by_case = {record["source"]["case_id"]: record for record in self.records[:11]}
        exact = by_case["exact_deadline_recovery"]["gold_labels"]["oracle"]
        late = by_case["one_step_late"]["gold_labels"]["oracle"]
        terminal = by_case["terminal_unresolved"]["gold_labels"]["oracle"]
        warning_equal = by_case["warning_equality_no_trigger"]["gold_labels"]["oracle"]
        self.assertEqual(exact["deadline_violation_count"], 0)
        self.assertEqual(exact["recovery_count"], 1)
        self.assertEqual(late["deadline_violation_count"], 1)
        self.assertEqual(late["late_recovery_steps"], [81])
        self.assertEqual(terminal["unresolved_count"], 1)
        self.assertEqual(warning_equal["trigger_count"], 0)

    def test_history_pair_has_same_observation_and_different_gold_state(self) -> None:
        pair = [record for record in self.records[:11] if record["history_pair_id"]]
        self.assertEqual(len(pair), 2)
        anchor = int(pair[0]["history_anchor_step"])
        self.assertEqual(pair[0]["samples"][anchor]["distance"], pair[1]["samples"][anchor]["distance"])
        states = {record["gold_labels"]["online"]["states"][anchor] for record in pair}
        self.assertEqual(states, {"inactive", "pending"})

    def test_validator_recomputes_stored_gold_labels(self) -> None:
        corrupted = copy.deepcopy(self.records[:1])
        corrupted[0]["gold_labels"]["online"]["states"][0] = "pending"
        with self.assertRaises(ValueError):
            validate_trajectories(corrupted, self.contract["specifications"])

    def test_every_parameter_pair_has_a_trace_level_witness(self) -> None:
        coverage = parameter_contrast_coverage(
            self.contract["specifications"],
            self.records,
        )
        self.assertEqual(coverage["pair_count"], 10)
        self.assertTrue(coverage["all_pairs_have_distinguishing_trace"])


if __name__ == "__main__":
    unittest.main()
