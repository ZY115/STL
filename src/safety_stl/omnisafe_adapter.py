"""Project-owned OmniSafe rollout adapter for episode-settled STL costs.

OmniSafe 0.5.0 bootstraps both reward and cost values at a time-limit
truncation.  The Stage I monitor, however, emits a terminal-unresolved cost and
settles that obligation on the final sample.  Continuing the cost critic from
the augmented final observation double-counts future monitor cost.  This
adapter preserves OmniSafe's reward bootstrap but forces only the cost
bootstrap to zero for that explicitly settled case.

The installed package is never modified.  Diagnostic runners replace their
algorithm's adapter instance with :class:`SettledCostOnPolicyAdapter`.
"""

from __future__ import annotations

from typing import Any, Dict

import torch
from rich.progress import track

from omnisafe.adapter.onpolicy_adapter import OnPolicyAdapter


def _indexed_boolean(value: Any, index: int) -> bool:
    if isinstance(value, torch.Tensor):
        flattened = value.detach().cpu().reshape(-1)
        if index >= flattened.numel():
            raise IndexError("terminal-settlement flag does not cover vector index")
        return bool(flattened[index].item())
    if isinstance(value, (list, tuple)):
        return bool(value[index])
    if index != 0:
        raise IndexError("scalar terminal-settlement flag only covers index zero")
    return bool(value)


def terminal_cost_is_settled(info: Dict[str, Any], index: int, time_out: Any) -> bool:
    """Return whether a truncated slot emitted terminal-unresolved Gold cost."""

    if not bool(time_out):
        return False
    if "stl_terminal_unresolved" not in info:
        return False
    return _indexed_boolean(info["stl_terminal_unresolved"], index)


class SettledCostOnPolicyAdapter(OnPolicyAdapter):
    """OmniSafe rollout with reward/cost bootstrap separation at settlement."""

    def rollout(  # pylint: disable=too-many-locals
        self,
        steps_per_epoch: int,
        agent: Any,
        buffer: Any,
        logger: Any,
    ) -> None:
        self._reset_log()  # pylint: disable=protected-access

        obs, _ = self.reset()
        for step in track(
            range(steps_per_epoch),
            description=f"Processing rollout for epoch: {logger.current_epoch}...",
        ):
            act, value_r, value_c, logp = agent.step(obs)
            next_obs, reward, cost, terminated, truncated, info = self.step(act)

            self._log_value(reward=reward, cost=cost, info=info)  # pylint: disable=protected-access
            if self._cfgs.algo_cfgs.use_cost:  # pylint: disable=protected-access
                logger.store({"Value/cost": value_c})
            logger.store({"Value/reward": value_r})
            buffer.store(
                obs=obs,
                act=act,
                reward=reward,
                cost=cost,
                value_r=value_r,
                value_c=value_c,
                logp=logp,
            )

            obs = next_obs
            epoch_end = step >= steps_per_epoch - 1
            for index, (done, time_out) in enumerate(zip(terminated, truncated)):
                if not (epoch_end or done or time_out):
                    continue
                last_value_r = torch.zeros(1)
                last_value_c = torch.zeros(1)
                if not done:
                    if epoch_end:
                        logger.log(
                            "Warning: trajectory cut off when rollout by epoch "
                            f"at {self._ep_len[index]} steps.",  # pylint: disable=protected-access
                        )
                        _, last_value_r, last_value_c, _ = agent.step(obs[index])
                    if time_out:
                        _, last_value_r, last_value_c, _ = agent.step(
                            info["final_observation"][index],
                        )
                        if terminal_cost_is_settled(info, index, time_out):
                            last_value_c = torch.zeros_like(last_value_c)
                    last_value_r = last_value_r.unsqueeze(0)
                    last_value_c = last_value_c.unsqueeze(0)

                if done or time_out:
                    self._log_metrics(logger, index)  # pylint: disable=protected-access
                    self._reset_log(index)  # pylint: disable=protected-access
                    self._ep_ret[index] = 0.0  # pylint: disable=protected-access
                    self._ep_cost[index] = 0.0  # pylint: disable=protected-access
                    self._ep_len[index] = 0.0  # pylint: disable=protected-access

                buffer.finish_path(last_value_r, last_value_c, index)


__all__ = ["SettledCostOnPolicyAdapter", "terminal_cost_is_settled"]
