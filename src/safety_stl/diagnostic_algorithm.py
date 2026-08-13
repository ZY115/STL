"""Project-owned PPO-Lagrangian diagnostic runtime required by D38."""

from __future__ import annotations

import math
from typing import Iterable

import numpy as np
import torch

from omnisafe.algorithms.on_policy.base.ppo import PPO
from omnisafe.algorithms.on_policy.naive_lagrange.ppo_lag import PPOLag
from omnisafe.utils import distributed

from safety_stl.omnisafe_adapter import SettledCostOnPolicyAdapter


ACTOR_LR_FLOOR = 3.0e-5


def floor_linear_lr_factor(step: int, total_steps: int, initial_lr: float) -> float:
    """Linear-decay multiplier with D38's nonzero actor learning-rate floor."""

    if total_steps <= 0 or initial_lr <= 0 or not 0 < ACTOR_LR_FLOOR <= initial_lr:
        raise ValueError("invalid learning-rate schedule inputs")
    return max(ACTOR_LR_FLOOR / initial_lr, 1.0 - int(step) / int(total_steps))


def gradient_l2_norm(gradients: Iterable[torch.Tensor]) -> torch.Tensor:
    """Compute a finite global L2 norm without mutating parameter gradients."""

    terms = [torch.sum(gradient.detach() ** 2) for gradient in gradients if gradient is not None]
    if not terms:
        return torch.tensor(0.0)
    return torch.sqrt(torch.stack(terms).sum())


class DiagnosticPPOLag(PPOLag):
    """PPOLag with settled cost bootstrap, LR floor, and mechanism logs."""

    def _init_env(self) -> None:
        self._env = SettledCostOnPolicyAdapter(
            self._env_id,
            self._cfgs.train_cfgs.vector_env_nums,
            self._seed,
            self._cfgs,
        )
        divisor = distributed.world_size() * self._cfgs.train_cfgs.vector_env_nums
        if self._cfgs.algo_cfgs.steps_per_epoch % divisor:
            raise ValueError("steps_per_epoch must divide across distributed vector environments")
        self._steps_per_epoch = self._cfgs.algo_cfgs.steps_per_epoch // divisor

    def _init_model(self) -> None:
        super()._init_model()
        initial_lr = float(self._cfgs.model_cfgs.actor.lr)
        epochs = int(self._cfgs.train_cfgs.epochs)
        self._actor_critic.actor_scheduler = torch.optim.lr_scheduler.LambdaLR(
            self._actor_critic.actor_optimizer,
            lr_lambda=lambda step: floor_linear_lr_factor(step, epochs, initial_lr),
        )

    def _init_log(self) -> None:
        super()._init_log()
        for key in (
            "Diagnostics/PositiveCostStepFraction",
            "Diagnostics/CostValueRMSE",
            "Diagnostics/CostValueMeanPrediction",
            "Diagnostics/CostValueMeanTarget",
            "Diagnostics/RewardAdvStdRaw",
            "Diagnostics/CostAdvStdActorScale",
            "Diagnostics/ActorRewardGradientNorm",
            "Diagnostics/ActorCostGradientNorm",
        ):
            self._logger.register_key(key)

    def _update(self) -> None:
        episode_cost = self._logger.get_stats("Metrics/EpCost")[0]
        if np.isnan(episode_cost):
            raise FloatingPointError("episode cost for Lagrange update is NaN")
        self._lagrange.update_lagrange_multiplier(episode_cost)

        def field(name: str) -> torch.Tensor:
            return torch.cat([buffer.data[name] for buffer in self._buf.buffers], dim=0)

        cost = field("cost")
        value_c = field("value_c")
        target_c = field("target_value_c")
        reward_adv = field("adv_r")
        cost_adv = field("adv_c")
        diagnostics = {
            "Diagnostics/PositiveCostStepFraction": (cost > 0).float().mean().item(),
            "Diagnostics/CostValueRMSE": torch.sqrt(torch.mean((value_c - target_c) ** 2)).item(),
            "Diagnostics/CostValueMeanPrediction": value_c.mean().item(),
            "Diagnostics/CostValueMeanTarget": target_c.mean().item(),
            "Diagnostics/RewardAdvStdRaw": reward_adv.std(unbiased=False).item(),
            # OmniSafe mean-centers but does not divide cost advantage by its
            # standard deviation; subtracting a mean leaves this scale intact.
            "Diagnostics/CostAdvStdActorScale": cost_adv.std(unbiased=False).item(),
        }
        if not all(math.isfinite(value) for value in diagnostics.values()):
            raise FloatingPointError(f"non-finite PPO diagnostic: {diagnostics}")
        self._logger.store(diagnostics)

        PPO._update(self)
        self._logger.store({"Metrics/LagrangeMultiplier": self._lagrange.lagrangian_multiplier})

    def _component_policy_loss(
        self,
        obs: torch.Tensor,
        act: torch.Tensor,
        logp: torch.Tensor,
        advantage: torch.Tensor,
    ) -> torch.Tensor:
        self._actor_critic.actor(obs)
        current_logp = self._actor_critic.actor.log_prob(act)
        ratio = torch.exp(current_logp - logp)
        clipped = torch.clamp(
            ratio,
            1 - self._cfgs.algo_cfgs.clip,
            1 + self._cfgs.algo_cfgs.clip,
        )
        return -torch.min(ratio * advantage, clipped * advantage).mean()

    def _update_actor(
        self,
        obs: torch.Tensor,
        act: torch.Tensor,
        logp: torch.Tensor,
        adv_r: torch.Tensor,
        adv_c: torch.Tensor,
    ) -> None:
        parameters = [parameter for parameter in self._actor_critic.actor.parameters() if parameter.requires_grad]
        reward_loss = self._component_policy_loss(obs, act, logp, adv_r)
        reward_gradients = torch.autograd.grad(
            reward_loss,
            parameters,
            retain_graph=False,
            allow_unused=True,
        )
        cost_loss = self._component_policy_loss(obs, act, logp, adv_c)
        cost_gradients = torch.autograd.grad(
            cost_loss,
            parameters,
            retain_graph=False,
            allow_unused=True,
        )
        self._logger.store(
            {
                "Diagnostics/ActorRewardGradientNorm": gradient_l2_norm(reward_gradients).item(),
                "Diagnostics/ActorCostGradientNorm": gradient_l2_norm(cost_gradients).item(),
            },
        )

        combined_advantage = self._compute_adv_surrogate(adv_r, adv_c)
        loss = self._loss_pi(obs, act, logp, combined_advantage)
        self._actor_critic.actor_optimizer.zero_grad()
        loss.backward()
        if self._cfgs.algo_cfgs.use_max_grad_norm:
            torch.nn.utils.clip_grad_norm_(
                self._actor_critic.actor.parameters(),
                self._cfgs.algo_cfgs.max_grad_norm,
            )
        distributed.avg_grads(self._actor_critic.actor)
        self._actor_critic.actor_optimizer.step()


__all__ = [
    "ACTOR_LR_FLOOR",
    "DiagnosticPPOLag",
    "floor_linear_lr_factor",
    "gradient_l2_norm",
]
