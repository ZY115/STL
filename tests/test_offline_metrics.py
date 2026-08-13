"""Tests for Stage II offline trace metrics."""

from __future__ import annotations

import unittest

from safety_stl.offline_metrics import evaluate_predictions
from safety_stl.stage2_benchmark import BENCHMARK_ROOT, generate_synthetic, validate_benchmark_contract


class OfflineMetricsTests(unittest.TestCase):
    def setUp(self) -> None:
        contract = validate_benchmark_contract(BENCHMARK_ROOT)
        self.specifications = contract["specifications"]
        self.trajectories = generate_synthetic(self.specifications)[:11]

    def _perfect_predictions(self):
        rows = []
        for trajectory in self.trajectories:
            costs = [sample["stl_cost"] for sample in trajectory["samples"]]
            states = trajectory["gold_labels"]["online"]["states"]
            rows.append(
                {
                    "method_id": "unit-test",
                    "trajectory_id": trajectory["trajectory_id"],
                    "language_variant": "canonical",
                    "predicted_costs": costs,
                    "predicted_event_steps": [i for i, value in enumerate(costs) if value],
                    "predicted_active_obligation": [int(state in {"pending", "overdue"}) for state in states],
                    "predicted_stl": self.specifications[0]["gold_stl"],
                    "predicted_structure": self.specifications[0]["typed_ast"],
                },
            )
        return rows

    def test_perfect_predictions_score_one_on_available_metrics(self) -> None:
        metrics = evaluate_predictions(
            self._perfect_predictions(),
            self.trajectories,
            self.specifications,
        )
        self.assertEqual(metrics["trace_cost"]["f1"], 1.0)
        self.assertEqual(metrics["boundary_accuracy"], 1.0)
        self.assertEqual(metrics["terminal_unresolved_accuracy"], 1.0)
        self.assertEqual(metrics["history_state_minimal_pair_accuracy"], 1.0)
        self.assertEqual(metrics["formula"]["syntax_validity"], 1.0)
        self.assertEqual(metrics["formula"]["exact_match"], 1.0)
        self.assertEqual(metrics["structured_meaning"]["exact_record_accuracy"], 1.0)

    def test_false_negative_is_counted(self) -> None:
        predictions = self._perfect_predictions()
        target = next(row for row in predictions if any(row["predicted_costs"]))
        target["predicted_costs"] = [0] * len(target["predicted_costs"])
        target["predicted_event_steps"] = []
        metrics = evaluate_predictions(predictions, self.trajectories, self.specifications)
        self.assertGreater(metrics["trace_cost"]["false_negative"], 0)
        self.assertGreater(metrics["event_timing"]["unmatched_gold_event_count"], 0)

    def test_rejects_future_or_out_of_range_event_step(self) -> None:
        predictions = self._perfect_predictions()
        predictions[0]["predicted_event_steps"] = [len(predictions[0]["predicted_costs"])]
        with self.assertRaises(ValueError):
            evaluate_predictions(predictions, self.trajectories, self.specifications)


if __name__ == "__main__":
    unittest.main()
