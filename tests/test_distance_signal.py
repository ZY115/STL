"""Tests for the public hazard-distance contract."""

from __future__ import annotations

import unittest

import numpy as np
import safety_gymnasium

from safety_stl.signals import (
    distance_from_hazards_lidar,
    distance_from_observation,
    simulator_nearest_hazard_center_distance,
)


class DistanceSignalTests(unittest.TestCase):
    def test_formula(self) -> None:
        self.assertEqual(distance_from_hazards_lidar([0.0] * 16), 3.0)
        self.assertEqual(distance_from_hazards_lidar([0.0, 1.0]), 0.0)
        self.assertAlmostEqual(distance_from_hazards_lidar([0.1, 0.25, 0.2]), 2.25)

    def test_invalid_lidar_inputs(self) -> None:
        for value in ([], [[0.2]], [float("nan")], [-0.1], [1.1]):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    distance_from_hazards_lidar(value)

    def test_flattened_public_observation_matches_privileged_diagnostic(self) -> None:
        environment = safety_gymnasium.make("SafetyPointGoal1-v0")
        try:
            observation, _ = environment.reset(seed=314159)
            task = environment.unwrapped.task
            schema = task.obs_info.obs_space_dict
            public = distance_from_observation(observation, schema)
            privileged = simulator_nearest_hazard_center_distance(task)
            self.assertLessEqual(abs(public - min(3.0, privileged)), 1e-12)

            action = np.zeros(environment.action_space.shape, dtype=np.float64)
            observation, reward, native_cost, terminated, truncated, _ = environment.step(action)
            self.assertIsInstance(float(reward), float)
            self.assertIsInstance(float(native_cost), float)
            self.assertFalse(terminated)
            self.assertFalse(truncated)
            public = distance_from_observation(observation, schema)
            privileged = simulator_nearest_hazard_center_distance(task)
            self.assertLessEqual(abs(public - min(3.0, privileged)), 1e-12)
        finally:
            environment.close()


if __name__ == "__main__":
    unittest.main()
