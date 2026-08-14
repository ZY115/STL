#!/usr/bin/env python3
"""Exercise real fixed-route resets, ordered goals, rendering and route geometry."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle  # noqa: E402
import numpy as np
import safety_gymnasium

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from safety_stl.fixed_route import install_fixed_route, load_fixed_route_scenario  # noqa: E402
from safety_stl.signals import distance_from_observation, simulator_nearest_hazard_center_distance  # noqa: E402


def _steer(task: Any) -> np.ndarray:
    vector = np.asarray(task.goal.pos)[:2] - np.asarray(task.agent.pos)[:2]
    ego = np.asarray([vector[0], vector[1], 0.0]) @ np.asarray(task.agent.mat)
    error = math.atan2(float(ego[1]), float(ego[0]))
    return np.asarray([0.35 if abs(error) < 0.12 else 0.0, np.clip(2.5 * error, -1, 1)])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/fixed_route_v1/scenario.yaml")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results/fixed_route_v1/lifecycle")
    parser.add_argument("--seed", type=int, default=9173)
    parser.add_argument("--max-steps", type=int, default=1000)
    options = parser.parse_args()
    scenario = load_fixed_route_scenario(options.config)
    environment = safety_gymnasium.make(scenario.environment_id, render_mode="rgb_array")
    install_fixed_route(environment.unwrapped.task, scenario)
    reset_records: List[Dict[str, Any]] = []
    try:
        for seed in (options.seed, options.seed + 1):
            observation, _ = environment.reset(seed=seed)
            task = environment.unwrapped.task
            public = distance_from_observation(observation, task.obs_info.obs_space_dict, 3.0)
            reset_records.append({
                "seed": seed,
                "agent": np.asarray(task.agent.pos)[:2].tolist(),
                "goal": np.asarray(task.goal.pos)[:2].tolist(),
                "hazards": np.asarray(task.hazards.pos)[:, :2].tolist(),
                "vases": np.asarray(task.vases.pos)[:, :2].tolist(),
                "public_distance": public,
                "simulator_distance": simulator_nearest_hazard_center_distance(task),
                "native_cost": float(task.calculate_cost()["cost_sum"]),
            })
        observation, _ = environment.reset(seed=options.seed)
        task = environment.unwrapped.task
        rows: List[Dict[str, Any]] = []
        goal_events: List[Dict[str, Any]] = []
        initial_index = int(task.fixed_route_goal_index)
        for step in range(options.max_steps + 1):
            distance = distance_from_observation(observation, task.obs_info.obs_space_dict, 3.0)
            rows.append({
                "sample_index": step,
                "agent_x": float(task.agent.pos[0]),
                "agent_y": float(task.agent.pos[1]),
                "goal_index": int(task.fixed_route_goal_index),
                "goal_x": float(task.goal.pos[0]),
                "goal_y": float(task.goal.pos[1]),
                "distance": distance,
            })
            if len(goal_events) >= len(scenario.goal_sequence):
                break
            action = _steer(task)
            observation, _, _, terminated, truncated, info = environment.step(action)
            if info.get("goal_met"):
                goal_events.append({"sample_index": step + 1, "next_goal_index": int(task.fixed_route_goal_index)})
            if terminated or truncated:
                break
        frame = environment.render()
    finally:
        environment.close()

    options.output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = options.output_dir / "route_attempt.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    figure, axis = plt.subplots(figsize=(7.2, 7.2))
    for hazard in scenario.hazard_locations:
        axis.add_patch(Circle(hazard, scenario.hazard_radius, color="#4c78a8", alpha=0.5))
        axis.add_patch(Circle(hazard, scenario.d_warn, fill=False, color="#d62728", linestyle="--"))
        axis.add_patch(Circle(hazard, scenario.d_safe, fill=False, color="#2ca02c", linestyle=":"))
    axis.plot([row["agent_x"] for row in rows], [row["agent_y"] for row in rows], color="#222222", linewidth=1.2)
    axis.scatter(*scenario.agent_start, marker="o", color="white", edgecolor="black", zorder=5)
    for index, goal in enumerate(scenario.goal_sequence):
        axis.scatter(*goal, marker="*", s=110, label=f"G{index + 1}")
    axis.set(xlim=(-1.55, 1.55), ylim=(-1.55, 1.55), aspect="equal", xlabel="x", ylabel="y", title="Real controlled route-completion attempt")
    axis.grid(alpha=0.15); axis.legend(loc="upper left", fontsize=8)
    figure.tight_layout(); figure.savefig(options.output_dir / "route_attempt.png", dpi=190); plt.close(figure)
    fixed_reset = all(np.allclose(row["agent"], scenario.agent_start, atol=1e-8) for row in reset_records)
    fixed_layout = np.allclose(reset_records[0]["hazards"], reset_records[1]["hazards"], atol=1e-8)
    summary = {
        "status": "passed" if fixed_reset and fixed_layout and len(goal_events) >= 4 else "failed",
        "scenario_id": scenario.scenario_id,
        "reset_records": reset_records,
        "fixed_reset": fixed_reset,
        "fixed_layout_across_resets": bool(fixed_layout),
        "initial_goal_index": initial_index,
        "goal_events": goal_events,
        "completed_full_four_goal_cycle": len(goal_events) >= 4 and goal_events[3]["next_goal_index"] == 0,
        "route_samples": len(rows),
        "minimum_distance": min(float(row["distance"]) for row in rows),
        "render_shape": list(frame.shape),
        "render_finite": bool(np.isfinite(frame).all()),
        "route_csv": str(csv_path),
        "route_figure": str(options.output_dir / "route_attempt.png"),
    }
    (options.output_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    if summary["status"] != "passed":
        raise RuntimeError("fixed-route lifecycle gate failed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
