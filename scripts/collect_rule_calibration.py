#!/usr/bin/env python3
"""Collect and summarize the fixed Stage I parameter-calibration protocol."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import sys
from importlib import metadata
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

import numpy as np
import safety_gymnasium


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPOSITORY_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from safety_stl.signals import (  # noqa: E402
    distance_from_observation,
    simulator_nearest_hazard_center_distance,
)


ENVIRONMENT_ID = "SafetyPointGoal1-v0"
CONTROLLED_SEEDS = tuple(range(1000, 1030))
RANDOM_SEEDS = tuple(range(2000, 2030))
PRIMARY_WARNINGS = (0.35, 0.45, 0.55)
PRIMARY_MARGINS = (0.10, 0.20)
FALLBACK_WARNINGS = (0.30, 0.60, 0.75)
FALLBACK_MARGINS = (0.10, 0.20, 0.30)

CSV_FIELDS = (
    "sample_index",
    "action_index",
    "seed",
    "policy",
    "phase",
    "target_hazard_index",
    "action_forward",
    "action_turn",
    "reward",
    "native_cost",
    "cost_hazards_info",
    "terminated",
    "truncated",
    "agent_x",
    "agent_y",
    "target_hazard_center_distance",
    "nearest_hazard_distance_public",
    "nearest_hazard_center_distance_simulator",
    "public_distance_reconstruction_error",
)


def parse_seed_range(value: str) -> Tuple[int, ...]:
    """Parse an inclusive ``START:END`` seed range."""

    try:
        start_text, end_text = value.split(":", maxsplit=1)
        start, end = int(start_text), int(end_text)
    except (ValueError, TypeError) as error:
        raise argparse.ArgumentTypeError("seed range must be START:END") from error
    if end < start:
        raise argparse.ArgumentTypeError("seed range END must be >= START")
    return tuple(range(start, end + 1))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def observation_distance(environment: Any, observation: Any) -> float:
    schema = environment.unwrapped.task.obs_info.obs_space_dict
    return distance_from_observation(observation, schema, lidar_range=3.0)


def nearest_hazard_index(task: Any) -> int:
    agent = np.asarray(task.agent.pos, dtype=np.float64)[:2]
    hazards = np.asarray(task.hazards.pos, dtype=np.float64)[:, :2]
    return int(np.argmin(np.linalg.norm(hazards - agent, axis=1)))


def select_outer_hazard(task: Any) -> int:
    """Select a deterministic outer hazard with a clear approach segment."""

    agent = np.asarray(task.agent.pos, dtype=np.float64)[:2]
    hazards = np.asarray(task.hazards.pos, dtype=np.float64)[:, :2]
    centroid = np.mean(hazards, axis=0)
    radial = np.linalg.norm(hazards - centroid, axis=1)
    distance_from_agent = np.linalg.norm(hazards - agent, axis=1)
    radial_scaled = radial / max(float(np.max(radial)), 1e-12)
    distance_scaled = distance_from_agent / max(float(np.max(distance_from_agent)), 1e-12)
    clearances = []
    for index, target in enumerate(hazards):
        segment = target - agent
        squared_length = float(np.dot(segment, segment))
        other_hazards = np.delete(hazards, index, axis=0)
        if squared_length < 1e-12:
            clearance = 0.0
        else:
            projection = np.clip(((other_hazards - agent) @ segment) / squared_length, 0.0, 1.0)
            closest = agent + projection[:, None] * segment
            clearance = float(np.min(np.linalg.norm(other_hazards - closest, axis=1)))
        clearances.append(clearance)
    clearance_values = np.asarray(clearances, dtype=np.float64)
    clearance_scaled = clearance_values / max(float(np.max(clearance_values)), 1e-12)
    score = 1.5 * clearance_scaled + radial_scaled - 0.25 * distance_scaled
    return int(np.argmax(score))


def select_escape_waypoint(
    task: Any,
    target_hazard: int,
    initial_agent: np.ndarray,
) -> np.ndarray:
    """Choose a clear outward ray without crossing the approached hazard."""

    hazards = np.asarray(task.hazards.pos, dtype=np.float64)[:, :2]
    target = hazards[target_hazard]
    others = np.delete(hazards, target_hazard, axis=0)
    initial_direction = np.asarray(initial_agent, dtype=np.float64)[:2] - target
    initial_direction /= max(float(np.linalg.norm(initial_direction)), 1e-9)
    best_score = -float("inf")
    best_endpoint = target + 3.0 * initial_direction
    for angle in np.linspace(0.0, 2.0 * math.pi, 360, endpoint=False):
        direction = np.asarray([math.cos(angle), math.sin(angle)], dtype=np.float64)
        alignment = float(np.dot(direction, initial_direction))
        if alignment < 0.8:
            continue
        endpoint = target + 3.0 * direction
        segment = endpoint - target
        squared_length = float(np.dot(segment, segment))
        projection = np.clip(((others - target) @ segment) / squared_length, 0.0, 1.0)
        closest = target + projection[:, None] * segment
        path_clearance = float(np.min(np.linalg.norm(others - closest, axis=1)))
        endpoint_clearance = float(np.min(np.linalg.norm(others - endpoint, axis=1)))
        score = path_clearance + 0.15 * endpoint_clearance + 0.10 * alignment
        if score > best_score:
            best_score = score
            best_endpoint = endpoint
    return best_endpoint


def steering_action(
    task: Any,
    target_xy: np.ndarray,
    *,
    forward_cap: float = 1.0,
    reverse_while_turning: bool = False,
) -> np.ndarray:
    """Deterministically steer the Point agent toward a privileged waypoint."""

    agent_xy = np.asarray(task.agent.pos, dtype=np.float64)[:2]
    vector_world = np.asarray(target_xy, dtype=np.float64)[:2] - agent_xy
    vector_ego = np.asarray([vector_world[0], vector_world[1], 0.0]) @ np.asarray(
        task.agent.mat,
        dtype=np.float64,
    )
    heading_error = math.atan2(float(vector_ego[1]), float(vector_ego[0]))
    turn = float(np.clip(2.5 * heading_error, -1.0, 1.0))
    if reverse_while_turning and abs(heading_error) > 1.2:
        forward = -1.0
    elif abs(heading_error) < 0.35:
        forward = forward_cap
    else:
        forward = min(0.05, forward_cap)
    return np.asarray([forward, turn], dtype=np.float64)


def controlled_action(
    task: Any,
    target_hazard: int,
    phase: str,
    escape_waypoint: np.ndarray,
) -> np.ndarray:
    hazards = np.asarray(task.hazards.pos, dtype=np.float64)[:, :2]
    target = hazards[target_hazard]
    if phase == "approach":
        waypoint = target
        target_distance = float(
            np.linalg.norm(np.asarray(task.agent.pos, dtype=np.float64)[:2] - target),
        )
        if target_distance > 0.60:
            forward_cap = 1.0
        elif target_distance > 0.40:
            forward_cap = 0.50
        elif target_distance > 0.28:
            forward_cap = 0.20
        else:
            forward_cap = 0.05
        return steering_action(task, waypoint, forward_cap=forward_cap)
    elif phase == "brake":
        return np.asarray([-1.0, 0.0], dtype=np.float64)
    else:
        return steering_action(task, escape_waypoint, reverse_while_turning=True)


def row_for_sample(
    environment: Any,
    observation: Any,
    *,
    sample_index: int,
    action_index: Any,
    seed: int,
    policy: str,
    phase: str,
    target_hazard_index: Any,
    action: Any,
    reward: Any,
    native_cost: Any,
    info: Dict[str, Any],
    terminated: bool,
    truncated: bool,
) -> Dict[str, Any]:
    task = environment.unwrapped.task
    public_distance = observation_distance(environment, observation)
    simulator_distance = simulator_nearest_hazard_center_distance(task)
    agent = np.asarray(task.agent.pos, dtype=np.float64)[:2]
    if target_hazard_index is None:
        target_distance = None
    else:
        target_position = np.asarray(task.hazards.pos[int(target_hazard_index)], dtype=np.float64)[:2]
        target_distance = float(np.linalg.norm(target_position - agent))
    if action is None:
        action_forward, action_turn = None, None
    else:
        action_forward, action_turn = float(action[0]), float(action[1])
    return {
        "sample_index": sample_index,
        "action_index": action_index,
        "seed": seed,
        "policy": policy,
        "phase": phase,
        "target_hazard_index": target_hazard_index,
        "action_forward": action_forward,
        "action_turn": action_turn,
        "reward": None if reward is None else float(reward),
        "native_cost": None if native_cost is None else float(native_cost),
        "cost_hazards_info": None
        if "cost_hazards" not in info
        else float(info["cost_hazards"]),
        "terminated": bool(terminated),
        "truncated": bool(truncated),
        "agent_x": float(agent[0]),
        "agent_y": float(agent[1]),
        "target_hazard_center_distance": target_distance,
        "nearest_hazard_distance_public": public_distance,
        "nearest_hazard_center_distance_simulator": simulator_distance,
        "public_distance_reconstruction_error": abs(public_distance - min(3.0, simulator_distance)),
    }


def write_rows(path: Path, rows: Sequence[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def collect_controlled(seed: int, raw_directory: Path, max_steps: int) -> Dict[str, Any]:
    environment = safety_gymnasium.make(ENVIRONMENT_ID)
    try:
        observation, info = environment.reset(seed=seed)
        task = environment.unwrapped.task
        target_hazard = select_outer_hazard(task)
        target_position = np.asarray(task.hazards.pos[target_hazard], dtype=np.float64)[:2]
        initial_agent = np.asarray(task.agent.pos, dtype=np.float64)[:2]
        escape_waypoint = select_escape_waypoint(task, target_hazard, initial_agent)
        initial_distance = observation_distance(environment, observation)
        phase = "approach"
        brake_steps_remaining = 0
        rows = [
            row_for_sample(
                environment,
                observation,
                sample_index=0,
                action_index=None,
                seed=seed,
                policy="controlled_approach_escape",
                phase=phase,
                target_hazard_index=target_hazard,
                action=None,
                reward=None,
                native_cost=None,
                info=info,
                terminated=False,
                truncated=False,
            ),
        ]
        reached_approach_target = False
        reached_escape_target = False
        escape_start_sample = None
        termination_reason = "max_steps"

        for action_index in range(max_steps):
            target_distance = float(
                np.linalg.norm(np.asarray(task.agent.pos, dtype=np.float64)[:2] - target_position),
            )
            if phase == "approach" and target_distance <= 0.30:
                phase = "brake"
                brake_steps_remaining = 8
                reached_approach_target = True
                escape_start_sample = action_index
            action = controlled_action(task, target_hazard, phase, escape_waypoint)
            observation, reward, native_cost, terminated, truncated, info = environment.step(action)
            sample_index = action_index + 1
            rows.append(
                row_for_sample(
                    environment,
                    observation,
                    sample_index=sample_index,
                    action_index=action_index,
                    seed=seed,
                    policy="controlled_approach_escape",
                    phase=phase,
                    target_hazard_index=target_hazard,
                    action=action,
                    reward=reward,
                    native_cost=native_cost,
                    info=info,
                    terminated=terminated,
                    truncated=truncated,
                ),
            )
            if phase == "brake":
                brake_steps_remaining -= 1
                if brake_steps_remaining == 0:
                    phase = "escape"
            if phase in ("brake", "escape") and rows[-1]["nearest_hazard_distance_public"] > 0.9:
                reached_escape_target = True
                termination_reason = "distance_above_0.9"
                break
            if terminated or truncated:
                termination_reason = "terminated" if terminated else "truncated"
                break

        output = raw_directory / f"controlled_seed_{seed}.csv"
        write_rows(output, rows)
        return {
            "seed": seed,
            "file": str(output.relative_to(raw_directory.parent)),
            "sha256": sha256_file(output),
            "samples": len(rows),
            "actions": len(rows) - 1,
            "initial_agent_xy": initial_agent.tolist(),
            "initial_public_distance": initial_distance,
            "target_hazard_index": target_hazard,
            "target_hazard_xy": target_position.tolist(),
            "escape_waypoint_xy": escape_waypoint.tolist(),
            "reached_approach_target": reached_approach_target,
            "escape_start_sample": escape_start_sample,
            "reached_escape_target": reached_escape_target,
            "termination_reason": termination_reason,
            "minimum_public_distance": min(row["nearest_hazard_distance_public"] for row in rows),
            "maximum_reconstruction_error": max(
                row["public_distance_reconstruction_error"] for row in rows
            ),
        }
    finally:
        environment.close()


def collect_random(seed: int, raw_directory: Path, max_steps: int) -> Dict[str, Any]:
    environment = safety_gymnasium.make(ENVIRONMENT_ID)
    rng = np.random.default_rng(seed)
    try:
        observation, info = environment.reset(seed=seed)
        rows = [
            row_for_sample(
                environment,
                observation,
                sample_index=0,
                action_index=None,
                seed=seed,
                policy="random",
                phase="random",
                target_hazard_index=None,
                action=None,
                reward=None,
                native_cost=None,
                info=info,
                terminated=False,
                truncated=False,
            ),
        ]
        for action_index in range(max_steps):
            action = rng.uniform(environment.action_space.low, environment.action_space.high)
            observation, reward, native_cost, terminated, truncated, info = environment.step(action)
            rows.append(
                row_for_sample(
                    environment,
                    observation,
                    sample_index=action_index + 1,
                    action_index=action_index,
                    seed=seed,
                    policy="random",
                    phase="random",
                    target_hazard_index=None,
                    action=action,
                    reward=reward,
                    native_cost=native_cost,
                    info=info,
                    terminated=terminated,
                    truncated=truncated,
                ),
            )
            if terminated or truncated:
                break
        output = raw_directory / f"random_seed_{seed}.csv"
        write_rows(output, rows)
        return {
            "seed": seed,
            "file": str(output.relative_to(raw_directory.parent)),
            "sha256": sha256_file(output),
            "samples": len(rows),
            "actions": len(rows) - 1,
            "minimum_public_distance": min(row["nearest_hazard_distance_public"] for row in rows),
            "maximum_reconstruction_error": max(
                row["public_distance_reconstruction_error"] for row in rows
            ),
            "terminated": bool(rows[-1]["terminated"]),
            "truncated": bool(rows[-1]["truncated"]),
        }
    finally:
        environment.close()


def load_distances(path: Path) -> List[float]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return [
            float(row["nearest_hazard_distance_public"])
            for row in csv.DictReader(handle)
        ]


def empirical_quantile(values: Sequence[int], probability: float) -> float:
    """Use NumPy's linear empirical quantile with a cross-version fallback."""

    try:
        return float(np.quantile(values, probability, method="linear"))
    except TypeError:  # NumPy before 1.22
        return float(np.quantile(values, probability, interpolation="linear"))


