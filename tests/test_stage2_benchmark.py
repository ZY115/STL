"""Tests for the frozen D37 Stage II v0 benchmark contract."""

from __future__ import annotations

import copy
import unittest
from collections import Counter

from safety_stl.stage2_benchmark import (
    BENCHMARK_ROOT,
    generate_synthetic,
    parameter_contrast_coverage,
    validate_benchmark_contract,
    validate_trajectories,
)
from safety_stl.stage2_specifications import build_specifications, compile_typed_ast


class Stage2BenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = validate_benchmark_contract(BENCHMARK_ROOT)
        cls.records = generate_synthetic(cls.contract["specifications"])

    def test_d37_forty_item_contract_and_split_are_exact(self) -> None:
        self.assertEqual(self.contract["specification_count"], 40)
        self.assertEqual(self.contract["semantic_pair_split_leakage_count"], 0)
        self.assertEqual(set(self.contract["family_counts"].values()), {8})
        self.assertEqual(
            self.contract["split_counts"],
            {"train": 20, "validation": 8, "parameter_test": 4, "structure_test": 8},
        )
        reviews = Counter(review["status"] for review in self.contract["reviews"])
        self.assertEqual(reviews, {"approved": 40})
        self.assertTrue(self.contract["all_held_out_reviewed"])

    def test_materialized_matrix_exactly_matches_frozen_builder(self) -> None:
        expected = {row["spec_id"]: row for row in build_specifications()}
        actual = {row["spec_id"]: row for row in self.contract["specifications"]}
        for spec_id, record in actual.items():
            self.assertEqual(record["typed_ast"], expected[spec_id]["typed_ast"])
            self.assertEqual(record["gold_stl"], compile_typed_ast(record["typed_ast"]))
            self.assertEqual(len(record["paraphrases"]), 2)

    def test_all_boundary_gold_labels_have_direct_rtamt_agreement(self) -> None:
        result = validate_trajectories(self.records, self.contract["specifications"])
        self.assertGreaterEqual(result["trajectory_count"], 40 * 12)
        self.assertTrue(result["all_online_oracle_agree"])
        self.assertLessEqual(result["rtamt_max_robustness_difference"], 1e-9)
        self.assertEqual(result["history_pairs_checked"], 40)

    def test_recovery_temporal_boundaries(self) -> None:
        first_spec = [row for row in self.records if row["spec_id"] == "br-v0-001"]
        by_case = {record["source"]["case_id"]: record for record in first_spec}
        exact = by_case["exact_deadline_recovery"]["gold_labels"]["oracle"]
        late = by_case["one_step_late"]["gold_labels"]["oracle"]
        terminal = by_case["terminal_unresolved"]["gold_labels"]["oracle"]
        warning_equal = by_case["warning_equality_no_trigger"]["gold_labels"]["oracle"]
        self.assertEqual(exact["deadline_violation_count"], 0)
        self.assertEqual(exact["recovery_count"], 1)
        self.assertEqual(late["deadline_violation_count"], 1)
        self.assertEqual(terminal["unresolved_count"], 1)
        self.assertEqual(warning_equal["trigger_count"], 0)

    def test_persistence_and_boolean_witnesses_exist(self) -> None:
        for family in ("rp", "and", "or"):
            records = [row for row in self.records if row["spec_id"].startswith(family)]
            tags = {tag for row in records for tag in row["case_tags"]}
            self.assertIn("persistence_break_first", tags)
            self.assertIn("persistence_break_middle", tags)
            self.assertIn("persistence_break_final", tags)
        boolean_records = [
            row
            for row in self.records
            if row["spec_id"].startswith(("and", "or"))
        ]
        self.assertTrue(
            any("boolean_distinguishing_witness" in row["case_tags"] for row in boolean_records),
        )

    def test_history_pair_has_same_observation_and_different_gold_state(self) -> None:
        pair = [
            record
            for record in self.records
            if record["history_pair_id"] == "rp-v0-001__history-state-contrast"
        ]
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

    def test_contrast_coverage_reports_frozen_logical_aliases(self) -> None:
        coverage = parameter_contrast_coverage(
            self.contract["specifications"],
            self.records,
        )
        self.assertEqual(coverage["required_pair_count"], 115)
        self.assertEqual(coverage["missing_witness_count"], 6)
        self.assertEqual(coverage["unclassified_missing_witness_count"], 0)
        self.assertTrue(coverage["all_non_alias_pairs_have_distinguishing_trace"])


if __name__ == "__main__":
    unittest.main()
