#!/usr/bin/env python3
"""Generate minimal, tracked monitor fixtures from formal calibration runs."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from statistics import median
from typing import Any, Dict, List, Sequence

import yaml
import numpy as np
import safety_gymnasium

from collect_rule_calibration import (
    controlled_action,
    nearest_hazard_index,
    observation_distance,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CALIBRATION_DIRECTORY = REPOSITORY_ROOT / "results" / "rule_calibration"
SUMMARY_PATH = CALIBRATION_DIRECTORY / "summary.json"
CONFIG_PATH = REPOSITORY_ROOT / "configs" / "stage1_rule.yaml"
FIXTURE_DIRECTORY = REPOSITORY_ROOT / "tests" / "fixtures"

FIXTURE_FIELDS = (
    "fixture_sample_index",
    "source_sample_index",
    "source_seed",
    "source_policy",
    "source_phase",
    "action_forward",
    "action_turn",
    "reward",
    "native_cost",
    "nearest_hazard_distance_public",
    "terminated",
    "truncated",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def select_trials(summary: Dict[str, Any], deadline_steps: int) -> Dict[str, Dict[str, Any]]:
    selected = summary["selected_parameters"]
    candidate = next(
        item
        for item in summary["candidate_statistics"]
        if item["grid"] == selected["supporting_grid"]
        and item["d_warn"] == selected["d_warn"]
        and item["d_safe"] == selected["d_safe"]
    )
    trials = [item for item in candidate["trial_details"] if item["recovery_steps"] is not None]
    samples_by_seed = {item["seed"]: item["samples"] for item in summary["controlled_runs"]}
    on_time_trials = [
        item
        for item in trials
        if item["recovery_steps"] <= deadline_steps
        and samples_by_seed[item["seed"]] > item["trigger_step"] + deadline_steps
    ]
    if not on_time_trials:
        raise RuntimeError("calibration produced no on-time recovery fixture candidate")
    center = median(item["recovery_steps"] for item in on_time_trials)
    on_time = min(on_time_trials, key=lambda item: (abs(item["recovery_steps"] - center), item["seed"]))
    return {"on_time": on_time, "unresolved": on_time}


def crop_rows(
    source_rows: Sequence[Dict[str, str]],
    start: int,
    stop: int,
    *,
    terminal_mode: str = "none",
) -> List[Dict[str, Any]]:
    selected = source_rows[start : stop + 1]
    if not selected:
        raise ValueError("fixture crop is empty")
    output = []
    for fixture_index, row in enumerate(selected):
        output.append(
            {
                "fixture_sample_index": fixture_index,
                "source_sample_index": int(row["sample_index"]),
                "source_seed": int(row["seed"]),
                "source_policy": row["policy"],
                "source_phase": row["phase"],
                "action_forward": row["action_forward"],
                "action_turn": row["action_turn"],
                "reward": row["reward"],
                "native_cost": row["native_cost"],
                "nearest_hazard_distance_public": row["nearest_hazard_distance_public"],
                "terminated": False,
                "truncated": False,
            },
        )
    if terminal_mode == "terminated":
        output[-1]["terminated"] = True
    elif terminal_mode == "truncated":
        output[-1]["truncated"] = True
    elif terminal_mode != "none":
        raise ValueError(f"unknown terminal mode {terminal_mode}")
    return output


def write_fixture(path: Path, rows: Sequence[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIXTURE_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def create_fixture(
    label: str,
    trial: Dict[str, Any],
    deadline_steps: int,
    terminal_mode: str,
) -> Dict[str, Any]:
    source_path = CALIBRATION_DIRECTORY / "raw" / f"controlled_seed_{trial['seed']}.csv"
    source_rows = load_rows(source_path)
    trigger = int(trial["trigger_step"])
    recovery = int(trial["recovery_step"])
    start = max(0, trigger - 2)
    relative_trigger = trigger - start
    if label == "on_time":
        stop = trigger + deadline_steps
        expected_outcome = "recovery"
    elif label == "unresolved":
        stop = min(trigger + 10, trigger + deadline_steps - 1, recovery - 1)
        expected_outcome = "terminal_unresolved"
    else:
        raise ValueError(label)
    if stop >= len(source_rows):
        raise RuntimeError(f"source seed {trial['seed']} is too short for fixture {label}")
    rows = crop_rows(source_rows, start, stop, terminal_mode=terminal_mode)
    path = FIXTURE_DIRECTORY / f"{label}.csv"
    write_fixture(path, rows)
    return {
        "label": label,
        "file": path.name,
        "sha256": sha256_file(path),
        "source_file": str(source_path.relative_to(REPOSITORY_ROOT)),
        "source_sha256": sha256_file(source_path),
        "source_seed": trial["seed"],
        "source_trigger_step": trigger,
        "source_recovery_step": recovery,
        "source_recovery_steps": trial["recovery_steps"],
        "crop_source_start": start,
        "crop_source_stop": stop,
        "fixture_trigger_step": relative_trigger,
        "fixture_deadline_step": relative_trigger + deadline_steps,
        "fixture_samples": len(rows),
        "terminal_mode": terminal_mode,
        "expected_outcome": expected_outcome,
        "collector_imposed_terminal_flag": terminal_mode != "none",
    }


def generate_violation_rows(config: Dict[str, Any], seed: int) -> Dict[str, Any]:
    """Run a real near-hazard hold trajectory through the inclusive deadline."""

    environment = safety_gymnasium.make(config["environment_id"])
    try:
        observation, _ = environment.reset(seed=seed)
        task = environment.unwrapped.task
        target_hazard = nearest_hazard_index(task)
        target_position = np.asarray(task.hazards.pos[target_hazard], dtype=np.float64)[:2]
        phase = "approach"
        samples: List[Dict[str, Any]] = []
        trigger_step = None
        sample_index = 0
        previous_action = None
        previous_reward = None
        previous_native_cost = None

        while sample_index <= 1000:
            distance = observation_distance(environment, observation)
            if trigger_step is None and distance < config["d_warn"]:
                trigger_step = sample_index
            samples.append(
                {
                    "source_sample_index": sample_index,
                    "source_seed": seed,
                    "source_policy": "controlled_approach_hold",
                    "source_phase": phase,
                    "action_forward": "" if previous_action is None else previous_action[0],
                    "action_turn": "" if previous_action is None else previous_action[1],
                    "reward": "" if previous_reward is None else previous_reward,
                    "native_cost": "" if previous_native_cost is None else previous_native_cost,
                    "nearest_hazard_distance_public": distance,
                    "terminated": False,
                    "truncated": False,
                },
            )
            if trigger_step is not None and sample_index >= trigger_step + config["deadline_steps"] + 5:
                break

            target_distance = float(
                np.linalg.norm(np.asarray(task.agent.pos, dtype=np.float64)[:2] - target_position),
            )
            velocity_world = np.asarray(task.agent.vel, dtype=np.float64)
            velocity_ego = velocity_world @ np.asarray(task.agent.mat, dtype=np.float64)
            if phase == "approach" and target_distance <= 0.45:
                phase = "decelerate"
            if phase == "decelerate" and float(velocity_ego[0]) <= 0.01:
                phase = "final_approach"
            if phase == "final_approach" and target_distance <= 0.28:
                phase = "hold"
            if phase == "hold":
                forward = float(np.clip(-10.0 * float(velocity_ego[0]), -1.0, 1.0))
                action = np.asarray([forward, 0.0], dtype=np.float64)
            else:
                action = controlled_action(task, target_hazard, phase)
            observation, reward, native_cost, terminated, truncated, _ = environment.step(action)
            if terminated or truncated:
                raise RuntimeError("violation fixture environment ended before its monitor deadline")
            previous_action = action
            previous_reward = float(reward)
            previous_native_cost = float(native_cost)
            sample_index += 1

        if trigger_step is None:
            raise RuntimeError("violation fixture never entered the warning zone")
        deadline = trigger_step + int(config["deadline_steps"])
        if max(
            float(row["nearest_hazard_distance_public"])
            for row in samples[trigger_step : deadline + 1]
        ) >= config["d_safe"]:
            raise RuntimeError("hold controller recovered before the intended violation deadline")
        start = max(0, trigger_step - 2)
        selected = samples[start:]
        for fixture_index, row in enumerate(selected):
            row["fixture_sample_index"] = fixture_index
        return {
            "rows": selected,
            "source_trigger_step": trigger_step,
            "fixture_trigger_step": trigger_step - start,
            "fixture_deadline_step": trigger_step - start + int(config["deadline_steps"]),
            "target_hazard_index": target_hazard,
            "target_hazard_xy": target_position.tolist(),
        }
    finally:
        environment.close()


def create_violation_fixture(config: Dict[str, Any]) -> Dict[str, Any]:
    last_error = None
    for seed in range(3000, 3010):
        try:
            generated = generate_violation_rows(config, seed)
            break
        except RuntimeError as error:
            last_error = error
    else:
        raise RuntimeError("failed to generate a real deadline-violation fixture") from last_error
    path = FIXTURE_DIRECTORY / "violation.csv"
    write_fixture(path, generated["rows"])
    return {
        "label": "violation",
        "file": path.name,
        "sha256": sha256_file(path),
        "source_type": "reproducible_live_environment_generation",
        "source_seed": generated["rows"][0]["source_seed"],
        "source_policy": "controlled_approach_hold",
        "target_hazard_index": generated["target_hazard_index"],
        "target_hazard_xy": generated["target_hazard_xy"],
        "source_trigger_step": generated["source_trigger_step"],
        "fixture_trigger_step": generated["fixture_trigger_step"],
        "fixture_deadline_step": generated["fixture_deadline_step"],
        "fixture_samples": len(generated["rows"]),
        "terminal_mode": "none",
        "expected_outcome": "deadline_violation",
        "collector_imposed_terminal_flag": False,
    }


def main() -> int:
    with SUMMARY_PATH.open("r", encoding="utf-8") as handle:
        summary = json.load(handle)
    with CONFIG_PATH.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    selected = summary["selected_parameters"]
    for key in ("d_warn", "d_safe", "deadline_steps"):
        if config[key] != selected[key]:
            raise RuntimeError(f"config {key} does not match calibration summary")

    deadline_steps = int(config["deadline_steps"])
    trials = select_trials(summary, deadline_steps)
    fixtures = [
        create_fixture("on_time", trials["on_time"], deadline_steps, "none"),
        create_violation_fixture(config),
        create_fixture("unresolved", trials["unresolved"], deadline_steps, "truncated"),
    ]
    manifest = {
        "schema_version": 1,
        "environment_id": config["environment_id"],
        "d_warn": config["d_warn"],
        "d_safe": config["d_safe"],
        "deadline_steps": deadline_steps,
        "note": (
            "All distances come from real SafetyPointGoal1-v0 executions. On-time and "
            "unresolved traces are cropped from formal calibration runs; violation is "
            "regenerated with the deterministic approach-hold controller. The unresolved "
            "fixture marks its deliberate collection cutoff as truncated."
        ),
        "fixtures": fixtures,
    }
    FIXTURE_DIRECTORY.mkdir(parents=True, exist_ok=True)
    manifest_path = FIXTURE_DIRECTORY / "manifest.json"
    with manifest_path.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
