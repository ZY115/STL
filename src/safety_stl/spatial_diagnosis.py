"""Deterministic spatial replay of the frozen Stage I pilot checkpoints.

The policy is evaluated through the unchanged project wrapper.  A second,
non-autoresetting Safety-Gymnasium instance receives the same seed and actions
and is used only to export simulator geometry.  Step-level reward, native cost,
termination flags and public observations are checked between the two copies so
that privileged geometry can never affect the policy or learner-cost path.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import math
import subprocess
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Mapping, Optional, Sequence, TextIO, Tuple

import numpy as np
import safety_gymnasium
import torch
from omnisafe.envs.core import make

from safety_stl.evaluation import (
    _boolean,
    _goal_met,
    _scalar,
    _trajectory_row,
    load_policy,
    verify_gold_oracle,
)
from safety_stl.omnisafe_env import BASE_ENVIRONMENT_ID, STL_COST_ENV_ID
from safety_stl.signals import distance_from_observation
from safety_stl.trajectory_diagnosis import (
    CONDITIONS,
    EVALUATION_SEEDS,
    TRAINING_SEEDS,
    assert_replay_matches_frozen,
    load_job,
    read_csv,
    sha256_file,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
ANALYSIS_EPISODES = REPOSITORY_ROOT / "results/stage1_pilot/analysis/episode_records.csv"
MAP_LOW = -1.5
MAP_HIGH = 1.5
HAZARD_RADIUS = 0.20
WARNING_RADIUS = 0.45
SAFE_RADIUS = 0.55
DENSITY_BINS = 75
GOAL_EVENT_WINDOW = 20

EXTREME_CASES = (
    {
        "case_id": "gold_worse_seed-4404_eval-10066",
        "selection": "frozen_largest_gold_minus_task_missed",
        "training_seed": 4404,
        "evaluation_seed": 10066,
    },
    {
        "case_id": "gold_better_seed-2202_eval-10031",
        "selection": "frozen_largest_task_minus_gold_missed",
        "training_seed": 2202,
        "evaluation_seed": 10031,
    },
)

EVENT_DENSITIES = ("occupancy", "warning", "recovery", "violation")

GEOMETRY_FIELDS = (
    "case_id",
    "selection",
    "condition",
    "training_seed",
    "evaluation_seed",
    "episode_index",
    "action_index",
    "sample_index",
    "agent_x",
    "agent_y",
    "agent_heading",
    "goal_id",
    "goal_x",
    "goal_y",
    "goal_met",
    *tuple(
        coordinate
        for index in range(8)
        for coordinate in (f"hazard_{index}_x", f"hazard_{index}_y")
    ),
    "nearest_hazard_id",
    "privileged_nearest_center_distance",
    "public_lidar_distance",
    "monitor_distance",
    "action_forward",
    "action_turn",
    "monitor_state",
    "remaining_steps",
    "warning_trigger",
    "recovery",
    "late_recovery",
    "deadline_violation",
    "terminal_unresolved",
    "trigger_step",
    "deadline_step",
    "elapsed_steps",
    "warning_episode_id",
    "reward",
    "native_cost",
    "stl_cost",
    "selected_algorithm_cost",
    "terminated",
    "truncated",
)


def _sha256(path: Path) -> str:
    return sha256_file(path)


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, Mapping):
        raise ValueError(f"expected a JSON mapping: {path}")
    return dict(value)


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def _git_commit(repository_root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(repository_root),
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _as_int(value: Any) -> int:
    return int(float(value))


def select_median_paired_case(
    episode_rows: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    """Select the pre-plot paired case closest to zero Gold-minus-task misses.

    Ties are resolved only by ascending training seed and then evaluation seed.
    """

    counts: Dict[Tuple[str, int, int], int] = {}
    for row in episode_rows:
        condition = str(row["condition"])
        if condition not in {"task_only", "gold_stl_cost"}:
            continue
        key = (condition, _as_int(row["training_seed"]), _as_int(row["evaluation_seed"]))
        counts[key] = _as_int(row["deadline_violation_count"]) + _as_int(
            row["terminal_unresolved_count"],
        )
    candidates: List[Tuple[int, int, int, int, int]] = []
    for training_seed in TRAINING_SEEDS:
        for evaluation_seed in EVALUATION_SEEDS:
            task_key = ("task_only", training_seed, evaluation_seed)
            gold_key = ("gold_stl_cost", training_seed, evaluation_seed)
            if task_key not in counts or gold_key not in counts:
                raise ValueError(f"missing paired episode row: {training_seed}/{evaluation_seed}")
            task_missed = counts[task_key]
            gold_missed = counts[gold_key]
            difference = gold_missed - task_missed
            candidates.append(
                (
                    abs(difference),
                    training_seed,
                    evaluation_seed,
                    task_missed,
                    gold_missed,
                ),
            )
    _, training_seed, evaluation_seed, task_missed, gold_missed = min(candidates)
    return {
        "case_id": f"median_seed-{training_seed}_eval-{evaluation_seed}",
        "selection": "minimum_absolute_gold_minus_task_missed_then_seed_tie_break",
        "training_seed": training_seed,
        "evaluation_seed": evaluation_seed,
        "task_missed_obligations": task_missed,
        "gold_missed_obligations": gold_missed,
        "gold_minus_task_missed_obligations": gold_missed - task_missed,
    }


def frozen_spatial_cases(analysis_episode_path: Path = ANALYSIS_EPISODES) -> Tuple[Dict[str, Any], ...]:
    median = select_median_paired_case(read_csv(analysis_episode_path))
    return (*EXTREME_CASES, median)


def _selected_cost(condition: str, native_cost: float, stl_cost: int) -> float:
    if condition == "task_only":
        return 0.0
    if condition == "native_cost":
        return float(native_cost)
    if condition == "gold_stl_cost":
        return float(stl_cost)
    raise ValueError(f"unknown condition: {condition}")


def geometry_snapshot(
    task: Any,
    public_observation: np.ndarray,
    observation_schema: Any,
    *,
    goal_id: int,
    goal_xy: Optional[Sequence[float]] = None,
) -> Dict[str, Any]:
    """Read diagnostic-only geometry and validate the public distance signal."""

    agent_xy = np.asarray(task.agent.pos, dtype=np.float64)[:2]
    agent_matrix = np.asarray(task.agent.mat, dtype=np.float64)
    heading = float(math.atan2(agent_matrix[1, 0], agent_matrix[0, 0]))
    hazards = np.asarray(task.hazards.pos, dtype=np.float64)[:, :2]
    if hazards.shape != (8, 2):
        raise AssertionError(f"expected eight 2-D hazards, got {hazards.shape}")
    deltas = hazards - agent_xy
    distances = np.linalg.norm(deltas, axis=1)
    nearest_id = int(np.argmin(distances))
    privileged_distance = float(distances[nearest_id])
    public_distance = float(
        distance_from_observation(public_observation, observation_schema, lidar_range=3.0),
    )
    if abs(public_distance - min(3.0, privileged_distance)) > 1e-9:
        raise AssertionError(
            "public/capped-privileged nearest-hazard distance mismatch: "
            f"{public_distance} versus {privileged_distance}",
        )
    target = np.asarray(task.goal.pos if goal_xy is None else goal_xy, dtype=np.float64)[:2]
    record: Dict[str, Any] = {
        "agent_x": float(agent_xy[0]),
        "agent_y": float(agent_xy[1]),
        "agent_heading": heading,
        "goal_id": int(goal_id),
        "goal_x": float(target[0]),
        "goal_y": float(target[1]),
        "nearest_hazard_id": nearest_id,
        "privileged_nearest_center_distance": privileged_distance,
        "public_lidar_distance": public_distance,
    }
    for index, hazard in enumerate(hazards):
        record[f"hazard_{index}_x"] = float(hazard[0])
        record[f"hazard_{index}_y"] = float(hazard[1])
    return record


def sampled_layout_fractions(
    hazards_xy: np.ndarray,
    *,
    grid_size: int = 301,
) -> Dict[str, float]:
    """Return deterministic grid fractions outside every hazard-centered disk."""

    hazards = np.asarray(hazards_xy, dtype=np.float64)
    if hazards.shape != (8, 2):
        raise ValueError("layout fractions require eight 2-D hazard centers")
    if grid_size < 3:
        raise ValueError("grid_size must be at least three")
    coordinates = np.linspace(MAP_LOW, MAP_HIGH, grid_size, dtype=np.float64)
    x_grid, y_grid = np.meshgrid(coordinates, coordinates)
    minimum_squared = np.full(x_grid.shape, np.inf, dtype=np.float64)
    for hazard_x, hazard_y in hazards:
        squared = (x_grid - hazard_x) ** 2 + (y_grid - hazard_y) ** 2
        minimum_squared = np.minimum(minimum_squared, squared)
    return {
        "outside_physical_radius_fraction": float(np.mean(minimum_squared >= HAZARD_RADIUS**2)),
        "outside_warning_radius_fraction": float(np.mean(minimum_squared >= WARNING_RADIUS**2)),
        "outside_safe_radius_fraction": float(np.mean(minimum_squared >= SAFE_RADIUS**2)),
    }


@contextmanager
def _deterministic_gzip_text(path: Path) -> Iterator[TextIO]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw_handle:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw_handle, mtime=0) as gzip_handle:
            with io.TextIOWrapper(gzip_handle, encoding="utf-8", newline="") as text_handle:
                yield text_handle


def _verify_manifest_artifact(record: Mapping[str, Any], label: str) -> Path:
    path = Path(str(record["path"]))
    if not path.is_file():
        raise FileNotFoundError(path)
    actual = _sha256(path)
    if actual != str(record["sha256"]):
        raise RuntimeError(f"{label} hash mismatch: {path}")
    return path


def _compare_parallel_step(
    *,
    wrapped_reward: float,
    raw_reward: float,
    wrapped_native_cost: float,
    raw_native_cost: float,
    wrapped_terminated: bool,
    raw_terminated: bool,
    wrapped_truncated: bool,
    raw_truncated: bool,
) -> None:
    if not math.isclose(wrapped_reward, raw_reward, rel_tol=0.0, abs_tol=1e-6):
        raise AssertionError("diagnostic twin reward diverged from the policy environment")
    if not math.isclose(wrapped_native_cost, raw_native_cost, rel_tol=0.0, abs_tol=1e-9):
        raise AssertionError("diagnostic twin native cost diverged from the policy environment")
    if wrapped_terminated != raw_terminated or wrapped_truncated != raw_truncated:
        raise AssertionError("diagnostic twin termination flags diverged")


def _episode_record(
    rows: Sequence[Mapping[str, Any]],
    *,
    evaluation_seed: int,
    episode_return: float,
    native_cost_total: float,
    goal_events: int,
    action_count: int,
) -> Dict[str, Any]:
    oracle = verify_gold_oracle(
        rows,
        d_warn=WARNING_RADIUS,
        d_safe=SAFE_RADIUS,
        deadline_steps=79,
        tolerance=1e-9,
    )
    return {
        "evaluation_seed": int(evaluation_seed),
        "episode_length": int(action_count),
        "episode_return": float(episode_return),
        "native_cost_total": float(native_cost_total),
        "gold_stl_cost_total": int(oracle["stl_event_cost_total"]),
        "goal_events": int(goal_events),
        "goal_success": bool(goal_events > 0),
        "minimum_distance": min(float(row["distance"]) for row in rows),
        "trigger_count": int(oracle["trigger_count"]),
        "recovery_count": int(oracle["recovery_count"]),
        "late_recovery_count": int(oracle["late_recovery_count"]),
        "deadline_violation_count": int(oracle["deadline_violation_count"]),
        "terminal_unresolved_count": int(oracle["terminal_unresolved_count"]),
        "on_time_recovery_latency_sum": int(oracle["on_time_recovery_latency_sum"]),
        "deadline_violation_delay_sum": int(oracle["deadline_violation_delay_sum"]),
        "terminal_unresolved_delay_sum": int(oracle["terminal_unresolved_delay_sum"]),
        "positive_cost_step_count": sum(int(row["stl_cost"]) for row in rows),
        "completed_window_count": int(oracle["completed_window_count"]),
        "trace_robustness": oracle["trace_robustness"],
        "online_oracle_agreement": bool(oracle["agreement"]),
        "rtamt_max_robustness_difference": float(oracle["rtamt_max_robustness_difference"]),
    }


def _geometry_record(
    monitor_row: Mapping[str, Any],
    geometry: Mapping[str, Any],
    *,
    condition: str,
    training_seed: int,
    evaluation_seed: int,
    episode_index: int,
    goal_met: bool,
    case: Optional[Mapping[str, Any]],
) -> Dict[str, Any]:
    return {
        "case_id": "" if case is None else str(case["case_id"]),
        "selection": "" if case is None else str(case["selection"]),
        "condition": condition,
        "training_seed": int(training_seed),
        "evaluation_seed": int(evaluation_seed),
        "episode_index": int(episode_index),
        "action_index": int(monitor_row["action_index"]),
        "sample_index": int(monitor_row["sample_index"]),
        **geometry,
        "goal_met": bool(goal_met),
        "monitor_distance": float(monitor_row["distance"]),
        "action_forward": monitor_row["action_forward"],
        "action_turn": monitor_row["action_turn"],
        "monitor_state": str(monitor_row["monitor_state"]),
        "remaining_steps": monitor_row["remaining_steps"],
        "warning_trigger": bool(monitor_row["warning_trigger"]),
        "recovery": bool(monitor_row["recovery"]),
        "late_recovery": bool(monitor_row["late_recovery"]),
        "deadline_violation": bool(monitor_row["deadline_violation"]),
        "terminal_unresolved": bool(monitor_row["terminal_unresolved"]),
        "trigger_step": monitor_row["trigger_step"],
        "deadline_step": monitor_row["deadline_step"],
        "elapsed_steps": monitor_row["elapsed_steps"],
        "warning_episode_id": int(monitor_row["warning_episode_id"]),
        "reward": float(monitor_row["reward"]),
        "native_cost": float(monitor_row["native_cost"]),
        "stl_cost": int(monitor_row["stl_cost"]),
        "selected_algorithm_cost": float(monitor_row["selected_algorithm_cost"]),
        "terminated": bool(monitor_row["terminated"]),
        "truncated": bool(monitor_row["truncated"]),
    }


class SpatialAccumulator:
    """Streaming compact aggregates for the 1.5-million-step replay."""

    def __init__(self) -> None:
        self.counts = np.zeros(
            (len(CONDITIONS), len(EVENT_DENSITIES), DENSITY_BINS, DENSITY_BINS),
            dtype=np.int64,
        )
        self.max_distance_disagreement = 0.0
        self.row_count = 0
        self.condition_metrics: Dict[str, Dict[str, float]] = {
            condition: {
                "episode_count": 0.0,
                "action_step_count": 0.0,
                "path_length": 0.0,
                "goal_event_count": 0.0,
                "warning_zone_samples": 0.0,
                "hysteresis_band_samples": 0.0,
                "safe_samples": 0.0,
                "distance_band_crossings": 0.0,
                "warning_trigger_count": 0.0,
                "recovery_count": 0.0,
                "deadline_violation_count": 0.0,
                "terminal_unresolved_count": 0.0,
                "deadline_violations_near_goal_event": 0.0,
            }
            for condition in CONDITIONS
        }

    @staticmethod
    def _bin(value: float) -> Optional[int]:
        if value < MAP_LOW or value > MAP_HIGH:
            return None
        if value == MAP_HIGH:
            return DENSITY_BINS - 1
        return int((value - MAP_LOW) / (MAP_HIGH - MAP_LOW) * DENSITY_BINS)

    def add_row(self, row: Mapping[str, Any]) -> None:
        condition_index = CONDITIONS.index(str(row["condition"]))
        x_bin = self._bin(float(row["agent_x"]))
        y_bin = self._bin(float(row["agent_y"]))
        if x_bin is not None and y_bin is not None:
            self.counts[condition_index, 0, y_bin, x_bin] += 1
            if bool(row["warning_trigger"]):
                self.counts[condition_index, 1, y_bin, x_bin] += 1
            if bool(row["recovery"]):
                self.counts[condition_index, 2, y_bin, x_bin] += 1
            if bool(row["deadline_violation"]) or bool(row["terminal_unresolved"]):
                self.counts[condition_index, 3, y_bin, x_bin] += 1
        difference = abs(
            float(row["public_lidar_distance"])
            - min(3.0, float(row["privileged_nearest_center_distance"])),
        )
        self.max_distance_disagreement = max(self.max_distance_disagreement, difference)
        self.row_count += 1

    @staticmethod
    def _distance_band(distance: float) -> int:
        if distance < WARNING_RADIUS:
            return 0
        if distance < SAFE_RADIUS:
            return 1
        return 2

    def add_episode(self, condition: str, rows: Sequence[Mapping[str, Any]]) -> None:
        metrics = self.condition_metrics[condition]
        metrics["episode_count"] += 1
        metrics["action_step_count"] += max(0, len(rows) - 1)
        positions = np.asarray(
            [[float(row["agent_x"]), float(row["agent_y"])] for row in rows],
            dtype=np.float64,
        )
        metrics["path_length"] += float(np.linalg.norm(np.diff(positions, axis=0), axis=1).sum())
        bands = [self._distance_band(float(row["public_lidar_distance"])) for row in rows]
        metrics["warning_zone_samples"] += sum(band == 0 for band in bands)
        metrics["hysteresis_band_samples"] += sum(band == 1 for band in bands)
        metrics["safe_samples"] += sum(band == 2 for band in bands)
        metrics["distance_band_crossings"] += sum(a != b for a, b in zip(bands, bands[1:]))
        for field in (
            "goal_met",
            "warning_trigger",
            "recovery",
            "deadline_violation",
            "terminal_unresolved",
        ):
            target = "goal_event_count" if field == "goal_met" else f"{field}_count"
            metrics[target] += sum(bool(row[field]) for row in rows)
        goal_steps = [int(row["sample_index"]) for row in rows if bool(row["goal_met"])]
        deadline_steps = [
            int(row["sample_index"]) for row in rows if bool(row["deadline_violation"])
        ]
        metrics["deadline_violations_near_goal_event"] += sum(
            bool(goal_steps) and min(abs(step - goal_step) for goal_step in goal_steps) <= GOAL_EVENT_WINDOW
            for step in deadline_steps
        )

    def summary(self) -> Dict[str, Any]:
        output: Dict[str, Any] = {}
        for condition, raw in self.condition_metrics.items():
            values = dict(raw)
            samples = (
                values["warning_zone_samples"]
                + values["hysteresis_band_samples"]
                + values["safe_samples"]
            )
            episodes = values["episode_count"]
            deadlines = values["deadline_violation_count"]
            values.update(
                {
                    "mean_path_length_per_episode": (
                        values["path_length"] / episodes if episodes else None
                    ),
                    "warning_zone_sample_fraction": (
                        values["warning_zone_samples"] / samples if samples else None
                    ),
                    "hysteresis_band_sample_fraction": (
                        values["hysteresis_band_samples"] / samples if samples else None
                    ),
                    "distance_band_crossings_per_episode": (
                        values["distance_band_crossings"] / episodes if episodes else None
                    ),
                    "deadline_violation_near_goal_fraction": (
                        values["deadline_violations_near_goal_event"] / deadlines
                        if deadlines
                        else None
                    ),
                    "terminal_unresolved_fraction_of_missed": (
                        values["terminal_unresolved_count"]
                        / (values["deadline_violation_count"] + values["terminal_unresolved_count"])
                        if values["deadline_violation_count"] + values["terminal_unresolved_count"]
                        else None
                    ),
                },
            )
            output[condition] = values
        return output


def _replay_checkpoint(
    *,
    repository_root: Path,
    condition: str,
    training_seed: int,
    cases_by_pair: Mapping[Tuple[int, int], Mapping[str, Any]],
    full_writer: csv.DictWriter,
    representative_writer: csv.DictWriter,
    accumulator: SpatialAccumulator,
    layouts: Dict[int, np.ndarray],
) -> Dict[str, Any]:
    manifest = load_job(repository_root, condition, training_seed)
    frozen_path = _verify_manifest_artifact(manifest["evaluation"]["episodes"], "evaluation episodes")
    _verify_manifest_artifact(manifest["evaluation"]["summary"], "evaluation summary")
    frozen_rows = read_csv(frozen_path)
    frozen_by_seed = {_as_int(row["evaluation_seed"]): row for row in frozen_rows}
    environment = make(
        STL_COST_ENV_ID,
        num_envs=1,
        device=torch.device("cpu"),
        max_episode_steps=1000,
    )
    geometry_environment = safety_gymnasium.make(
        BASE_ENVIRONMENT_ID,
        autoreset=False,
        max_episode_steps=1000,
    )
    replayed_episodes: List[Dict[str, Any]] = []
    checkpoint_max_twin_observation_difference = 0.0
    try:
        policy = load_policy(
            Path(str(manifest["run_dir"])),
            Path(str(manifest["final_checkpoint"]["path"])).name,
            environment.observation_space,
            environment.action_space,
        )
        observation_schema = geometry_environment.unwrapped.task.obs_info.obs_space_dict
        for episode_index, evaluation_seed in enumerate(EVALUATION_SEEDS):
            torch.manual_seed(int(evaluation_seed))
            observation, reset_info = environment.reset(seed=int(evaluation_seed))
            raw_observation, _ = geometry_environment.reset(seed=int(evaluation_seed))
            initial_difference = float(
                np.max(
                    np.abs(
                        observation[: len(raw_observation)].detach().cpu().numpy()
                        - np.asarray(raw_observation),
                    ),
                ),
            )
            checkpoint_max_twin_observation_difference = max(
                checkpoint_max_twin_observation_difference,
                initial_difference,
            )
            if initial_difference > 1e-5:
                raise AssertionError("diagnostic twin reset observation diverged")
            task = geometry_environment.unwrapped.task
            goal_id = 0
            case = cases_by_pair.get((training_seed, evaluation_seed))
            monitor_rows: List[Dict[str, Any]] = [
                _trajectory_row(
                    reset_info,
                    action_index=-1,
                    action=None,
                    reward=0.0,
                    native_cost=0.0,
                    selected_algorithm_cost=0.0,
                    terminated=False,
                    truncated=False,
                    goal_met=False,
                ),
            ]
            initial_geometry = geometry_snapshot(
                task,
                np.asarray(raw_observation),
                observation_schema,
                goal_id=goal_id,
            )
            geometry_rows: List[Dict[str, Any]] = [
                _geometry_record(
                    monitor_rows[0],
                    initial_geometry,
                    condition=condition,
                    training_seed=training_seed,
                    evaluation_seed=evaluation_seed,
                    episode_index=episode_index,
                    goal_met=False,
                    case=case,
                ),
            ]
            full_writer.writerow({key: geometry_rows[0][key] for key in GEOMETRY_FIELDS})
            if case is not None:
                representative_writer.writerow(
                    {key: geometry_rows[0][key] for key in GEOMETRY_FIELDS},
                )
            accumulator.add_row(geometry_rows[0])
            hazard_layout = np.asarray(task.hazards.pos, dtype=np.float64)[:, :2]
            if evaluation_seed in layouts:
                if not np.allclose(layouts[evaluation_seed], hazard_layout, rtol=0.0, atol=1e-12):
                    raise AssertionError("same evaluation seed produced different hazard layouts")
            else:
                layouts[evaluation_seed] = hazard_layout.copy()

            episode_return = 0.0
            native_cost_total = 0.0
            goal_events = 0
            action_count = 0
            done = False
            while not done:
                actor_observation = policy.policy_observation(observation)
                with torch.no_grad():
                    action = policy.actor.predict(actor_observation, deterministic=True)
                previous_goal = np.asarray(task.goal.pos, dtype=np.float64)[:2].copy()
                observation, reward, _, terminated, truncated, info = environment.step(action)
                raw_observation, raw_reward, raw_cost, raw_terminated, raw_truncated, raw_info = (
                    geometry_environment.step(action.detach().cpu().numpy())
                )
                term = _boolean(terminated)
                trunc = _boolean(truncated)
                done = term or trunc
                wrapped_reward = _scalar(reward)
                native_cost = _scalar(info["native_cost"])
                _compare_parallel_step(
                    wrapped_reward=wrapped_reward,
                    raw_reward=float(raw_reward),
                    wrapped_native_cost=native_cost,
                    raw_native_cost=float(raw_cost),
                    wrapped_terminated=term,
                    raw_terminated=bool(raw_terminated),
                    wrapped_truncated=trunc,
                    raw_truncated=bool(raw_truncated),
                )
                if not done:
                    twin_difference = float(
                        np.max(
                            np.abs(
                                observation[: len(raw_observation)].detach().cpu().numpy()
                                - np.asarray(raw_observation),
                            ),
                        ),
                    )
                    checkpoint_max_twin_observation_difference = max(
                        checkpoint_max_twin_observation_difference,
                        twin_difference,
                    )
                    if twin_difference > 1e-5:
                        raise AssertionError("diagnostic twin step observation diverged")
                goal_met = _goal_met(info, done)
                if goal_met != bool(raw_info.get("goal_met", False)):
                    raise AssertionError("diagnostic twin goal event diverged")
                action_count += 1
                episode_return += wrapped_reward
                native_cost_total += native_cost
                goal_events += int(goal_met)
                stl_cost = int(_scalar(info["stl_cost"]))
                monitor_row = _trajectory_row(
                    info,
                    action_index=action_count - 1,
                    action=action,
                    reward=wrapped_reward,
                    native_cost=native_cost,
                    selected_algorithm_cost=_selected_cost(condition, native_cost, stl_cost),
                    terminated=term,
                    truncated=trunc,
                    goal_met=goal_met,
                )
                monitor_rows.append(monitor_row)
                geometry = geometry_snapshot(
                    task,
                    np.asarray(raw_observation),
                    observation_schema,
                    goal_id=goal_id,
                    goal_xy=previous_goal if goal_met else None,
                )
                geometry_row = _geometry_record(
                    monitor_row,
                    geometry,
                    condition=condition,
                    training_seed=training_seed,
                    evaluation_seed=evaluation_seed,
                    episode_index=episode_index,
                    goal_met=goal_met,
                    case=case,
                )
                geometry_rows.append(geometry_row)
                full_writer.writerow({key: geometry_row[key] for key in GEOMETRY_FIELDS})
                if case is not None:
                    representative_writer.writerow(
                        {key: geometry_row[key] for key in GEOMETRY_FIELDS},
                    )
                accumulator.add_row(geometry_row)
                if goal_met:
                    goal_id += 1
                if action_count > 1001:
                    raise RuntimeError("spatial replay exceeded the frozen episode horizon")

            episode = _episode_record(
                monitor_rows,
                evaluation_seed=evaluation_seed,
                episode_return=episode_return,
                native_cost_total=native_cost_total,
                goal_events=goal_events,
                action_count=action_count,
            )
            replayed_episodes.append(episode)
            accumulator.add_episode(condition, geometry_rows)
            expected = frozen_by_seed[evaluation_seed]
            _assert_episode_matches_row(episode, expected)
    finally:
        environment.close()
        geometry_environment.close()

    # The per-episode check above gives a more local failure, while this final
    # check protects row order and the complete frozen table contract.
    if tuple(EVALUATION_SEEDS) == tuple(range(10000, 10100)):
        assert_replay_matches_frozen(replayed_episodes, frozen_path)
    return {
        "condition": condition,
        "training_seed": training_seed,
        "checkpoint": str(manifest["final_checkpoint"]["path"]),
        "checkpoint_sha256": str(manifest["final_checkpoint"]["sha256"]),
        "frozen_episode_table": str(frozen_path),
        "frozen_episode_sha256": str(manifest["evaluation"]["episodes"]["sha256"]),
        "frozen_summary": str(manifest["evaluation"]["summary"]["path"]),
        "frozen_summary_sha256": str(manifest["evaluation"]["summary"]["sha256"]),
        "episode_count": len(replayed_episodes),
        "replay_matches_frozen": True,
        "max_policy_vs_geometry_twin_observation_difference": (
            checkpoint_max_twin_observation_difference
        ),
    }


def _assert_episode_matches_row(current: Mapping[str, Any], expected: Mapping[str, Any]) -> None:
    integer_fields = (
        "evaluation_seed",
        "episode_length",
        "gold_stl_cost_total",
        "goal_events",
        "trigger_count",
        "recovery_count",
        "late_recovery_count",
        "deadline_violation_count",
        "terminal_unresolved_count",
    )
    float_fields = ("episode_return", "native_cost_total", "minimum_distance")
    for field in integer_fields:
        if int(current[field]) != _as_int(expected[field]):
            raise AssertionError(f"spatial replay mismatch in {field}")
    for field in float_fields:
        if not math.isclose(float(current[field]), float(expected[field]), rel_tol=0.0, abs_tol=1e-8):
            raise AssertionError(f"spatial replay mismatch in {field}")


def _write_schema(path: Path) -> None:
    required = {
        "condition",
        "training_seed",
        "evaluation_seed",
        "sample_index",
        "agent_x",
        "agent_y",
        "agent_heading",
        "goal_id",
        "goal_x",
        "goal_y",
        "goal_met",
        "nearest_hazard_id",
        "privileged_nearest_center_distance",
        "public_lidar_distance",
        "action_forward",
        "action_turn",
        "monitor_state",
        "remaining_steps",
        "warning_trigger",
        "recovery",
        "deadline_violation",
        "terminal_unresolved",
        "reward",
        "native_cost",
        "stl_cost",
        "selected_algorithm_cost",
    }
    if not required.issubset(GEOMETRY_FIELDS):
        raise AssertionError("geometry schema is missing a required work-order field")
    _write_json(
        path,
        {
            "schema_version": 1,
            "fields": list(GEOMETRY_FIELDS),
            "row_semantics": "reset sample followed by every action-result sample",
            "geometry_scope": "privileged diagnostic replay only",
            "goal_semantics": (
                "goal_id identifies the target pursued by the preceding action; a goal-met row "
                "retains the reached goal coordinates and the next row uses the resampled goal"
            ),
            "distance_validation": "public_lidar_distance equals min(3.0, privileged distance)",
            "distance_validation_tolerance": 1e-9,
            "full_table_tracking": "local ignored deterministic gzip CSV; hash retained",
        },
    )


def run_spatial_replay(
    output_root: Path,
    *,
    repository_root: Path = REPOSITORY_ROOT,
) -> Dict[str, Any]:
    """Replay the complete frozen matrix and write compact tracked artifacts."""

    output_root.mkdir(parents=True, exist_ok=True)
    full_path = output_root / "full_geometry.csv.gz"
    representative_path = output_root / "representative_geometry.csv"
    density_path = output_root / "spatial_density_counts.npz"
    layouts_path = output_root / "layout_feasibility.csv"
    schema_path = output_root / "geometry_schema.json"
    summary_path = output_root / "summary.json"
    manifest_path = output_root / "replay_manifest.json"
    cases = frozen_spatial_cases(repository_root / ANALYSIS_EPISODES.relative_to(REPOSITORY_ROOT))
    cases_by_pair = {
        (int(case["training_seed"]), int(case["evaluation_seed"])): case for case in cases
    }
    accumulator = SpatialAccumulator()
    layouts: Dict[int, np.ndarray] = {}
    provenance: List[Dict[str, Any]] = []

    with _deterministic_gzip_text(full_path) as full_handle, representative_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as representative_handle:
        full_writer = csv.DictWriter(full_handle, fieldnames=list(GEOMETRY_FIELDS))
        representative_writer = csv.DictWriter(
            representative_handle,
            fieldnames=list(GEOMETRY_FIELDS),
        )
        full_writer.writeheader()
        representative_writer.writeheader()
        for condition in CONDITIONS:
            for training_seed in TRAINING_SEEDS:
                print(f"spatial replay {condition} seed={training_seed}", flush=True)
                provenance.append(
                    _replay_checkpoint(
                        repository_root=repository_root,
                        condition=condition,
                        training_seed=training_seed,
                        cases_by_pair=cases_by_pair,
                        full_writer=full_writer,
                        representative_writer=representative_writer,
                        accumulator=accumulator,
                        layouts=layouts,
                    ),
                )

    edges = np.linspace(MAP_LOW, MAP_HIGH, DENSITY_BINS + 1, dtype=np.float64)
    np.savez_compressed(
        density_path,
        counts=accumulator.counts,
        edges=edges,
        conditions=np.asarray(CONDITIONS),
        event_types=np.asarray(EVENT_DENSITIES),
    )
    layout_rows: List[Dict[str, Any]] = []
    for evaluation_seed in sorted(layouts):
        fractions = sampled_layout_fractions(layouts[evaluation_seed])
        row: Dict[str, Any] = {"evaluation_seed": evaluation_seed, **fractions}
        for index, (hazard_x, hazard_y) in enumerate(layouts[evaluation_seed]):
            row[f"hazard_{index}_x"] = float(hazard_x)
            row[f"hazard_{index}_y"] = float(hazard_y)
        layout_rows.append(row)
    with layouts_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(layout_rows[0]))
        writer.writeheader()
        writer.writerows(layout_rows)
    _write_schema(schema_path)

    layout_summary = {
        field: {
            "mean": float(np.mean([float(row[field]) for row in layout_rows])),
            "minimum": float(np.min([float(row[field]) for row in layout_rows])),
            "maximum": float(np.max([float(row[field]) for row in layout_rows])),
        }
        for field in (
            "outside_physical_radius_fraction",
            "outside_warning_radius_fraction",
            "outside_safe_radius_fraction",
        )
    }
    summary: Dict[str, Any] = {
        "schema_version": 1,
        "scope": "existing fixed-checkpoint diagnostic replay; no training or checkpoint selection",
        "cases": list(cases),
        "matrix": {
            "checkpoint_count": len(provenance),
            "episode_count": len(provenance) * len(EVALUATION_SEEDS),
            "geometry_row_count": accumulator.row_count,
            "conditions": list(CONDITIONS),
            "training_seeds": list(TRAINING_SEEDS),
            "evaluation_seeds": list(EVALUATION_SEEDS),
            "all_replays_match_frozen": all(row["replay_matches_frozen"] for row in provenance),
            "max_public_capped_geometry_distance_disagreement": accumulator.max_distance_disagreement,
            "max_policy_vs_geometry_twin_observation_difference": max(
                float(row["max_policy_vs_geometry_twin_observation_difference"])
                for row in provenance
            ),
        },
        "spatial_metrics": accumulator.summary(),
        "layout_feasibility": layout_summary,
        "diagnostic_constants": {
            "map_bounds": [MAP_LOW, MAP_HIGH],
            "physical_hazard_radius": HAZARD_RADIUS,
            "warning_radius": WARNING_RADIUS,
            "safe_radius": SAFE_RADIUS,
            "density_bins": DENSITY_BINS,
            "layout_grid_size": 301,
            "goal_event_window_steps": GOAL_EVENT_WINDOW,
        },
        "provenance": provenance,
    }
    _write_json(summary_path, summary)
    tracked_inputs = [
        representative_path,
        density_path,
        layouts_path,
        schema_path,
        summary_path,
    ]
    manifest = {
        "schema_version": 1,
        "git_commit_at_replay": _git_commit(repository_root),
        "command": (
            "env PYTHONNOUSERSITE=1 PYTHONPATH=src MUJOCO_GL=egl "
            "/home/jerry/anaconda3/envs/stl-stage1/bin/python "
            "scripts/replay_stage1_spatial_trajectories.py "
            f"--output-root {output_root}"
        ),
        "source_files": {
            "module": {
                "path": str(Path(__file__).resolve()),
                "sha256": _sha256(Path(__file__).resolve()),
            },
            "analysis_episode_table": {
                "path": str(repository_root / ANALYSIS_EPISODES.relative_to(REPOSITORY_ROOT)),
                "sha256": _sha256(repository_root / ANALYSIS_EPISODES.relative_to(REPOSITORY_ROOT)),
            },
        },
        "compact_artifacts": {
            path.relative_to(output_root).as_posix(): {
                "path": str(path),
                "sha256": _sha256(path),
                "bytes": path.stat().st_size,
            }
            for path in tracked_inputs
        },
        "local_full_geometry": {
            "path": str(full_path),
            "sha256": _sha256(full_path),
            "bytes": full_path.stat().st_size,
            "row_count": accumulator.row_count,
            "tracked_by_git": False,
        },
    }
    _write_json(manifest_path, manifest)
    return {**summary, "manifest": manifest}


def verify_replay_artifacts(output_root: Path) -> Dict[str, Any]:
    """Load a replay manifest and reject missing or hash-mismatched artifacts."""

    manifest = _load_json(output_root / "replay_manifest.json")
    for relative_path, record in manifest["compact_artifacts"].items():
        path = output_root / relative_path
        if not path.is_file() or _sha256(path) != str(record["sha256"]):
            raise RuntimeError(f"spatial replay artifact hash mismatch: {path}")
    return manifest


__all__ = [
    "DENSITY_BINS",
    "EVENT_DENSITIES",
    "EXTREME_CASES",
    "GEOMETRY_FIELDS",
    "SpatialAccumulator",
    "frozen_spatial_cases",
    "geometry_snapshot",
    "run_spatial_replay",
    "sampled_layout_fractions",
    "select_median_paired_case",
    "verify_replay_artifacts",
]