def first_trigger_and_recovery(
    distances: Sequence[float],
    d_warn: float,
    d_safe: float,
) -> Tuple[Any, Any]:
    trigger = next((index for index, value in enumerate(distances) if value < d_warn), None)
    if trigger is None:
        return None, None
    recovery = next(
        (index for index in range(trigger, len(distances)) if distances[index] >= d_safe),
        None,
    )
    return trigger, recovery


def candidate_statistics(
    controlled: Sequence[Dict[str, Any]],
    random_runs: Sequence[Dict[str, Any]],
    output_directory: Path,
    warnings: Iterable[float],
    margins: Iterable[float],
    grid_name: str,
) -> List[Dict[str, Any]]:
    controlled_distances = {
        run["seed"]: load_distances(output_directory / run["file"]) for run in controlled
    }
    random_distances = {
        run["seed"]: load_distances(output_directory / run["file"]) for run in random_runs
    }
    statistics = []
    for d_warn in warnings:
        for margin in margins:
            d_safe = round(d_warn + margin, 12)
            recoveries = []
            trial_details = []
            for seed, distances in controlled_distances.items():
                trigger, recovery = first_trigger_and_recovery(distances, d_warn, d_safe)
                recovery_steps = None if recovery is None else recovery - trigger
                if recovery_steps is not None:
                    recoveries.append(recovery_steps)
                trial_details.append(
                    {
                        "seed": seed,
                        "trigger_step": trigger,
                        "recovery_step": recovery,
                        "recovery_steps": recovery_steps,
                    },
                )
            percentile = empirical_quantile(recoveries, 0.95) if recoveries else None
            deadline = None if percentile is None else max(5, int(math.ceil(1.25 * percentile)))
            random_trigger_seeds = [
                seed
                for seed, distances in random_distances.items()
                if any(value < d_warn for value in distances)
            ]
            valid_count = len(recoveries)
            eligible = (
                0.2 < d_warn < d_safe < 3.0
                and valid_count >= 27
                and deadline is not None
                and deadline <= 100
            )
            statistics.append(
                {
                    "grid": grid_name,
                    "d_warn": d_warn,
                    "d_safe": d_safe,
                    "hysteresis_margin": margin,
                    "valid_controlled_recoveries": valid_count,
                    "controlled_trials": len(controlled),
                    "recovery_steps": recoveries,
                    "recovery_q95_linear": percentile,
                    "deadline_steps": deadline,
                    "random_trigger_count": len(random_trigger_seeds),
                    "random_trials": len(random_runs),
                    "random_trigger_rate": len(random_trigger_seeds) / len(random_runs),
                    "random_trigger_seeds": random_trigger_seeds,
                    "eligible": eligible,
                    "trial_details": trial_details,
                },
            )
    return statistics


