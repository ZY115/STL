"""Executable regression checks for the project-owned bootstrap repair."""

from __future__ import annotations

import math
import unittest
from types import SimpleNamespace
from typing import Any, Dict

import torch

from safety_stl.omnisafe_adapter import SettledCostOnPolicyAdapter, terminal_cost_is_settled


class _ProbeAdapter(SettledCostOnPolicyAdapter):
    def reset(self, seed=None, options=None):
        del seed, options
        return torch.zeros((1, 3), dtype=torch.float32), {}

    def step(self, action: torch.Tensor):
        del action
        return (
            torch.zeros((1, 3), dtype=torch.float32),
            torch.zeros(1),
            torch.ones(1),
            torch.tensor([False]),
            torch.tensor([True]),
            {
                "final_observation": torch.tensor([[9.0, 0.0, 0.0]]),
                "stl_terminal_unresolved": torch.tensor([True]),
            },
        )

    def _log_value(self, reward: torch.Tensor, cost: torch.Tensor, info: Dict[str, Any]) -> None:
        del reward, cost, info

    def _log_metrics(self, logger: Any, idx: int) -> None:
        del logger, idx


class _ProbeAgent:
    def step(self, observation: torch.Tensor):
        marker = float(observation.reshape(-1)[0])
        return (
            torch.zeros((1, 2)),
            torch.tensor([3.0 if math.isclose(marker, 9.0) else 0.25]),
            torch.tensor([7.0 if math.isclose(marker, 9.0) else 0.5]),
            torch.tensor([0.0]),
        )


class _ProbeBuffer:
    def __init__(self) -> None:
        self.last_value_r = None
        self.last_value_c = None

    def store(self, **data: torch.Tensor) -> None:
        del data

    def finish_path(self, last_value_r: torch.Tensor, last_value_c: torch.Tensor, idx: int) -> None:
        if idx != 0:
            raise AssertionError("probe has one vector slot")
        self.last_value_r = float(last_value_r.reshape(-1)[0])
        self.last_value_c = float(last_value_c.reshape(-1)[0])


class _ProbeLogger:
    current_epoch = 0

    def store(self, data: Dict[str, Any]) -> None:
        del data

    def log(self, message: str) -> None:
        del message


class SettledCostAdapterTests(unittest.TestCase):
    def test_terminal_settlement_detection_is_vector_safe(self) -> None:
        info = {"stl_terminal_unresolved": torch.tensor([False, True])}
        self.assertFalse(terminal_cost_is_settled(info, 0, True))
        self.assertTrue(terminal_cost_is_settled(info, 1, True))
        self.assertFalse(terminal_cost_is_settled(info, 1, False))

    def test_reward_bootstraps_but_settled_cost_does_not(self) -> None:
        adapter = object.__new__(_ProbeAdapter)
        adapter._env = SimpleNamespace(num_envs=1)  # pylint: disable=protected-access
        adapter._cfgs = SimpleNamespace(  # pylint: disable=protected-access
            algo_cfgs=SimpleNamespace(use_cost=True),
        )
        buffer = _ProbeBuffer()
        adapter.rollout(1, _ProbeAgent(), buffer, _ProbeLogger())
        self.assertEqual(buffer.last_value_r, 3.0)
        self.assertEqual(buffer.last_value_c, 0.0)


if __name__ == "__main__":
    unittest.main()
