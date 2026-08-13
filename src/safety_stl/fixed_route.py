"""Deterministic SafetyPointGoal1 layout and ordered-goal support.

The controller fixes the scenario inputs, not the agent trajectory.  The
policy still selects every action and may take any dynamically feasible path.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from types import MethodType
from typing import Any, Dict, Iterable, Mapping, Sequence, Tuple

import numpy as np
import yaml


Point = Tuple[float, float]


def _point(value: Any, field: str) -> Point:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) != 2:
        raise ValueError(f"{field} must be a two-number coordinate")
    point = (float(value[0]), float(value[1]))
    if not all(math.isfinite(item) for item in point):
        raise ValueError(f"{field} must contain finite coordinates")
    return point


def _points(value: Any, field: str) -> Tuple[Point, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or not value:
        raise ValueError(f"{field} must be a non-empty coordinate sequence")
    return tuple(_point(item, f"{field}[{index}]") for index, item in enumerate(value))


def _segment_distance(point: Point, start: Point, end: Point) -> float:
    point_array = np.asarray(point, dtype=np.float64)
    start_array = np.asarray(start, dtype=np.float64)
    direction = np.asarray(end, dtype=np.float64) - start_array
    denominator = float(np.dot(direction, direction))
    if denominator == 0.0:
        return float(np.linalg.norm(point_array - start_array))
    fraction = float(np.dot(point_array - start_array, direction) / denominator)
    projection = start_array + np.clip(fraction, 0.0, 1.0) * direction
    return float(np.linalg.norm(point_array - projection))


@dataclass(frozen=True)
class FixedRouteScenario:
    """Validated deterministic layout and candidate STL thresholds."""

    scenario_id: str
    environment_id: str
    status: str
    agent_start: Point
    agent_heading: float
    goal_sequence: Tuple[Point, ...]
    hazard_locations: Tuple[Point, ...]
    vase_locations: Tuple[Point, ...]
    cycle_goal_sequence: bool
    hazard_radius: float
    d_warn: float
    d_safe: float
    deadline_steps: Any

    def route_clearances(self) -> Tuple[float, ...]:
        """Return each straight route segment's nearest hazard-center distance."""

        waypoints = (self.agent_start, *self.goal_sequence)
        return tuple(
            min(_segment_distance(hazard, start, end) for hazard in self.hazard_locations)
            for start, end in zip(waypoints, waypoints[1:])
        )

    def as_dict(self) -> Dict[str, Any]:
        """Return stable machine-readable scenario metadata."""

        return {
            "scenario_id": self.scenario_id,
            "environment_id": self.environment_id,
            "status": self.status,
            "agent_start": list(self.agent_start),
            "agent_heading": self.agent_heading,
            "goal_sequence": [list(point) for point in self.goal_sequence],
            "hazard_locations": [list(point) for point in self.hazard_locations],
            "vase_locations": [list(point) for point in self.vase_locations],
            "cycle_goal_sequence": self.cycle_goal_sequence,
            "hazard_radius": self.hazard_radius,
            "d_warn": self.d_warn,
            "d_safe": self.d_safe,
            "deadline_steps": self.deadline_steps,
            "straight_segment_minimum_center_distances": list(self.route_clearances()),
        }


def load_fixed_route_scenario(path: Path) -> FixedRouteScenario:
    """Load and validate one controlled fixed-route configuration."""

    with path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle)
    if not isinstance(loaded, Mapping):
        raise ValueError("fixed-route configuration must be a mapping")
    layout = loaded.get("layout")
    rule = loaded.get("stl_rule_candidate")
    if not isinstance(layout, Mapping) or not isinstance(rule, Mapping):
        raise ValueError("fixed-route configuration requires layout and stl_rule_candidate")

    scenario = FixedRouteScenario(
        scenario_id=str(loaded.get("scenario_id", "")),
        environment_id=str(loaded.get("environment_id", "")),
        status=str(loaded.get("status", "")),
        agent_start=_point(layout.get("agent_start"), "layout.agent_start"),
        agent_heading=float(layout.get("agent_heading")),
        goal_sequence=_points(layout.get("goal_sequence"), "layout.goal_sequence"),
        hazard_locations=_points(layout.get("hazard_locations"), "layout.hazard_locations"),
        vase_locations=_points(layout.get("vase_locations"), "layout.vase_locations"),
        cycle_goal_sequence=bool(layout.get("cycle_goal_sequence")),
        hazard_radius=float(layout.get("hazard_radius")),
        d_warn=float(rule.get("d_warn")),
        d_safe=float(rule.get("d_safe")),
        deadline_steps=rule.get("deadline_steps"),
    )
    if not scenario.scenario_id:
        raise ValueError("scenario_id must not be empty")
    if scenario.environment_id != "SafetyPointGoal1-v0":
        raise ValueError("fixed-route v1 requires SafetyPointGoal1-v0")
    if len(scenario.hazard_locations) != 8:
        raise ValueError("SafetyPointGoal1-v0 requires exactly eight hazard locations")
    if len(scenario.vase_locations) != 1:
        raise ValueError("SafetyPointGoal1-v0 requires exactly one vase location")
    if not math.isfinite(scenario.agent_heading):
        raise ValueError("agent_heading must be finite")
    if not 0.0 < scenario.hazard_radius < scenario.d_warn < scenario.d_safe:
        raise ValueError("thresholds must satisfy 0 < hazard_radius < d_warn < d_safe")
    if scenario.deadline_steps is not None:
        raise ValueError("fixed-route v1 deadline must remain null until recalibration")
    if any(abs(value) > 1.5 for point in _all_points(scenario) for value in point):
        raise ValueError("all controlled locations must lie within the Level-1 placement extents")
    minimum_endpoint_clearance = min(
        math.dist(point, hazard)
        for point in (scenario.agent_start, *scenario.goal_sequence)
        for hazard in scenario.hazard_locations
    )
    if minimum_endpoint_clearance < scenario.d_safe:
        raise ValueError("every start/goal endpoint must begin outside d_safe")
    _validate_benchmark_keepouts(scenario)
    return scenario


