"""Tests for the deterministic Stage II controlled-grammar sanity baseline."""

from __future__ import annotations

import unittest

from safety_stl.stage2_benchmark import BENCHMARK_ROOT, validate_benchmark_contract
from safety_stl.stage2_grammar import ControlledGrammarParser


class Stage2GrammarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.specifications = validate_benchmark_contract(BENCHMARK_ROOT)["specifications"]
        cls.parser = ControlledGrammarParser(cls.specifications)

    def test_all_120_registered_wordings_parse_exactly(self) -> None:
        count = 0
        for spec in self.specifications:
            for language in [spec["canonical_natural_language"], *spec["paraphrases"]]:
                self.assertEqual(self.parser.parse(language), spec["typed_ast"])
                count += 1
        self.assertEqual(count, 120)

    def test_out_of_registry_language_is_rejected_without_repair(self) -> None:
        with self.assertRaises(ValueError):
            self.parser.parse("Stay safe near the hazard.")


if __name__ == "__main__":
    unittest.main()
