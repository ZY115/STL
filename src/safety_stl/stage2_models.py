"""Stage II-A MiniLM current-observation and causal-history direct models."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple

import torch
from torch import nn


def mean_pool(last_hidden_state: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
    """Attention-mask-aware mean pooling for the frozen MiniLM interface."""

    mask = attention_mask.unsqueeze(-1).to(last_hidden_state.dtype)
    denominator = mask.sum(dim=1).clamp_min(1.0)
    return (last_hidden_state * mask).sum(dim=1) / denominator


class MiniLMTextEncoder(nn.Module):
    """Fine-tunable Hugging Face encoder with deterministic mean pooling."""

    def __init__(self, model_name: str) -> None:
        super().__init__()
        from transformers import AutoModel

        self.model_name = model_name
        self.encoder = AutoModel.from_pretrained(model_name)
        self.output_size = int(self.encoder.config.hidden_size)

    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
        output = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
        return mean_pool(output.last_hidden_state, attention_mask)


class CurrentObservationDirectModel(nn.Module):
    """Language plus current public distance structural ablation."""

    def __init__(self, model_name: str, hidden_size: int = 128) -> None:
        super().__init__()
        self.text = MiniLMTextEncoder(model_name)
        self.classifier = nn.Sequential(
            nn.Linear(self.text.output_size + 1, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, 1),
        )

    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
        distances: torch.Tensor,
    ) -> torch.Tensor:
        language = self.text(input_ids, attention_mask)
        if distances.ndim != 2:
            raise ValueError("current-observation distances must have shape (batch, steps)")
        expanded = language.unsqueeze(1).expand(-1, distances.shape[1], -1)
        features = torch.cat([expanded, distances.unsqueeze(-1)], dim=-1)
        return self.classifier(features).squeeze(-1)


class HistoryAwareDirectModel(nn.Module):
    """Fine-tuned MiniLM language embedding plus causal GRU-128 history."""

    def __init__(self, model_name: str, hidden_size: int = 128) -> None:
        super().__init__()
        self.text = MiniLMTextEncoder(model_name)
        self.gru = nn.GRU(
            input_size=self.text.output_size + 1,
            hidden_size=hidden_size,
            num_layers=1,
            batch_first=True,
        )
        self.fusion_head = nn.Sequential(
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, 3),
        )

    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
        distances: torch.Tensor,
    ) -> Dict[str, torch.Tensor]:
        language = self.text(input_ids, attention_mask)
        if distances.ndim != 2:
            raise ValueError("history distances must have shape (batch, steps)")
        expanded = language.unsqueeze(1).expand(-1, distances.shape[1], -1)
        sequence = torch.cat([expanded, distances.unsqueeze(-1)], dim=-1)
        causal_hidden, _ = self.gru(sequence)
        outputs = self.fusion_head(causal_hidden)
        return {
            "violation_logits": outputs[..., 0],
            "active_logits": outputs[..., 1],
            "remaining_prediction": torch.sigmoid(outputs[..., 2]),
        }


def direct_multitask_loss(
    outputs: Mapping[str, torch.Tensor],
    *,
    costs: torch.Tensor,
    active: torch.Tensor,
    remaining: torch.Tensor,
    positive_weight: torch.Tensor,
    active_weight: float = 0.5,
    remaining_weight: float = 0.2,
) -> Tuple[torch.Tensor, Dict[str, float]]:
    """Frozen history-direct objective with train-derived event class weight."""

    violation_loss = nn.functional.binary_cross_entropy_with_logits(
        outputs["violation_logits"],
        costs,
        pos_weight=positive_weight,
    )
    active_loss = nn.functional.binary_cross_entropy_with_logits(
        outputs["active_logits"],
        active,
    )
    active_mask = active > 0.5
    remaining_loss = (
        nn.functional.mse_loss(outputs["remaining_prediction"][active_mask], remaining[active_mask])
        if active_mask.any()
        else outputs["remaining_prediction"].sum() * 0.0
    )
    total = violation_loss + active_weight * active_loss + remaining_weight * remaining_loss
    return total, {
        "violation_loss": float(violation_loss.detach().cpu()),
        "active_loss": float(active_loss.detach().cpu()),
        "remaining_loss": float(remaining_loss.detach().cpu()),
    }


__all__ = [
    "CurrentObservationDirectModel",
    "HistoryAwareDirectModel",
    "MiniLMTextEncoder",
    "direct_multitask_loss",
    "mean_pool",
]
