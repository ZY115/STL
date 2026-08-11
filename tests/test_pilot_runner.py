"""Focused tests for the resumable Stage I pilot runner."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence

from safety_stl.pilot_protocol import load_and_validate_pilot
from safety_stl.pilot_runner import (
    ExistingRunError,
    ManifestMismatchError,
    PilotJob,
    enumerate_pilot_jobs,
    execute_job,
    select_fixed_final_checkpoint,
    sha256_file,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = REPOSITORY_ROOT / "configs" / "stage1_pilot" / "protocol.yaml"
OVERLAY_PATHS = {
    name: REPOSITORY_ROOT / "configs" / "stage1_pilot" / f"{name}.yaml"
    for name in ("task_only", "native_cost", "gold_stl_cost")
}


class PilotRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.protocol, cls.conditions = load_and_validate_pilot(
            PROTOCOL_PATH,
            list(OVERLAY_PATHS.values()),
        )

    def test_exact_fifteen_job_matrix_enumeration(self) -> None:
        jobs = enumerate_pilot_jobs(self.protocol["matched_design"]["training_seeds"])
        self.assertEqual(len(jobs), 15)
        self.assertEqual(jobs[0].job_id, "task_only__seed-1101")
        self.assertEqual(jobs[4].job_id, "task_only__seed-5505")
        self.assertEqual(jobs[5].job_id, "native_cost__seed-1101")
        self.assertEqual(jobs[-1].job_id, "gold_stl_cost__seed-5505")

    def test_fixed_final_checkpoint_does_not_select_later_or_best_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            save = run_dir / "torch_save"
            save.mkdir()
            for epoch in (1, 90, 100, 101):
                (save / f"epoch-{epoch}.pt").write_bytes(str(epoch).encode("ascii"))
            (save / "best.pt").write_bytes(b"best")
            selected = select_fixed_final_checkpoint(
                run_dir,
                total_steps=1_000_000,
                steps_per_epoch=10_000,
            )
            self.assertEqual(selected.name, "epoch-100.pt")

    @staticmethod
    def _mock_train(_: Mapping[str, Any], attempt_dir: Path) -> Dict[str, Any]:
        run_dir = attempt_dir / "training" / "mock-run"
        save = run_dir / "torch_save"
        save.mkdir(parents=True)
        progress = run_dir / "progress.csv"
        progress.write_text("TotalEnvSteps\n1000000\n", encoding="utf-8")
        checkpoint = save / "epoch-100.pt"
        checkpoint.write_bytes(b"fixed-final-checkpoint")
        return {
            "run_dir": str(run_dir),
            "progress": {"path": str(progress), "sha256": sha256_file(progress)},
            "final_checkpoint": {
                "path": str(checkpoint),
                "sha256": sha256_file(checkpoint),
            },
            "fixed_final_epoch": 100,
            "wall_clock_seconds": 1.0,
            "transitions_per_second": 1_000_000.0,
            "peak_gpu_memory_allocated_bytes": 1,
            "peak_gpu_memory_reserved_bytes": 1,
            "disk_bytes_at_training_completion": 1,
            "checks": {"mock": True},
        }

    @staticmethod
    def _mock_evaluate(
        _: Mapping[str, Any],
        seeds: Sequence[int],
        __: int,
        attempt_dir: Path,
    ) -> Dict[str, Any]:
        output = attempt_dir / "evaluation"
        output.mkdir()
        summary = output / "summary.json"
        episodes = output / "episodes.csv"
        summary.write_text(json.dumps({"agreement": True}) + "\n", encoding="utf-8")
        episodes.write_text("evaluation_seed\n" + "\n".join(map(str, seeds)) + "\n", encoding="utf-8")
        return {
            "summary": {"path": str(summary), "sha256": sha256_file(summary)},
            "episodes": {"path": str(episodes), "sha256": sha256_file(episodes)},
            "episode_count": len(seeds),
            "evaluation_seeds": list(seeds),
            "deterministic_policy": True,
            "gold_oracle_agreement": True,
            "rtamt_max_robustness_difference": 0.0,
            "aggregate": {},
        }

    def _execute(
        self,
        output: Path,
        *,
        resume: bool,
        overlay_path: Path = OVERLAY_PATHS["task_only"],
    ) -> Dict[str, Any]:
        return execute_job(
            job=PilotJob(1, "task_only", 1101),
            repository_root=REPOSITORY_ROOT,
            output_root=output,
            protocol=self.protocol,
            overlay=self.conditions["task_only"],
            protocol_path=PROTOCOL_PATH,
            overlay_path=overlay_path,
            evaluation_seeds=[10000, 10001],
            episode_horizon=1000,
            resume=resume,
            train_only=False,
            evaluate_only=False,
            train_function=self._mock_train,
            evaluation_function=self._mock_evaluate,
        )

    def test_completed_job_skip_and_no_accidental_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            first = self._execute(output, resume=False)
            self.assertEqual(first["action"], "completed")
            skipped = self._execute(output, resume=True)
            self.assertEqual(skipped["action"], "skipped_verified_success")
            with self.assertRaises(ExistingRunError):
                self._execute(output, resume=False)
            attempts = list(output.glob("jobs/task_only/seed-1101/attempts/attempt-*"))
            self.assertEqual(len(attempts), 1)

    def test_hash_mismatch_rejects_completed_job_skip(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            first = self._execute(output, resume=False)
            checkpoint = Path(first["manifest"]["final_checkpoint"]["path"])
            checkpoint.write_bytes(b"tampered")
            with self.assertRaises(ManifestMismatchError):
                self._execute(output, resume=True)

    def test_frozen_config_hash_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            overlay_copy = root / "task_only.yaml"
            overlay_copy.write_bytes(OVERLAY_PATHS["task_only"].read_bytes())
            output = root / "results"
            self._execute(output, resume=False, overlay_path=overlay_copy)
            overlay_copy.write_text(
                overlay_copy.read_text(encoding="utf-8") + "\n# changed after run\n",
                encoding="utf-8",
            )
            with self.assertRaises(ManifestMismatchError):
                self._execute(output, resume=True, overlay_path=overlay_copy)

    def test_interrupted_job_resumes_in_a_new_attempt(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            job_dir = output / "jobs" / "task_only" / "seed-1101"
            interrupted_attempt = job_dir / "attempts" / "attempt-0001"
            interrupted_attempt.mkdir(parents=True)
            state = {
                "schema_version": 1,
                "job_id": "task_only__seed-1101",
                "condition": "task_only",
                "training_seed": 1101,
                "attempt": 1,
                "attempt_dir": str(interrupted_attempt),
                "start_time_utc": "2026-08-11T00:00:00+00:00",
                "status": "running",
            }
            (job_dir / "state.json").write_text(json.dumps(state), encoding="utf-8")
            result = self._execute(output, resume=True)
            self.assertEqual(result["action"], "completed")
            self.assertTrue((interrupted_attempt / "interrupted_manifest.json").is_file())
            self.assertTrue((job_dir / "attempts" / "attempt-0002").is_dir())


if __name__ == "__main__":
    unittest.main()
