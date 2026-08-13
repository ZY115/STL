"""Network-independent unit checks for Stage II-A model helpers."""

from __future__ import annotations

import unittest

import torch

from safety_stl.stage2_models import direct_multitask_loss, mean_pool
from safety_stl.stage2_training import (
    FORMAL_JSON_TOKENS,
    FORMAL_SIGNAL_REGISTRY,
    formal_source_text,
)


class Stage2ModelHelperTests(unittest.TestCase):
    def test_formal_input_always_includes_typed_public_registry(self) -> None:
        source = formal_source_text("Stay safe.")
        self.assertTrue(source.startswith(FORMAL_SIGNAL_REGISTRY))
        self.assertIn("nearest_hazard_center_distance_public", source)
        self.assertTrue(source.endswith("Stay safe."))

    def test_json_structure_tokens_are_frozen_as_regular_tokens(self) -> None:
        self.assertEqual(FORMAL_JSON_TOKENS, ("{", "}", ",", "[", "]"))

    def test_mean_pool_ignores_padding(self) -> None:
        hidden = torch.tensor([[[1.0, 2.0], [3.0, 4.0], [100.0, 100.0]]])
        mask = torch.tensor([[1, 1, 0]])
        pooled = mean_pool(hidden, mask)
        torch.testing.assert_close(pooled, torch.tensor([[2.0, 3.0]]))

    def test_multitask_loss_is_finite_and_backpropagates(self) -> None:
        outputs = {
            "violation_logits": torch.zeros((2, 3), requires_grad=True),
            "active_logits": torch.zeros((2, 3), requires_grad=True),
            "remaining_prediction": torch.full((2, 3), 0.5, requires_grad=True),
        }
        total, components = direct_multitask_loss(
            outputs,
            costs=torch.tensor([[0.0, 1.0, 0.0], [0.0, 0.0, 0.0]]),
            active=torch.tensor([[0.0, 1.0, 1.0], [0.0, 0.0, 0.0]]),
            remaining=torch.tensor([[0.0, 1.0, 0.5], [0.0, 0.0, 0.0]]),
            positive_weight=torch.tensor(5.0),
        )
        self.assertTrue(torch.isfinite(total))
        self.assertTrue(all(value >= 0.0 for value in components.values()))
        total.backward()
        self.assertIsNotNone(outputs["violation_logits"].grad)


if __name__ == "__main__":
    unittest.main()
