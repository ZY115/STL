"""Resumable execution support for the frozen Stage I pilot matrix."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import platform
import re
import subprocess
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from safety_stl.pilot_protocol import compose_omnisafe_config


CONDITION_ORDER = ("task_only", "native_cost", "gold_stl_cost")
REQUIRED_PROGRESS_METRICS = {
    "TotalEnvSteps",
    "Metrics/NativeCost",
    "Metrics/STLCost",
    "Metrics/SelectedAlgorithmCost",
    "Metrics/STLTriggers",
    "Metrics/STLDeadlineViolations",
    "Metrics/STLTerminalUnresolved",
    "Metrics/LagrangeMultiplier",
}


class ExistingRunError(RuntimeError):
    """Raised when execution would overwrite prior job evidence."""


class ManifestMismatchError(RuntimeError):
    """Raised when existing evidence does not match the current immutable inputs."""


@dataclass(frozen=True)
class PilotJob:
    """One condition/training-seed cell in the matched pilot matrix."""

    index: int
    condition: str
    seed: int

    @property
    def job_id(self) -> str:
        return f"{self.condition}__seed-{self.seed}"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json_hash(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256_bytes(encoded)


def installed_version(distribution: str) -> str:
    try:
        return metadata.version(distribution)
    except metadata.PackageNotFoundError:
        return "not-installed"


def git_revision(repository_root: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def git_worktree_clean(repository_root: Path) -> bool:
    completed = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return not completed.stdout.strip()


def source_tree_hash(repository_root: Path) -> str:
    """Hash the execution source independently of documentation-only changes."""

    candidates: List[Path] = []
    for relative in ("src", "scripts", "configs/stage1_pilot"):
        root = repository_root / relative
        if root.is_dir():
            candidates.extend(
                path
                for path in root.rglob("*")
                if path.is_file() and path.suffix in {".py", ".sh", ".yaml"}
            )
    digest = hashlib.sha256()
    for path in sorted(candidates):
        relative = path.relative_to(repository_root).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(bytes.fromhex(sha256_file(path)))
    return digest.hexdigest()


def write_json_atomic(path: Path, value: Mapping[str, Any], *, immutable: bool = False) -> None:
    """Write JSON atomically; immutable writes refuse an existing target."""

    path.parent.mkdir(parents=True, exist_ok=True)
    if immutable and path.exists():
        raise ExistingRunError(f"refusing to overwrite immutable file: {path}")
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    with temporary.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
    if immutable and path.exists():
        temporary.unlink()
        raise ExistingRunError(f"refusing to overwrite immutable file: {path}")
    temporary.replace(path)


def load_json_mapping(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, Mapping):
        raise ValueError(f"expected a JSON mapping: {path}")
    return dict(value)


def enumerate_pilot_jobs(
    training_seeds: Sequence[int],
    *,
    conditions: Optional[Sequence[str]] = None,
    seeds: Optional[Sequence[int]] = None,
) -> List[PilotJob]:
    """Enumerate condition-major jobs in one stable order."""

    selected_conditions = list(conditions) if conditions else list(CONDITION_ORDER)
    if len(set(selected_conditions)) != len(selected_conditions):
        raise ValueError("condition selection contains duplicates")
    unknown_conditions = set(selected_conditions) - set(CONDITION_ORDER)
    if unknown_conditions:
        raise ValueError(f"unknown conditions: {sorted(unknown_conditions)}")
    selected_conditions = [name for name in CONDITION_ORDER if name in selected_conditions]

    frozen_seeds = [int(seed) for seed in training_seeds]
    selected_seeds = [int(seed) for seed in seeds] if seeds else frozen_seeds
    if len(set(selected_seeds)) != len(selected_seeds):
        raise ValueError("seed selection contains duplicates")
    unknown_seeds = set(selected_seeds) - set(frozen_seeds)
    if unknown_seeds:
        raise ValueError(f"seeds are outside the frozen pilot: {sorted(unknown_seeds)}")
    selected_seeds = [seed for seed in frozen_seeds if seed in selected_seeds]

    jobs: List[PilotJob] = []
    for condition in selected_conditions:
        for seed in selected_seeds:
            jobs.append(PilotJob(len(jobs) + 1, condition, seed))
    return jobs


def read_progress_rows(path: Path) -> List[Dict[str, float]]:
    with path.open(newline="", encoding="utf-8") as handle:
        raw_rows = list(csv.DictReader(handle))
    return [
        {
            key: float(value)
            for key, value in row.items()
            if key is not None and value not in (None, "")
        }
        for row in raw_rows
    ]


def select_fixed_final_checkpoint(
    run_dir: Path,
    *,
    total_steps: int,
    steps_per_epoch: int,
) -> Path:
    """Select the declared final epoch, never a post-hoc best or highest checkpoint."""

    if total_steps <= 0 or steps_per_epoch <= 0 or total_steps % steps_per_epoch:
        raise ValueError("total_steps must be a positive whole number of epochs")
    final_epoch = total_steps // steps_per_epoch
    checkpoint = run_dir / "torch_save" / f"epoch-{final_epoch}.pt"
    if not checkpoint.is_file():
        raise FileNotFoundError(f"fixed final checkpoint is missing: {checkpoint}")
    return checkpoint


def routing_checks(condition: str, rows: Sequence[Mapping[str, float]]) -> Dict[str, bool]:
    if condition == "task_only":
        exact = all(
            math.isclose(row["Metrics/SelectedAlgorithmCost"], 0.0, abs_tol=1e-9)
            for row in rows
        )
    elif condition == "native_cost":
        exact = all(
            math.isclose(
                row["Metrics/SelectedAlgorithmCost"],
                row["Metrics/NativeCost"],
                rel_tol=0.0,
                abs_tol=1e-9,
            )
            for row in rows
        )
    elif condition == "gold_stl_cost":
        exact = all(
            math.isclose(
                row["Metrics/SelectedAlgorithmCost"],
                row["Metrics/STLCost"],
                rel_tol=0.0,
                abs_tol=1e-9,
            )
            for row in rows
        )
    else:
        raise ValueError(f"unknown condition: {condition}")
    return {"selected_cost_routing_exact_every_epoch": exact}


def directory_size(path: Path) -> int:
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def next_attempt_dir(job_dir: Path) -> Tuple[int, Path]:
    attempts = job_dir / "attempts"
    attempts.mkdir(parents=True, exist_ok=True)
    numbers = []
    for path in attempts.glob("attempt-*"):
        match = re.fullmatch(r"attempt-(\d+)", path.name)
        if match:
            numbers.append(int(match.group(1)))
    number = max(numbers, default=0) + 1
    path = attempts / f"attempt-{number:04d}"
    path.mkdir()
    return number, path


def _hash_record(path: Path) -> Dict[str, str]:
    return {"path": str(path.resolve()), "sha256": sha256_file(path)}


def build_input_identity(
    *,
    repository_root: Path,
    protocol_path: Path,
    overlay_path: Path,
    resolved_config: Mapping[str, Any],
) -> Dict[str, Any]:
    return {
        "git_commit": git_revision(repository_root),
        "worktree_clean": git_worktree_clean(repository_root),
        "source_tree_sha256": source_tree_hash(repository_root),
        "protocol": _hash_record(protocol_path),
        "condition_overlay": _hash_record(overlay_path),
        "resolved_config_sha256": canonical_json_hash(resolved_config),
    }


def _same_input_identity(recorded: Mapping[str, Any], current: Mapping[str, Any]) -> bool:
    keys = ("git_commit", "source_tree_sha256", "resolved_config_sha256")
    if any(recorded.get(key) != current.get(key) for key in keys):
        return False
    for key in ("protocol", "condition_overlay"):
        old = recorded.get(key)
        new = current.get(key)
        if not isinstance(old, Mapping) or not isinstance(new, Mapping):
            return False
        if old.get("sha256") != new.get("sha256"):
            return False
    return True


def verify_success_manifest(
    manifest_path: Path,
    *,
    job: PilotJob,
    current_identity: Mapping[str, Any],
) -> Dict[str, Any]:
    """Verify every immutable input/output needed to skip a completed job."""

    manifest = load_json_mapping(manifest_path)
    if manifest.get("status") != "success":
        raise ManifestMismatchError(f"job manifest is not successful: {manifest_path}")
    if manifest.get("job_id") != job.job_id or int(manifest.get("training_seed")) != job.seed:
        raise ManifestMismatchError(f"job identity mismatch: {manifest_path}")
    recorded_identity = manifest.get("input_identity")
    if not isinstance(recorded_identity, Mapping) or not _same_input_identity(
        recorded_identity,
        current_identity,
    ):
        raise ManifestMismatchError(
            f"commit/config/source hash mismatch for completed job {job.job_id}",
        )
    for key in ("progress", "final_checkpoint"):
        record = manifest.get(key)
        if not isinstance(record, Mapping):
            raise ManifestMismatchError(f"missing {key} hash for {job.job_id}")
        path = Path(str(record.get("path")))
        if not path.is_file() or sha256_file(path) != record.get("sha256"):
            raise ManifestMismatchError(f"{key} hash mismatch for {job.job_id}")
    evaluation = manifest.get("evaluation")
    if not isinstance(evaluation, Mapping):
        raise ManifestMismatchError(f"missing evaluation evidence for {job.job_id}")
    for key in ("summary", "episodes"):
        record = evaluation.get(key)
        if not isinstance(record, Mapping):
            raise ManifestMismatchError(f"missing evaluation {key} for {job.job_id}")
        path = Path(str(record.get("path")))
        if not path.is_file() or sha256_file(path) != record.get("sha256"):
            raise ManifestMismatchError(f"evaluation {key} hash mismatch for {job.job_id}")
    return manifest


def mark_stale_attempt_interrupted(job_dir: Path, state: Mapping[str, Any]) -> None:
    if state.get("status") != "running":
        return
    attempt_dir = Path(str(state["attempt_dir"]))
    interrupted = attempt_dir / "interrupted_manifest.json"
    if not interrupted.exists():
        write_json_atomic(
            interrupted,
            {
                "schema_version": 1,
                "job_id": state.get("job_id"),
                "attempt": state.get("attempt"),
                "start_time_utc": state.get("start_time_utc"),
                "end_time_utc": utc_now(),
                "status": "interrupted_detected_on_resume",
                "reason": "prior process ended without a terminal manifest",
            },
            immutable=True,
        )


def latest_training_manifest(job_dir: Path) -> Optional[Path]:
    candidates = sorted((job_dir / "attempts").glob("attempt-*/training_manifest.json"))
    return candidates[-1] if candidates else None


def train_one_job(
    resolved: Mapping[str, Any],
    *,
    attempt_dir: Path,
) -> Dict[str, Any]:
    """Run one real OmniSafe training job and validate its final artifacts."""

    required_workspace = ":4096:8"
    if os.environ.get("CUBLAS_WORKSPACE_CONFIG") != required_workspace:
        raise RuntimeError(
            f"CUBLAS_WORKSPACE_CONFIG must be {required_workspace} before Torch initialization",
        )
    import omnisafe  # pylint: disable=import-outside-toplevel
    import torch  # pylint: disable=import-outside-toplevel
    import safety_stl.omnisafe_env  # noqa: F401  # pylint: disable=import-outside-toplevel,unused-import

    custom_cfgs = dict(resolved["custom_cfgs"])
    train_cfgs = custom_cfgs["train_cfgs"]
    algo_cfgs = custom_cfgs["algo_cfgs"]
    total_steps = int(train_cfgs["total_steps"])
    steps_per_epoch = int(algo_cfgs["steps_per_epoch"])
    expected_epochs = total_steps // steps_per_epoch
    if train_cfgs["device"] != "cuda:0" or not torch.cuda.is_available():
        raise RuntimeError("the frozen pilot requires an available cuda:0 backend")
    # PyTorch 2.4.1 accepts the integer CUDA index here but rejects a
    # ``torch.device`` instance on this host build.
    torch.cuda.set_device(0)
    torch.cuda.reset_peak_memory_stats(0)
    start = time.monotonic()
    agent = omnisafe.Agent(
        str(resolved["algorithm"]),
        str(resolved["environment_id"]),
        custom_cfgs=custom_cfgs,
    )
    observation_shape = list(agent.agent._env.observation_space.shape)  # pylint: disable=protected-access
    learn_result = agent.learn()
    torch.cuda.synchronize(0)
    wall_seconds = time.monotonic() - start
    run_dir = Path(agent.agent.logger.log_dir).resolve()
    progress_path = run_dir / "progress.csv"
    rows = read_progress_rows(progress_path)
    checkpoint = select_fixed_final_checkpoint(
        run_dir,
        total_steps=total_steps,
        steps_per_epoch=steps_per_epoch,
    )
    checks = {
        "expected_epoch_rows": len(rows) == expected_epochs,
        "declared_transition_count": bool(rows)
        and rows[-1].get("TotalEnvSteps") == float(total_steps),
        "augmented_observation_dimension": observation_shape == [63],
        "required_metrics_present_every_epoch": all(
            REQUIRED_PROGRESS_METRICS.issubset(row) for row in rows
        ),
        "all_training_metrics_finite": all(
            math.isfinite(value) for row in rows for value in row.values()
        ),
        **routing_checks(str(resolved["condition"]), rows),
    }
    if not all(checks.values()):
        raise AssertionError(f"training artifact checks failed: {checks}")
    return {
        "run_dir": str(run_dir),
        "progress": _hash_record(progress_path),
        "final_checkpoint": _hash_record(checkpoint),
        "fixed_final_epoch": expected_epochs,
        "wall_clock_seconds": wall_seconds,
        "transitions_per_second": total_steps / wall_seconds,
        "peak_gpu_memory_allocated_bytes": int(torch.cuda.max_memory_allocated(0)),
        "peak_gpu_memory_reserved_bytes": int(torch.cuda.max_memory_reserved(0)),
        "disk_bytes_at_training_completion": directory_size(attempt_dir),
        "observation_shape": observation_shape,
        "learn_return": {
            "mean_episode_return": float(learn_result[0]),
            "mean_selected_episode_cost": float(learn_result[1]),
            "mean_episode_length": float(learn_result[2]),
        },
        "checks": checks,
    }


def evaluate_one_job(
    training: Mapping[str, Any],
    *,
    evaluation_seeds: Sequence[int],
    episode_horizon: int,
    attempt_dir: Path,
) -> Dict[str, Any]:
    """Evaluate the fixed final checkpoint immediately with the common gold oracle."""

    from safety_stl.evaluation import (  # pylint: disable=import-outside-toplevel
        evaluate_checkpoint,
        write_evaluation_outputs,
    )

    checkpoint = Path(str(training["final_checkpoint"]["path"]))
    summary, episodes, trajectories = evaluate_checkpoint(
        Path(str(training["run_dir"])),
        checkpoint.name,
        evaluation_seeds,
        max_episode_steps=episode_horizon,
        deterministic=True,
        save_trajectories=False,
    )
    outputs = write_evaluation_outputs(
        attempt_dir / "evaluation",
        summary,
        episodes,
        trajectories,
    )
    if trajectories:
        raise AssertionError("full trajectory JSONL must remain disabled by default")
    return {
        "summary": _hash_record(Path(outputs["summary"])),
        "episodes": _hash_record(Path(outputs["episodes"])),
        "episode_count": len(episodes),
        "evaluation_seeds": [int(seed) for seed in evaluation_seeds],
        "deterministic_policy": True,
        "gold_oracle_agreement": bool(summary["aggregate"]["all_online_oracle_agree"]),
        "rtamt_max_robustness_difference": float(
            summary["aggregate"]["rtamt_max_robustness_difference"],
        ),
        "aggregate": summary["aggregate"],
    }


TrainingFunction = Callable[[Mapping[str, Any]], Dict[str, Any]]
EvaluationFunction = Callable[[Mapping[str, Any]], Dict[str, Any]]


def execute_job(
    *,
    job: PilotJob,
    repository_root: Path,
    output_root: Path,
    protocol: Mapping[str, Any],
    overlay: Mapping[str, Any],
    protocol_path: Path,
    overlay_path: Path,
    evaluation_seeds: Sequence[int],
    episode_horizon: int,
    resume: bool,
    train_only: bool,
    evaluate_only: bool,
    overrides: Optional[Mapping[str, Any]] = None,
    train_function: Optional[Callable[[Mapping[str, Any], Path], Dict[str, Any]]] = None,
    evaluation_function: Optional[
        Callable[[Mapping[str, Any], Sequence[int], int, Path], Dict[str, Any]]
    ] = None,
) -> Dict[str, Any]:
    """Execute or resume one job without overwriting any successful evidence."""

    if train_only and evaluate_only:
        raise ValueError("train-only and evaluate-only are mutually exclusive")
    job_dir = output_root / "jobs" / job.condition / f"seed-{job.seed}"
    resolved = compose_omnisafe_config(
        protocol,
        overlay,
        seed=job.seed,
        log_dir=job_dir / "placeholder",
        overrides=overrides,
    )
    # The physical attempt path is excluded from the immutable scientific config identity.
    resolved_identity = json.loads(json.dumps(resolved))
    resolved_identity["custom_cfgs"]["logger_cfgs"]["log_dir"] = "<attempt-log-dir>"
    identity = build_input_identity(
        repository_root=repository_root,
        protocol_path=protocol_path,
        overlay_path=overlay_path,
        resolved_config=resolved_identity,
    )
    success_path = job_dir / "manifest.json"
    if success_path.exists():
        manifest = verify_success_manifest(
            success_path,
            job=job,
            current_identity=identity,
        )
        if resume:
            return {"job_id": job.job_id, "action": "skipped_verified_success", "manifest": manifest}
        raise ExistingRunError(
            f"successful job already exists; use --resume to verify and skip: {job.job_id}",
        )

    state_path = job_dir / "state.json"
    state = load_json_mapping(state_path) if state_path.exists() else None
    if state and state.get("status") == "running":
        if not resume:
            raise ExistingRunError(f"job has an interrupted/running attempt: {job.job_id}")
        mark_stale_attempt_interrupted(job_dir, state)
    elif state and not resume and not evaluate_only:
        raise ExistingRunError(f"job has prior evidence; use --resume: {job.job_id}")

    if evaluate_only:
        training_path = latest_training_manifest(job_dir)
        if training_path is None:
            raise FileNotFoundError(f"no completed training manifest for {job.job_id}")
        training_manifest = load_json_mapping(training_path)
        if not _same_input_identity(training_manifest["input_identity"], identity):
            raise ManifestMismatchError(f"training inputs changed for {job.job_id}")
        training = dict(training_manifest["training"])
        attempt_dir = training_path.parent
        attempt_number = int(training_manifest["attempt"])
        start_time = str(training_manifest["start_time_utc"])
    else:
        attempt_number, attempt_dir = next_attempt_dir(job_dir)
        start_time = utc_now()
        resolved["custom_cfgs"]["logger_cfgs"]["log_dir"] = str(attempt_dir / "training")
        state_record = {
            "schema_version": 1,
            "job_id": job.job_id,
            "condition": job.condition,
            "training_seed": job.seed,
            "attempt": attempt_number,
            "attempt_dir": str(attempt_dir.resolve()),
            "start_time_utc": start_time,
            "status": "running",
        }
        write_json_atomic(state_path, state_record)
        try:
            trainer = train_function or (
                lambda config, path: train_one_job(config, attempt_dir=path)
            )
            training = trainer(resolved, attempt_dir)
            training_manifest = {
                **state_record,
                "end_time_utc": utc_now(),
                "status": "trained",
                "input_identity": identity,
                "resolved_config": resolved_identity,
                "training": training,
            }
            write_json_atomic(
                attempt_dir / "training_manifest.json",
                training_manifest,
                immutable=True,
            )
            if train_only:
                write_json_atomic(state_path, {**state_record, "status": "trained"})
                return {"job_id": job.job_id, "action": "trained", "manifest": training_manifest}
        except BaseException as error:
            failure = {
                **state_record,
                "end_time_utc": utc_now(),
                "status": "interrupted" if isinstance(error, KeyboardInterrupt) else "failed",
                "error_type": type(error).__name__,
                "error": str(error),
            }
            write_json_atomic(attempt_dir / "failure_manifest.json", failure, immutable=True)
            write_json_atomic(state_path, failure)
            raise

    evaluation_start = utc_now()
    try:
        evaluator = evaluation_function or (
            lambda record, seeds, horizon, path: evaluate_one_job(
                record,
                evaluation_seeds=seeds,
                episode_horizon=horizon,
                attempt_dir=path,
            )
        )
        evaluation = evaluator(training, evaluation_seeds, episode_horizon, attempt_dir)
        evaluation_manifest = {
            "schema_version": 1,
            "job_id": job.job_id,
            "attempt": attempt_number,
            "start_time_utc": evaluation_start,
            "end_time_utc": utc_now(),
            "status": "evaluated",
            "evaluation": evaluation,
        }
        write_json_atomic(
            attempt_dir / "evaluation_manifest.json",
            evaluation_manifest,
            immutable=True,
        )
        success = {
            "schema_version": 1,
            "job_id": job.job_id,
            "matrix_index": job.index,
            "condition": job.condition,
            "training_seed": job.seed,
            "attempt": attempt_number,
            "start_time_utc": start_time,
            "end_time_utc": utc_now(),
            "status": "success",
            "input_identity": identity,
            "run_dir": training["run_dir"],
            "progress": training["progress"],
            "final_checkpoint": training["final_checkpoint"],
            "training": training,
            "evaluation": evaluation,
            "disk_usage": {
                "training_bytes_at_completion": int(
                    training["disk_bytes_at_training_completion"],
                ),
                "evaluation_bytes": directory_size(attempt_dir / "evaluation"),
                "attempt_total_bytes": directory_size(attempt_dir),
            },
            "platform": {
                "python": platform.python_version(),
                "omnisafe": installed_version("omnisafe"),
                "torch": installed_version("torch"),
                "safety_gymnasium": installed_version("safety-gymnasium"),
                "rtamt": installed_version("rtamt"),
            },
        }
        write_json_atomic(success_path, success, immutable=True)
        write_json_atomic(
            state_path,
            {
                "schema_version": 1,
                "job_id": job.job_id,
                "status": "success",
                "manifest": str(success_path.resolve()),
            },
        )
        return {"job_id": job.job_id, "action": "completed", "manifest": success}
    except BaseException as error:
        failure = {
            "schema_version": 1,
            "job_id": job.job_id,
            "attempt": attempt_number,
            "start_time_utc": evaluation_start,
            "end_time_utc": utc_now(),
            "status": "evaluation_interrupted"
            if isinstance(error, KeyboardInterrupt)
            else "evaluation_failed",
            "error_type": type(error).__name__,
            "error": str(error),
        }
        failure_path = attempt_dir / "evaluation_failure_manifest.json"
        if not failure_path.exists():
            write_json_atomic(failure_path, failure, immutable=True)
        write_json_atomic(state_path, failure)
        raise


def dry_run_manifest(
    *,
    jobs: Sequence[PilotJob],
    repository_root: Path,
    output_root: Path,
    protocol: Mapping[str, Any],
    conditions: Mapping[str, Mapping[str, Any]],
    protocol_path: Path,
    overlay_paths: Mapping[str, Path],
    evaluation_seeds: Sequence[int],
) -> Dict[str, Any]:
    entries = []
    for job in jobs:
        resolved = compose_omnisafe_config(
            protocol,
            conditions[job.condition],
            seed=job.seed,
            log_dir=Path("<attempt-log-dir>"),
        )
        identity = build_input_identity(
            repository_root=repository_root,
            protocol_path=protocol_path,
            overlay_path=overlay_paths[job.condition],
            resolved_config=resolved,
        )
        entries.append(
            {
                **asdict(job),
                "job_id": job.job_id,
                "output_dir": str(
                    (output_root / "jobs" / job.condition / f"seed-{job.seed}").resolve(),
                ),
                "input_identity": identity,
                "evaluation_seeds": [int(seed) for seed in evaluation_seeds],
                "status": "planned_not_started",
            },
        )
    return {
        "schema_version": 1,
        "created_at_utc": utc_now(),
        "status": "dry_run_only_no_training_started",
        "job_count": len(entries),
        "jobs": entries,
    }


__all__ = [
    "CONDITION_ORDER",
    "ExistingRunError",
    "ManifestMismatchError",
    "PilotJob",
    "build_input_identity",
    "dry_run_manifest",
    "enumerate_pilot_jobs",
    "execute_job",
    "read_progress_rows",
    "select_fixed_final_checkpoint",
    "sha256_file",
    "verify_success_manifest",
    "write_json_atomic",
]