def selection_key(candidate: Dict[str, Any]) -> Tuple[Any, ...]:
    rate = candidate["random_trigger_rate"]
    in_preferred_band = 0.10 <= rate <= 0.80
    return (
        0 if in_preferred_band else 1,
        abs(rate - 0.50),
        -candidate["hysteresis_margin"],
        candidate["deadline_steps"],
        candidate["d_warn"],
    )


def select_candidate(
    controlled: Sequence[Dict[str, Any]],
    random_runs: Sequence[Dict[str, Any]],
    output_directory: Path,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any], bool]:
    primary = candidate_statistics(
        controlled,
        random_runs,
        output_directory,
        PRIMARY_WARNINGS,
        PRIMARY_MARGINS,
        "primary",
    )
    eligible = [candidate for candidate in primary if candidate["eligible"]]
    used_fallback = False
    all_candidates = list(primary)
    if not eligible:
        fallback = candidate_statistics(
            controlled,
            random_runs,
            output_directory,
            FALLBACK_WARNINGS,
            FALLBACK_MARGINS,
            "fallback",
        )
        all_candidates.extend(fallback)
        eligible = [candidate for candidate in fallback if candidate["eligible"]]
        used_fallback = True
    if not eligible:
        raise RuntimeError("neither primary nor fallback calibration grid has an eligible candidate")
    chosen = min(eligible, key=selection_key)
    return all_candidates, chosen, used_fallback


