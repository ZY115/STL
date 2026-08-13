"""Network-independent checks for D38 PPO diagnostic mechanics."""

from __future__ import annotations

import unittest

import torch

from safety_stl.diagnostic_algorithm import (
    ACTOR_LR_FLOOR,
    floor_linear_lr_factor,
    gradient_l2_norm,
)


class DiagnosticAlgorithmTests(unittest.TestCase):
    def test_lr_schedule_reaches_but_never_crosses_floor(self) -> None:
        initial = 3.0e-4
        factors = [floor_linear_lr_factor(step, 30, initial) for step in range(31)]
        self.assertEqual(factors[0], 1.0)
        self.assertAlmostEqual(factors[-1] * initial, ACTOR_LR_FLOOR)
        self.assertTrue(all(value * initial >= ACTOR_LR_FLOOR - 1.0e-12 for value in factors))
        self.assertEqual(factors, sorted(factors, reverse=True))

    def test_global_gradient_norm(self) -> None:
        norm = gradient_l2_norm([torch.tensor([3.0, 4.0]), torch.tensor([12.0])])
        self.assertEqual(float(norm), 13.0)


if __name__ == "__main__":
    unittest.main()
