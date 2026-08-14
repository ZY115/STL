"""Tests for the fixed Stage II real-policy corpus selection and review gate."""

from __future__ import annotations

import csv
import json
import unittest
from pathlib import Path

from safety_stl.stage2_benchmark import BENCHMARK_ROOT, validate_benchmark_contract
from safety_stl.stage2_real_corpus import STRATA, select_stratified_real_episodes


class Stage2RealCorpusTests(unittest.TestCase):
    def test_frozen_episode_table_produces_exact_stratified_sixty(self) -> None:
        with Path("results/stage1_pilot/analysis/episode_records.csv").open(
            "r",
            newline="",
            encoding="utf-8",
        ) as handle:
            selected = select_stratified_real_episodes(list(csv.DictReader(handle)))
        self.assertEqual(len(selected), 60)
        self.assertEqual({row["outcome_stratum"] for row in selected}, set(STRATA))
        for condition in ("task_only", "native_cost", "gold_stl_cost"):
            rows = [row for row in selected if row["condition"] == condition]
            self.assertEqual(len(rows), 20)
            for training_seed in (1101, 2202, 3303, 4404, 5505):
                seed_rows = [row for row in rows if row["training_seed"] == training_seed]
                self.assertEqual({row["outcome_stratum"] for row in seed_rows}, set(STRATA))

    def test_current_held_out_alias_amendment_gate_is_closed(self) -> None:
        contract = validate_benchmark_contract(BENCHMARK_ROOT)
        held_out = [
            spec
            for spec in contract["specifications"]
            if spec["split"] in {"parameter_test", "structure_test"}
        ]
        self.assertEqual(len(held_out), 12)
        self.assertTrue(all(spec["review_status"] == "independently_reviewed" for spec in held_out))
        coverage = json.loads(
            (BENCHMARK_ROOT / "generated" / "coverage.json").read_text(encoding="utf-8"),
        )
        self.assertGreater(
            coverage["parameter_contrast_coverage"]["missing_witness_count"],
            0,
        )

    def test_real_corpus_machine_checks_all_specs_but_releases_only_train_validation(self) -> None:
        manifest = json.loads(
            Path("benchmarks/stage2_v0/generated/real_corpus_manifest.json").read_text(
                encoding="utf-8",
            ),
        )
        self.assertEqual(manifest["trajectory_count"], 60)
        self.assertEqual(manifest["machine_review_label_record_count"], 2400)
        self.assertEqual(manifest["label_record_count"], 1680)
        self.assertEqual(manifest["labeled_splits"], ["train", "validation"])
        self.assertFalse(manifest["held_out_labels_released"])


if __name__ == "__main__":
    unittest.main()
