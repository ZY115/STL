#!/usr/bin/env python3
"""Calibrate the fixed-route 0.25 -> 0.28 recovery deadline on real dynamics."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

import numpy as np
import safety_gymnasium


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from safety_stl.fixed_route import install_fixed_route, load_fixed_route_scenario  # noqa: E402
from safety_stl.monitor import BoundedRecoveryMonitor  # noqa: E402
from safety_stl.oracle import evaluate_trace, rtamt_window_robustness  # noqa: E402
from safety_stl.signals import distance_from_observation  # noqa: E402


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _quantile(values: Sequence[int], probability: float) -> float:
    try:
        return float(np.quantile(values, probability, method="linear"))
    except TypeError:
        return float(np.quantile(values, probability, interpolation="linear"))


def _steer(task: Any, target: np.ndarray, forward: float) -> np.ndarray:
    agent = np.asarray(task.agent.pos, dtype=np.float64)[:2]
    vector = target - agent
    ego = np.asarray([vector[0], vector[1], 0.0]) @ np.asarray(task.agent.mat)
    error = math.atan2(float(ego[1]), float(ego[0]))
    return np.asarray([forward if abs(error) < 0.10 else 0.0, np.clip(2.5 * error, -1, 1)])


def _distance(environment: Any, observation: Any) -> float:
    return distance_from_observation(
        observation,
        environment.unwrapped.task.obs_info.obs_space_dict,
        lidar_range=3.0,
    )


def _trial(config: Path, seed: int, output: Path, max_steps: int) -> Dict[str, Any]:
    scenario = load_fixed_route_scenario(config)
    environment = safety_gymnasium.make(scenario.environment_id)
    rows: List[Dict[str, Any]] = []
    try:
        install_fixed_route(environment.unwrapped.task, scenario)
        observation, _ = environment.reset(seed=seed)
        task = environment.unwrapped.task
        agent = np.asarray(task.agent.pos, dtype=np.float64)[:2]
        hazards = np.asarray(task.hazards.pos, dtype=np.float64)[:, :2]
        target_index = int(np.argmin(np.linalg.norm(hazards - agent, axis=1)))
        target = hazards[target_index].copy()
        phase = "approach"
        trigger_step = None
        recovery_step = None
        trigger_inward_velocity = None
        for step in range(max_steps + 1):
            distance = _distance(environment, observation)
            velocity_ego = np.asarray(task.agent.vel, dtype=np.float64) @ np.asarray(task.agent.mat)
            if trigger_step is None and distance < scenario.d_warn:
                trigger_step = step
                trigger_inward_velocity = float(velocity_ego[0])
            elif trigger_step is not None and recovery_step is None and distance >= scenario.d_safe:
                recovery_step = step
            rows.append(
                {
                    "sample_index": step,
                    "phase": phase,
                    "distance": distance,
                    "agent_x": float(task.agent.pos[0]),
                    "agent_y": float(task.agent.pos[1]),
                    "forward_velocity": float(velocity_ego[0]),
                },
            )
            if recovery_step is not None and distance >= 0.60:
                break
            if step == max_steps:
                break
            target_distance = float(np.linalg.norm(np.asarray(task.agent.pos)[:2] - target))
            if phase == "approach" and target_distance <= 0.38:
                phase = "decelerate"
            if phase == "decelerate" and float(velocity_ego[0]) <= 0.01:
                phase = "final_approach"
            if phase == "final_approach" and distance < 0.235:
                phase = "retreat"
            if phase == "approach":
                action = _steer(task, target, 0.20 if target_distance > 0.75 else 0.12)
            elif phase == "decelerate":
                action = np.asarray([-1.0, 0.0])
            elif phase == "final_approach":
                action = _steer(task, target, 0.04)
            else:
                action = np.asarray([-1.0, 0.0])
            observation, _, _, terminated, truncated, _ = environment.step(action)
            if terminated or truncated:
                break
    finally:
        environment.close()

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    distances = [float(row["distance"]) for row in rows]
    return {
        "seed": seed,
        "target_hazard_index": target_index,
        "trigger_step": trigger_step,
        "recovery_step": recovery_step,
        "recovery_steps": None if recovery_step is None or trigger_step is None else recovery_step - trigger_step,
        "minimum_distance": min(distances),
        "entry_depth": None if trigger_step is None else scenario.d_warn - min(distances[trigger_step : (recovery_step or len(distances)) + 1]),
        "trigger_inward_velocity": trigger_inward_velocity,
        "post_recovery_retrigger": False if recovery_step is None else any(value < scenario.d_warn for value in distances[recovery_step + 1 :]),
        "samples": len(rows),
        "csv": str(output),
        "sha256": _sha256(output),
        "distances": distances,
    }


def _agreement(trials: Sequence[Dict[str, Any]], d_warn: float, d_safe: float, deadline: int) -> Dict[str, Any]:
    event_mismatches = 0
    max_rtamt = 0.0
    completed = 0
    for trial in trials:
        distances = trial["distances"]
        monitor = BoundedRecoveryMonitor(d_warn, d_safe, deadline)
        online = [monitor.reset(distances[0])]
        online.extend(monitor.step(value) for value in distances[1:])
        direct = evaluate_trace(distances, d_warn, d_safe, deadline)
        fields = {
            "trigger": [row.sample_index for row in online if row.stl_warning_trigger],
            "recovery": [row.sample_index for row in online if row.stl_recovery],
            "violation": [row.sample_index for row in online if row.stl_deadline_violation],
            "cost": [row.stl_cost for row in online],
        }
        expected = {
            "trigger": direct.trigger_steps,
            "recovery": direct.recovery_steps,
            "violation": direct.violation_steps,
            "cost": direct.costs,
        }
        event_mismatches += sum(fields[key] != expected[key] for key in fields)
        for window in direct.completed_windows:
            values = distances[window.trigger_step : window.deadline_step + 1]
            rtamt = rtamt_window_robustness(values, d_safe, deadline)
            max_rtamt = max(max_rtamt, abs(rtamt - window.robustness))
            completed += 1
    return {
        "online_direct_event_mismatches": event_mismatches,
        "rtamt_completed_windows": completed,
        "rtamt_max_robustness_difference": max_rtamt,
        "passed": event_mismatches == 0 and max_rtamt <= 1e-9 and completed > 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/fixed_route_v1/scenario.yaml")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results/fixed_route_v1/calibration")
    parser.add_argument("--seed-start", type=int, default=12000)
    parser.add_argument("--trials", type=int, default=30)
    parser.add_argument("--max-steps", type=int, default=400)
    options = parser.parse_args()
    if options.trials < 30:
        raise ValueError("the declared calibration requires at least 30 trials")
    scenario = load_fixed_route_scenario(options.config)
    trials = [
        _trial(options.config, options.seed_start + index, options.output_dir / "raw" / f"trial_{index:03d}.csv", options.max_steps)
        for index in range(options.trials)
    ]
    recovery = [int(row["recovery_steps"]) for row in trials if row["recovery_steps"] is not None]
    if len(recovery) < math.ceil(0.9 * options.trials):
        raise RuntimeError("fewer than 90% of controlled entries recovered")
    q95 = _quantile(recovery, 0.95)
    deadline = max(5, int(math.ceil(1.25 * q95)))
    agreement = _agreement(trials, scenario.d_warn, scenario.d_safe, deadline)
    if not agreement["passed"]:
        raise RuntimeError(f"monitor/oracle/RTAMT gate failed: {agreement}")
    compact_trials = [{key: value for key, value in row.items() if key != "distances"} for row in trials]
    summary = {
        "schema_version": 1,
        "status": "passed",
        "scenario_id": scenario.scenario_id,
        "selection_rule": "max(5, ceil(1.25 * empirical_linear_q95(recovery_steps)))",
        "d_warn": scenario.d_warn,
        "d_safe": scenario.d_safe,
        "trial_count": len(trials),
        "valid_recoveries": len(recovery),
        "failed_recoveries": len(trials) - len(recovery),
        "recovery_steps": recovery,
        "recovery_q95_linear": q95,
        "deadline_steps": deadline,
        "maximum_entry_depth": max(float(row["entry_depth"]) for row in trials if row["entry_depth"] is not None),
        "trigger_inward_velocity_range": [min(float(row["trigger_inward_velocity"]) for row in trials), max(float(row["trigger_inward_velocity"]) for row in trials)],
        "post_recovery_retrigger_count": sum(bool(row["post_recovery_retrigger"]) for row in trials),
        "agreement": agreement,
        "trials": compact_trials,
    }
    options.output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = options.output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: summary[key] for key in ("valid_recoveries", "recovery_q95_linear", "deadline_steps", "agreement")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