def _all_points(scenario: FixedRouteScenario) -> Iterable[Point]:
    return (
        scenario.agent_start,
        *scenario.goal_sequence,
        *scenario.hazard_locations,
        *scenario.vase_locations,
    )


def _minimum_cross_distance(first: Sequence[Point], second: Sequence[Point]) -> float:
    return min(math.dist(left, right) for left in first for right in second)


def _minimum_pair_distance(points: Sequence[Point]) -> float:
    return min(
        math.dist(points[left], points[right])
        for left in range(len(points))
        for right in range(left + 1, len(points))
    )


def _validate_benchmark_keepouts(scenario: FixedRouteScenario) -> None:
    """Enforce the pinned Safety-Gymnasium 1.0.0 placement keepouts."""

    starts = (scenario.agent_start,)
    goals = scenario.goal_sequence
    hazards = scenario.hazard_locations
    vases = scenario.vase_locations
    route_points = (scenario.agent_start, *goals, goals[0])
    consecutive_goal_distance = min(
        math.dist(start, end) for start, end in zip(route_points, route_points[1:])
    )
    checks = (
        ("agent-current-goal", consecutive_goal_distance, 0.40 + 0.40),
        ("agent-hazard", _minimum_cross_distance(starts, hazards), 0.40 + 0.18),
        ("agent-vase", _minimum_cross_distance(starts, vases), 0.40 + 0.15),
        ("goal-hazard", _minimum_cross_distance(goals, hazards), 0.40 + 0.18),
        ("goal-vase", _minimum_cross_distance(goals, vases), 0.40 + 0.15),
        ("hazard-hazard", _minimum_pair_distance(hazards), 0.18 + 0.18),
        ("hazard-vase", _minimum_cross_distance(hazards, vases), 0.18 + 0.15),
    )
    failures = [
        f"{name} distance {distance:.6g} < keepout sum {required:.6g}"
        for name, distance, required in checks
        if distance < required
    ]
    if failures:
        raise ValueError("invalid fixed layout: " + "; ".join(failures))


def install_fixed_route(task: Any, scenario: FixedRouteScenario) -> None:
    """Install deterministic layout and ordered goal updates on one GoalLevel1 task.

    This must run after task construction and before its first reset.  It uses
    the public object-location fields for the initial layout, then replaces the
    task's random goal resampling with an ordered goal sequence.
    """

    required = ("agent", "goal", "hazards", "vases", "placements_conf")
    missing = [name for name in required if not hasattr(task, name)]
    if missing:
        raise TypeError(f"task is missing fixed-route fields: {', '.join(missing)}")

    task.agent.locations = [scenario.agent_start]
    task.agent.rot = scenario.agent_heading
    task.goal.locations = [scenario.goal_sequence[0]]
    task.hazards.locations = list(scenario.hazard_locations)
    task.vases.locations = list(scenario.vase_locations)
    task.placements_conf.placements = None
    task.mechanism_conf.continue_goal = bool(scenario.cycle_goal_sequence)

    original_reset = task.reset
    state = {"goal_index": 0, "initial_goal_pending": True}

    def fixed_reset(_task: Any) -> Any:
        state["goal_index"] = 0
        state["initial_goal_pending"] = True
        return original_reset()

    def fixed_update_world(_task: Any) -> None:
        if state["initial_goal_pending"]:
            state["initial_goal_pending"] = False
        else:
            state["goal_index"] = (state["goal_index"] + 1) % len(scenario.goal_sequence)
        position = np.asarray(scenario.goal_sequence[state["goal_index"]], dtype=np.float64)
        _task.world_info.layout["goal"] = position.copy()
        world_config = getattr(_task.world_info, "world_config_dict", None)
        if isinstance(world_config, Mapping):
            world_config["geoms"]["goal"]["pos"][:2] = position
        _task._set_goal(position)  # pylint: disable=protected-access
        if hasattr(_task, "model") and hasattr(_task, "data"):
            import mujoco  # pylint: disable=import-outside-toplevel

            mujoco.mj_forward(_task.model, _task.data)
        _task.last_dist_goal = _task.dist_goal()
        _task.fixed_route_goal_index = int(state["goal_index"])

    task.reset = MethodType(fixed_reset, task)
    task.update_world = MethodType(fixed_update_world, task)
    task.fixed_route_scenario_id = scenario.scenario_id
    task.fixed_route_goal_index = 0


def install_on_omnisafe_base_env(base_env: Any, scenario: FixedRouteScenario) -> int:
    """Install the route on every synchronous Safety-Gymnasium subenvironment."""

    wrapped = base_env._env  # pylint: disable=protected-access
    if hasattr(wrapped, "envs"):
        environments = list(wrapped.envs)
    else:
        environments = [wrapped]
    for environment in environments:
        install_fixed_route(environment.unwrapped.task, scenario)
    return len(environments)


__all__ = [
    "FixedRouteScenario",
    "install_fixed_route",
    "install_on_omnisafe_base_env",
    "load_fixed_route_scenario",
]
