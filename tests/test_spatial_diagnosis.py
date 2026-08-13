"""Tests for deterministic Stage I spatial replay helpers."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from safety_stl.spatial_diagnosis import (
    SpatialAccumulator,
    geometry_snapshot,
    sampled_layout_fractions,
    select_median_paired_case,
    verify_replay_artifacts,
)


class SpatialDiagnosisTests(unittest.TestCase):
    def test_median_case_uses_absolute_difference_then_seed_tie_break(self) -> None:
        rows = []
        for training_seed in (1101, 2202, 3303, 4404, 5505):
            for evaluation_seed in range(10000, 10100):
                task_missed = 1
                gold_missed = 3
                if (training_seed, evaluation_seed) in {(1101, 10002), (2202, 10001)}:
                    gold_missed = 1
                for condition, missed in (
                    ("task_only", task_missed),
                    ("gold_stl_cost", gold_missed),
                ):
                    rows.append(
                        {
                            "condition": condition,
                            "training_seed": training_seed,
                            "evaluation_seed": evaluation_seed,
                            "deadline_violation_count": missed,
                            "terminal_unresolved_count": 0,
                        },
                    )
        selected = select_median_paired_case(rows)
        self.assertEqual(selected["training_seed"], 1101)
        self.assertEqual(selected["evaluation_seed"], 10002)
        self.assertEqual(selected["gold_minus_task_missed_obligations"], 0)

    def test_geometry_snapshot_matches_public_lidar_and_heading(self) -> None:
        hazards = [np.asarray([0.5, 0.0, 0.02])] + [
            np.asarray([1.0 + index, 1.0, 0.02]) for index in range(7)
        ]
        task = SimpleNamespace(
            agent=SimpleNamespace(
                pos=np.asarray([0.0, 0.0, 0.1]),
                mat=np.asarray([[0.0, -1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]]),
            ),
            hazards=SimpleNamespace(pos=hazards),
            goal=SimpleNamespace(pos=np.asarray([0.2, -0.3, 0.16])),
        )
        record = geometry_snapshot(
            task,
            {"hazards_lidar": np.asarray([1.0 - 0.5 / 3.0, 0.0])},
            None,
            goal_id=2,
        )
        self.assertEqual(record["nearest_hazard_id"], 0)
        self.assertAlmostEqual(record["public_lidar_distance"], 0.5)
        self.assertAlmostEqual(record["privileged_nearest_center_distance"], 0.5)
        self.assertAlmostEqual(record["agent_heading"], np.pi / 2)
        self.assertEqual(record["goal_id"], 2)

    def test_layout_fraction_is_ordered_by_radius(self) -> None:
        hazards = np.asarray(
            [
                [-1.0, -1.0],
                [-1.0, 0.0],
                [-1.0, 1.0],
                [0.0, -1.0],
                [0.0, 1.0],
                [1.0, -1.0],
                [1.0, 0.0],
                [1.0, 1.0],
            ],
        )
        result = sampled_layout_fractions(hazards, grid_size=51)
        self.assertGreater(
            result["outside_physical_radius_fraction"],
            result["outside_warning_radius_fraction"],
        )
        self.assertGreater(
            result["outside_warning_radius_fraction"],
            result["outside_safe_radius_fraction"],
        )

    def test_geometry_validation_respects_public_lidar_range_cap(self) -> None:
        hazards = [
            np.asarray([3.1 + index, 0.0, 0.02]) for index in range(8)
        ]
        task = SimpleNamespace(
            agent=SimpleNamespace(pos=np.asarray([0.0, 0.0, 0.1]), mat=np.eye(3)),
            hazards=SimpleNamespace(pos=hazards),
            goal=SimpleNamespace(pos=np.asarray([0.0, 0.0, 0.16])),
        )
        record = geometry_snapshot(
            task,
            {"hazards_lidar": np.asarray([0.0, 0.0])},
            None,
            goal_id=0,
        )
        self.assertEqual(record["public_lidar_distance"], 3.0)
        self.assertEqual(record["privileged_nearest_center_distance"], 3.1)

    def test_accumulator_keeps_events_and_band_metrics_separate(self) -> None:
        accumulator = SpatialAccumulator()
        base = {
            "condition": "task_only",
            "agent_x": 0.0,
            "agent_y": 0.0,
            "public_lidar_distance": 0.4,
            "privileged_nearest_center_distance": 0.4,
            "goal_met": False,
            "warning_trigger": True,
            "recovery": False,
            "deadline_violation": False,
            "terminal_unresolved": False,
            "sample_index": 0,
        }
        second = {
            **base,
            "agent_x": 0.1,
            "public_lidar_distance": 0.6,
            "privileged_nearest_center_distance": 0.6,
            "warning_trigger": False,
            "recovery": True,
            "sample_index": 1,
        }
        accumulator.add_row(base)
        accumulator.add_row(second)
        accumulator.add_episode("task_only", [base, second])
        result = accumulator.summary()["task_only"]
        self.assertEqual(result["warning_trigger_count"], 1)
        self.assertEqual(result["recovery_count"], 1)
        self.assertAlmostEqual(result["mean_path_length_per_episode"], 0.1)
        self.assertEqual(result["distance_band_crossings_per_episode"], 1)

    def test_artifact_verifier_rejects_hash_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = root / "artifact.txt"
            artifact.write_text("valid", encoding="utf-8")
            import hashlib

            digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
            (root / "replay_manifest.json").write_text(
                json.dumps(
                    {
                        "compact_artifacts": {
                            "artifact.txt": {"sha256": digest},
                        },
                    },
                ),
                encoding="utf-8",
            )
            verify_replay_artifacts(root)
            artifact.write_text("tampered", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                verify_replay_artifacts(root)


if __name__ == "__main__":
    unittest.main()
