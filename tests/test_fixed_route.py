"""Tests for deterministic fixed-route configuration and task installation."""

from __future__ import annotations

import math
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import yaml

from safety_stl.fixed_route import install_fixed_route, load_fixed_route_scenario


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPOSITORY_ROOT / "configs" / "fixed_route_v1" / "scenario.yaml"
QUICK_TURN_PATH = REPOSITORY_ROOT / "configs" / "fixed_route_v1" / "quick_turn.yaml"


class FakeTask:
    def __init__(self) -> None:
        self.agent = SimpleNamespace(locations=[], rot=None)
        self.goal = SimpleNamespace(locations=[])
        self.hazards = SimpleNamespace(locations=[])
        self.vases = SimpleNamespace(locations=[])
        self.placements_conf = SimpleNamespace(placements={"old": "layout"})
        self.mechanism_conf = SimpleNamespace(continue_goal=False)
        self.world_info = SimpleNamespace(
            layout={},
            world_config_dict={"geoms": {"goal": {"pos": np.zeros(3)}}},
        )
        self.goal_position = np.zeros(2)
        self.last_dist_goal = None
        self.reset_calls = 0

    def reset(self) -> None:
        self.reset_calls += 1

    def _set_goal(self, position: np.ndarray) -> None:
        self.goal_position = position.copy()

    def dist_goal(self) -> float:
        return float(np.linalg.norm(self.goal_position))


class FixedRouteTests(unittest.TestCase):
    def test_config_has_requested_thresholds_and_challenging_segments(self) -> None:
        scenario = load_fixed_route_scenario(CONFIG_PATH)
        self.assertEqual(scenario.environment_id, "SafetyPointGoal1-v0")
        self.assertEqual(scenario.d_warn, 0.25)
        self.assertEqual(scenario.d_safe, 0.28)
        self.assertIsNone(scenario.deadline_steps)
        self.assertEqual(len(scenario.goal_sequence), 4)
        self.assertEqual(len(scenario.hazard_locations), 8)
        clearances = scenario.route_clearances()
        self.assertTrue(any(value < scenario.d_warn for value in clearances))
        self.assertTrue(any(value >= scenario.d_warn for value in clearances))

    def test_install_fixes_layout_and_cycles_goals(self) -> None:
        scenario = load_fixed_route_scenario(CONFIG_PATH)
        task = FakeTask()
        install_fixed_route(task, scenario)

        self.assertEqual(task.agent.locations, [scenario.agent_start])
        self.assertTrue(math.isclose(task.agent.rot, scenario.agent_heading))
        self.assertEqual(task.hazards.locations, list(scenario.hazard_locations))
        self.assertIsNone(task.placements_conf.placements)

        task.reset()
        task.update_world()
        np.testing.assert_allclose(task.goal_position, scenario.goal_sequence[0])
        task.update_world()
        np.testing.assert_allclose(task.goal_position, scenario.goal_sequence[1])
        task.reset()
        task.update_world()
        np.testing.assert_allclose(task.goal_position, scenario.goal_sequence[0])

    def test_quick_turn_budget_and_outputs_are_bounded(self) -> None:
        protocol = yaml.safe_load(QUICK_TURN_PATH.read_text(encoding="utf-8"))
        training = protocol["training"]
        self.assertEqual(protocol["protocol_id"], "fixed_route_v1_quick_turn")
        self.assertEqual(training["target_transitions_per_condition"], 150_000)
        self.assertEqual(training["minimum_transitions_per_condition"], 50_000)
        self.assertEqual(training["aggregate_training_wall_clock_limit_minutes"], 30)
        self.assertEqual(
            training["condition_order"],
            ["task_only", "native_safety", "stl_dense_safety"],
        )
        self.assertTrue(training["transitions_must_match_across_conditions"])
        self.assertEqual(protocol["evaluation"]["deterministic_trajectory_episodes_per_condition"], 1)
        self.assertEqual(
            protocol["required_outputs"]["trajectory_figure"],
            "fixed_route_quick_turn_trajectories.png",
        )


if __name__ == "__main__":
    unittest.main()
