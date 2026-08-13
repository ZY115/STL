"""Tests for Stage I cost routing and OmniSafe environment integration."""

from __future__ import annotations

import unittest
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import torch
from gymnasium import spaces
from gymnasium.spaces.utils import flatten

from omnisafe.envs.core import CMDP, make, support_envs
from omnisafe.envs.safety_gymnasium_env import SafetyGymnasiumEnv

from safety_stl.omnisafe_env import (
    CostMode,
    NATIVE_COST_ENV_ID,
    REGISTERED_ENV_IDS,
    STL_COST_ENV_ID,
    Stage1TemporalCostWrapper,
    TASK_ONLY_ENV_ID,
    select_algorithm_cost,
)


D_WARN = 0.30
D_SAFE = 0.50
K = 3


def observation_schema() -> spaces.Dict:
    return spaces.Dict(
        {"hazards_lidar": spaces.Box(0.0, 1.0, shape=(2,), dtype=np.float64)},
    )


def observation_for_distance(distance: float) -> np.ndarray:
    closeness = 1.0 - distance / 3.0
    return flatten(
        observation_schema(),
        {"hazards_lidar": np.asarray([closeness, 0.0], dtype=np.float64)},
    ).astype(np.float32)


class ScriptedCMDP(CMDP):
    """Minimal tensor CMDP with explicit auto-reset transitions for wrapper tests."""

    need_auto_reset_wrapper = False
    need_time_limit_wrapper = False

    def __init__(
        self,
        reset_distances: Sequence[float],
        transitions: Sequence[Dict[str, Any]],
    ) -> None:
        self._num_envs = len(reset_distances)
        self._reset_distances = list(reset_distances)
        self._transitions = list(transitions)
        self._cursor = 0
        self._action_space = spaces.Box(-1.0, 1.0, shape=(2,), dtype=np.float32)
        self._observation_space = spaces.Box(0.0, 1.0, shape=(2,), dtype=np.float32)
        self._metadata = {}

    def _batch(self, rows: Sequence[np.ndarray]) -> torch.Tensor:
        tensor = torch.as_tensor(np.stack(rows), dtype=torch.float32)
        return tensor[0] if self._num_envs == 1 else tensor

    def _value(self, values: Sequence[Any], dtype: torch.dtype) -> torch.Tensor:
        tensor = torch.as_tensor(values, dtype=dtype)
        return tensor[0] if self._num_envs == 1 else tensor

    def reset(
        self,
        seed: Optional[int] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Tuple[torch.Tensor, Dict[str, Any]]:
        del seed, options
        self._cursor = 0
        return self._batch([observation_for_distance(value) for value in self._reset_distances]), {}

    def step(self, action: torch.Tensor) -> Tuple[torch.Tensor, ...]:
        del action
        transition = self._transitions[self._cursor]
        self._cursor += 1
        distances = transition["distances"]
        terminated = transition.get("terminated", [False] * self._num_envs)
        truncated = transition.get("truncated", [False] * self._num_envs)
        reward = transition.get("reward", [0.0] * self._num_envs)
        cost = transition.get("cost", [0.0] * self._num_envs)
        info: Dict[str, Any] = {}
        if any(a or b for a, b in zip(terminated, truncated)):
            final_distances = transition["final_distances"]
            final_rows = [observation_for_distance(value) for value in final_distances]
            final_tensor = self._batch(final_rows)
            info["final_observation"] = final_tensor
            if self._num_envs == 1:
                info["final_info"] = {}
            else:
                info["final_info"] = np.asarray([{} for _ in distances], dtype=object)
                info["_final_observation"] = np.asarray(
                    [a or b for a, b in zip(terminated, truncated)],
                    dtype=bool,
                )
                info["_final_info"] = info["_final_observation"].copy()
        return (
            self._batch([observation_for_distance(value) for value in distances]),
            self._value(reward, torch.float32),
            self._value(cost, torch.float32),
            self._value(terminated, torch.bool),
            self._value(truncated, torch.bool),
            info,
        )

    def set_seed(self, seed: int) -> None:
        self.reset(seed=seed)

    def render(self) -> np.ndarray:
        return np.zeros((2, 2, 3), dtype=np.uint8)

    def close(self) -> None:
        return None


def wrap(base: CMDP, mode: CostMode) -> Stage1TemporalCostWrapper:
    return Stage1TemporalCostWrapper(
        base,
        cost_mode=mode,
        observation_space_dict=observation_schema(),
        lidar_range=3.0,
        d_warn=D_WARN,
        d_safe=D_SAFE,
        deadline_steps=K,
        max_episode_steps=1000,
        device=torch.device("cpu"),
    )


class CapturingLogger:
    def __init__(self) -> None:
        self.records: List[Dict[str, float]] = []

    def store(self, record: Dict[str, float]) -> None:
        self.records.append(record)


class OmniSafeWrapperTests(unittest.TestCase):
    def test_registered_environment_ids_are_available(self) -> None:
        available = support_envs()
        for environment_id in REGISTERED_ENV_IDS:
            self.assertIn(environment_id, available)

    def test_cost_routing_preserves_diagnostics(self) -> None:
        native = torch.tensor([2.0, 0.0])
        stl = torch.tensor([0.0, 1.0])
        dense = torch.tensor([0.25, 1.0])
        torch.testing.assert_close(
            select_algorithm_cost(CostMode.TASK_ONLY, native, stl),
            torch.zeros(2),
        )
        torch.testing.assert_close(select_algorithm_cost(CostMode.NATIVE, native, stl), native)
        torch.testing.assert_close(select_algorithm_cost(CostMode.STL, native, stl), stl)
        torch.testing.assert_close(
            select_algorithm_cost(CostMode.STL_DENSE, native, stl, dense),
            dense,
        )
        torch.testing.assert_close(native, torch.tensor([2.0, 0.0]))
        torch.testing.assert_close(stl, torch.tensor([0.0, 1.0]))

    def test_reset_observation_contains_triggered_temporal_state(self) -> None:
        environment = wrap(ScriptedCMDP([0.29], []), CostMode.STL)
        observation, info = environment.reset()
        self.assertEqual(observation.shape, (5,))
        torch.testing.assert_close(observation[-3:], torch.tensor([1.0, 0.0, 1.0]))
        self.assertTrue(bool(info["stl_warning_trigger"]))
        self.assertEqual(int(info["stl_sample_index"]), 0)

    def test_recovery_clears_active_policy_state(self) -> None:
        base = ScriptedCMDP([0.29], [{"distances": [D_SAFE]}])
        environment = wrap(base, CostMode.STL)
        environment.reset()
        observation, _, cost, _, _, info = environment.step(torch.zeros(2))
        torch.testing.assert_close(observation[-3:], torch.zeros(3))
        self.assertTrue(bool(info["stl_recovery"]))
        self.assertEqual(float(cost), 0.0)

    def test_deadline_violation_cost_is_emitted_once(self) -> None:
        transitions = [{"distances": [0.40]} for _ in range(4)]
        environment = wrap(ScriptedCMDP([0.29], transitions), CostMode.STL)
        environment.reset()
        costs = []
        violations = []
        for _ in transitions:
            _, _, cost, _, _, info = environment.step(torch.zeros(2))
            costs.append(float(cost))
            violations.append(bool(info["stl_deadline_violation"]))
        self.assertEqual(costs, [0.0, 0.0, 1.0, 0.0])
        self.assertEqual(violations, [False, False, True, False])

    def test_terminal_unresolved_uses_final_observation_then_resets_monitor(self) -> None:
        base = ScriptedCMDP(
            [0.29],
            [
                {
                    "distances": [0.80],
                    "final_distances": [0.40],
                    "reward": [1.25],
                    "cost": [2.0],
                    "truncated": [True],
                },
            ],
        )
        environment = wrap(base, CostMode.STL)
        environment.reset()
        observation, reward, selected, _, truncated, info = environment.step(torch.zeros(2))
        self.assertTrue(bool(truncated))
        self.assertEqual(float(reward), 1.25)
        self.assertEqual(float(info["native_cost"]), 2.0)
        self.assertEqual(float(info["stl_cost"]), 1.0)
        self.assertEqual(float(selected), 1.0)
        self.assertTrue(bool(info["stl_terminal_unresolved"]))
        torch.testing.assert_close(observation[-3:], torch.zeros(3))
        torch.testing.assert_close(
            info["final_observation"][-3:],
            torch.tensor([1.0, 0.0, 2.0 / 3.0]),
        )
        self.assertEqual(environment.monitors[0].sample_index, 0)
        self.assertEqual(environment.monitors[0].trigger_count, 0)

    def test_each_mode_returns_same_shape_and_expected_selected_cost(self) -> None:
        expected = {
            CostMode.TASK_ONLY: 0.0,
            CostMode.NATIVE: 2.0,
            CostMode.STL: 1.0,
            CostMode.STL_DENSE: 1.0,
        }
        for mode, expected_cost in expected.items():
            with self.subTest(mode=mode.value):
                base = ScriptedCMDP(
                    [0.29],
                    [
                        {
                            "distances": [0.80],
                            "final_distances": [0.40],
                            "reward": [0.75],
                            "cost": [2.0],
                            "truncated": [True],
                        },
                    ],
                )
                environment = wrap(base, mode)
                reset_observation, _ = environment.reset()
                observation, reward, selected, _, _, info = environment.step(torch.zeros(2))
                self.assertEqual(reset_observation.shape, observation.shape)
                self.assertEqual(observation.dtype, torch.float32)
                self.assertEqual(float(reward), 0.75)
                self.assertEqual(float(info["native_cost"]), 2.0)
                self.assertEqual(float(info["stl_cost"]), 1.0)
                self.assertEqual(float(info["stl_dense_cost"]), 1.0)
                self.assertEqual(float(selected), expected_cost)
                self.assertEqual(float(info["selected_algorithm_cost"]), expected_cost)

    def test_vector_monitors_and_resets_are_independent(self) -> None:
        base = ScriptedCMDP(
            [0.29, 0.80],
            [
                {
                    "distances": [0.90, 0.80],
                    "final_distances": [0.40, 0.80],
                    "truncated": [True, False],
                },
            ],
        )
        environment = wrap(base, CostMode.STL)
        reset_observation, _ = environment.reset()
        torch.testing.assert_close(reset_observation[0, -3:], torch.tensor([1.0, 0.0, 1.0]))
        torch.testing.assert_close(reset_observation[1, -3:], torch.zeros(3))
        observation, _, cost, _, truncated, info = environment.step(torch.zeros((2, 2)))
        torch.testing.assert_close(cost, torch.tensor([1.0, 0.0]))
        torch.testing.assert_close(observation[0, -3:], torch.zeros(3))
        torch.testing.assert_close(observation[1, -3:], torch.zeros(3))
        self.assertEqual([monitor.sample_index for monitor in environment.monitors], [0, 1])
        self.assertEqual([monitor.trigger_count for monitor in environment.monitors], [0, 0])
        torch.testing.assert_close(truncated, torch.tensor([True, False]))
        self.assertEqual(tuple(info["stl_status"]), ("pending", "inactive"))

    def test_episode_log_keeps_all_three_costs_separate(self) -> None:
        base = ScriptedCMDP(
            [0.29],
            [
                {
                    "distances": [0.80],
                    "final_distances": [0.40],
                    "cost": [2.0],
                    "truncated": [True],
                },
            ],
        )
        environment = wrap(base, CostMode.STL)
        environment.reset()
        environment.step(torch.zeros(2))
        logger = CapturingLogger()
        environment.spec_log(logger)
        self.assertEqual(len(logger.records), 1)
        record = logger.records[0]
        self.assertEqual(record["Metrics/NativeCost"], 2.0)
        self.assertEqual(record["Metrics/STLCost"], 1.0)
        self.assertEqual(record["Metrics/SelectedAlgorithmCost"], 1.0)
        self.assertEqual(record["Metrics/STLTriggers"], 1.0)
        self.assertEqual(record["Metrics/STLTerminalUnresolved"], 1.0)

    def test_real_environment_preserves_reward_and_native_cost(self) -> None:
        reference = SafetyGymnasiumEnv(
            "SafetyPointGoal1-v0",
            num_envs=1,
            device=torch.device("cpu"),
        )
        native = make(NATIVE_COST_ENV_ID, num_envs=1, device=torch.device("cpu"))
        task = make(TASK_ONLY_ENV_ID, num_envs=1, device=torch.device("cpu"))
        stl = make(STL_COST_ENV_ID, num_envs=1, device=torch.device("cpu"))
        try:
            environments = [native, task, stl]
            reference_reset = reference.reset(seed=314159)[0]
            resets = [environment.reset(seed=314159)[0] for environment in environments]
            for observation in resets:
                torch.testing.assert_close(observation[:60], reference_reset)
            reference_output = reference.step(torch.zeros(2))
            outputs = [environment.step(torch.zeros(2)) for environment in environments]
            for output in outputs:
                torch.testing.assert_close(output[0][:60], reference_output[0])
                torch.testing.assert_close(output[1], reference_output[1])
                torch.testing.assert_close(output[5]["native_cost"], reference_output[2])
            self.assertEqual([float(output[2]) for output in outputs], [0.0, 0.0, 0.0])
        finally:
            reference.close()
            native.close()
            task.close()
            stl.close()

    def test_omnisafe_make_vector_contract(self) -> None:
        environment = make(
            STL_COST_ENV_ID,
            num_envs=2,
            device=torch.device("cpu"),
            max_episode_steps=2,
        )
        try:
            observation, _ = environment.reset(seed=20260810)
            self.assertEqual(observation.shape, (2, 63))
            output = environment.step(torch.zeros((2, 2)))
            self.assertEqual([tensor.shape for tensor in output[:5]], [(2, 63), (2,), (2,), (2,), (2,)])
            self.assertEqual(output[0].dtype, torch.float32)
            self.assertEqual(output[2].device.type, "cpu")
        finally:
            environment.close()


if __name__ == "__main__":
    unittest.main()
