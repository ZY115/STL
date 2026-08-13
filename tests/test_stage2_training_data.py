"""Tests for frozen, leakage-safe Stage II-A synthetic training data."""

from __future__ import annotations

import unittest
from collections import Counter

from safety_stl.stage2_benchmark import BENCHMARK_ROOT, validate_benchmark_contract
from safety_stl.stage2_training_data import (
    GENERATION_SEED,
    generate_direct_traces,
    generate_formal_training_pairs,
)


class Stage2TrainingDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.specifications = validate_benchmark_contract(BENCHMARK_ROOT)["specifications"]
        cls.formal = generate_formal_training_pairs(cls.specifications)
        cls.direct_train = generate_direct_traces(cls.specifications, split="train")
        cls.direct_validation = generate_direct_traces(cls.specifications, split="validation")

    def test_formal_pairs_are_exact_scale_and_train_only(self) -> None:
        self.assertEqual(len(self.formal), 10000)
        self.assertEqual({row["split"] for row in self.formal}, {"train"})
        self.assertFalse(any(row["spec_id"].startswith("or-") for row in self.formal))
        self.assertTrue(all(row["generation_seed"] == GENERATION_SEED for row in self.formal))
        self.assertEqual(len({row["controlled_natural_language"] for row in self.formal}), 10000)

    def test_direct_train_and_validation_have_exact_balanced_counts(self) -> None:
        for records, expected_count, expected_split in (
            (self.direct_train, 2000, "train"),
            (self.direct_validation, 400, "validation"),
        ):
            self.assertEqual(len(records), expected_count)
            self.assertEqual({row["split"] for row in records}, {expected_split})
            classes = Counter(row["positive_event_case"] for row in records)
            self.assertEqual(classes[True], expected_count // 2)
            self.assertEqual(classes[False], expected_count // 2)
            self.assertFalse(any(row["spec_id"].startswith("or-") for row in records))

    def test_direct_sequences_are_causal_length_128_and_gold_consistent(self) -> None:
        for record in [*self.direct_train[:20], *self.direct_validation[:20]]:
            self.assertEqual(len(record["distances"]), 128)
            self.assertEqual(len(record["gold_costs"]), 128)
            self.assertEqual(len(record["gold_active_obligation"]), 128)
            self.assertEqual(len(record["gold_remaining_fraction"]), 128)
            self.assertEqual(bool(sum(record["gold_costs"])), record["positive_event_case"])


if __name__ == "__main__":
    unittest.main()
