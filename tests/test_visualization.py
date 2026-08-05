"""Tests for the runnable Stage I visualization surface."""

from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

import numpy as np

from safety_stl.monitor import MonitorOutput
from safety_stl.visualization import (
    DEFAULT_CONFIG_PATH,
    DemoOptions,
    RunTotals,
    annotate_frame,
    build_log_row,
    load_rule_config,
    run_demo,
)


def inactive_output(distance: float = 0.8) -> MonitorOutput:
    """Return one representative output without duplicating monitor logic."""

    return MonitorOutput(
        sample_index=0,
        stl_distance=distance,
        stl_unsafe=False,
        stl_safe=True,
        stl_status="inactive",
        stl_warning_trigger=False,
        stl_recovery=False,
        stl_late_recovery=False,
        stl_deadline_violation=False,
        stl_terminal_unresolved=False,
        stl_trigger_step=None,
        stl_deadline_step=None,
        stl_elapsed_steps=None,
        stl_remaining_steps=None,
        stl_cost=0,
        stl_episode_id=0,
        terminated=False,
        truncated=False,
    )


class VisualizationUnitTests(unittest.TestCase):
    def test_fixed_rule_config_loads(self) -> None:
        config = load_rule_config(DEFAULT_CONFIG_PATH)
        self.assertEqual(config["environment_id"], "SafetyPointGoal1-v0")
        self.assertEqual(config["d_warn"], 0.45)
        self.assertEqual(config["d_safe"], 0.55)
        self.assertEqual(config["deadline_steps"], 79)

    def test_annotated_frame_preserves_simulator_pixels_and_adds_panel(self) -> None:
        frame = np.full((240, 320, 3), 127, dtype=np.uint8)
        annotated = annotate_frame(
            frame,
            inactive_output(),
            RunTotals(reward=1.25, native_cost=2.0, stl_cost=1),
            policy="scripted",
            phase="escape",
            d_warn=0.45,
            d_safe=0.55,
        )
        self.assertEqual(annotated.shape, (390, 660, 3))
        np.testing.assert_array_equal(annotated[:240, :320], frame)
        self.assertFalse(np.all(annotated[:, 320:] == 127))

    def test_log_row_keeps_native_and_stl_cost_separate(self) -> None:
        totals = RunTotals(reward=0.5, native_cost=3.0, stl_cost=1)
        row = build_log_row(
            output=inactive_output(),
            action_index=4,
            action=np.asarray([0.2, -0.1]),
            seed=44,
            policy="scripted",
            phase="escape",
            reward=0.5,
            native_cost=1.0,
            info={"cost_hazards": 1.0},
            totals=totals,
        )
        self.assertEqual(row["reward"], 0.5)
        self.assertEqual(row["native_cost"], 1.0)
        self.assertEqual(row["stl_cost"], 0)
        self.assertEqual(row["cumulative_native_cost"], 3.0)
        self.assertEqual(row["cumulative_stl_cost"], 1)

    def test_real_environment_headless_smoke_writes_artifacts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="stl-visualization-test-") as directory:
            output_dir = Path(directory)
            options = DemoOptions(
                config_path=DEFAULT_CONFIG_PATH,
                output_dir=output_dir,
                render="none",
                policy="random",
                seed=7,
                max_steps=2,
                width=320,
                height=240,
                fps=30,
                camera_name="fixedfar",
                status_interval=10,
            )
            summary = run_demo(options)
            self.assertEqual(summary["actions"], 2)
            self.assertEqual(summary["samples"], 3)
            self.assertEqual(summary["render_mode"], "none")
            self.assertTrue((output_dir / "summary.json").is_file())
            with (output_dir / "trajectory.csv").open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 3)
            self.assertIn("native_cost", rows[1])
            self.assertIn("stl_cost", rows[1])


if __name__ == "__main__":
    unittest.main()