def installed_version(distribution: str) -> str:
    try:
        return metadata.version(distribution)
    except metadata.PackageNotFoundError:
        return "not-installed"


def build_summary(
    controlled: Sequence[Dict[str, Any]],
    random_runs: Sequence[Dict[str, Any]],
    candidates: Sequence[Dict[str, Any]],
    chosen: Dict[str, Any],
    used_fallback: bool,
) -> Dict[str, Any]:
    return {
        "schema_version": 1,
        "environment_id": ENVIRONMENT_ID,
        "distance_signal": "3 * (1 - max(hazards_lidar))",
        "distance_semantics": "public nearest agent-origin-to-hazard-center distance capped at 3",
        "software": {
            "python": platform.python_version(),
            "numpy": installed_version("numpy"),
            "safety-gymnasium": installed_version("safety-gymnasium"),
            "gymnasium": installed_version("gymnasium"),
            "mujoco": installed_version("mujoco"),
            "omnisafe": installed_version("omnisafe"),
            "rtamt": installed_version("rtamt"),
            "torch": installed_version("torch"),
        },
        "controller": {
            "privileged_geometry_used": True,
            "purpose": "controlled calibration data generation only",
            "target_selection": "outer hazard maximizing radial position with distance penalty",
            "approach_phase_switch_center_distance": 0.30,
            "intended_minimum_center_distance": 0.25,
            "escape_waypoint": (
                "3.0-unit ray chosen from 360 candidates on the approach-side half-plane; "
                "score maximizes clearance from all non-target hazards"
            ),
            "escape_stop_public_distance": 0.9,
            "action_law": (
                "turn=clip(2.5*heading_error,-1,1); approach forward cap decreases "
                "from 1.0 to 0.05 near the target; escape starts with eight [-1,0] "
                "braking actions and then applies -1.0 reverse braking while "
                "|heading_error|>1.2"
            ),
        },
        "controlled_seed_range": [min(run["seed"] for run in controlled), max(run["seed"] for run in controlled)],
        "random_seed_range": [min(run["seed"] for run in random_runs), max(run["seed"] for run in random_runs)],
        "controlled_runs": list(controlled),
        "random_runs": list(random_runs),
        "candidate_statistics": list(candidates),
        "fallback_grid_used": used_fallback,
        "selection_priority": [
            "random trigger rate in [0.10, 0.80]",
            "random trigger rate closest to 0.50",
            "larger hysteresis margin",
            "smaller deadline_steps",
        ],
        "selected_parameters": {
            "d_warn": chosen["d_warn"],
            "d_safe": chosen["d_safe"],
            "deadline_steps": chosen["deadline_steps"],
            "supporting_grid": chosen["grid"],
            "valid_controlled_recoveries": chosen["valid_controlled_recoveries"],
            "recovery_q95_linear": chosen["recovery_q95_linear"],
            "random_trigger_rate": chosen["random_trigger_rate"],
        },
        "maximum_reconstruction_error": max(
            run["maximum_reconstruction_error"] for run in list(controlled) + list(random_runs)
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPOSITORY_ROOT / "results" / "rule_calibration",
    )
    parser.add_argument(
        "--controlled-seeds",
        type=parse_seed_range,
        default=CONTROLLED_SEEDS,
        help="inclusive range, default: 1000:1029",
    )
    parser.add_argument(
        "--random-seeds",
        type=parse_seed_range,
        default=RANDOM_SEEDS,
        help="inclusive range, default: 2000:2029",
    )
    parser.add_argument("--max-steps", type=int, default=1000)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_directory = args.output_dir.resolve()
    raw_directory = output_directory / "raw"
    raw_directory.mkdir(parents=True, exist_ok=True)

    controlled = [
        collect_controlled(seed, raw_directory, args.max_steps) for seed in args.controlled_seeds
    ]
    random_runs = [
        collect_random(seed, raw_directory, args.max_steps) for seed in args.random_seeds
    ]
    candidates, chosen, used_fallback = select_candidate(
        controlled,
        random_runs,
        output_directory,
    )
    summary = build_summary(controlled, random_runs, candidates, chosen, used_fallback)
    summary_path = output_directory / "summary.json"
    with summary_path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps(summary["selected_parameters"], indent=2, sort_keys=True))
    print(f"wrote {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
