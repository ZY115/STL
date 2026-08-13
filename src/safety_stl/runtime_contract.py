"""Inspect the effective OmniSafe 0.5.0 runtime used by the Stage I pilot.

The frozen YAML records requested settings.  This module records what the
installed on-policy implementation actually does, without patching
``site-packages`` or changing the completed pilot.
"""

from __future__ import annotations

import hashlib
import inspect
import math
import re
from importlib import metadata
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, Mapping

import torch
import yaml
from omnisafe.adapter.onpolicy_adapter import OnPolicyAdapter
from omnisafe.algorithms.on_policy.base.policy_gradient import PolicyGradient
from omnisafe.algorithms.on_policy.naive_lagrange.pdo import PDO
from omnisafe.common.buffer.onpolicy_buffer import OnPolicyBuffer
from omnisafe.common.lagrange import Lagrange
from omnisafe.models.actor_critic.actor_critic import ActorCritic

from safety_stl.monitor import BoundedRecoveryMonitor


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROTOCOL = REPOSITORY_ROOT / "configs" / "stage1_pilot" / "protocol.yaml"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _source_record(obj: Any) -> Dict[str, str]:
    path = Path(inspect.getsourcefile(obj) or "").resolve()
    if not path.is_file():
        raise RuntimeError(f"cannot resolve installed source for {obj!r}")
    return {"path": str(path), "sha256": _sha256(path)}


def _load_protocol(path: Path) -> Mapping[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    if not isinstance(value, Mapping):
        raise ValueError("pilot protocol must be a mapping")
    return value


class _ProbeAdapter(OnPolicyAdapter):
    """Minimal adapter that executes the installed timeout branch once."""

    def reset(self, seed: int | None = None, options: Dict[str, Any] | None = None):
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
        value_c = 7.0 if math.isclose(marker, 9.0) else 0.5
        return (
            torch.zeros((1, 2)),
            torch.tensor([0.25]),
            torch.tensor([value_c]),
            torch.tensor([0.0]),
        )


class _ProbeBuffer:
    def __init__(self) -> None:
        self.last_value_r: float | None = None
        self.last_value_c: float | None = None

    def store(self, **data: torch.Tensor) -> None:
        del data

    def finish_path(
        self,
        last_value_r: torch.Tensor,
        last_value_c: torch.Tensor,
        idx: int,
    ) -> None:
        if idx != 0:
            raise AssertionError("probe has exactly one vector slot")
        self.last_value_r = float(last_value_r.reshape(-1)[0])
        self.last_value_c = float(last_value_c.reshape(-1)[0])


class _ProbeLogger:
    current_epoch = 0

    def store(self, data: Dict[str, Any]) -> None:
        del data

    def log(self, message: str) -> None:
        del message


def probe_timeout_cost_bootstrap() -> Dict[str, Any]:
    """Execute OmniSafe's installed truncation path with a known cost value."""

    adapter = object.__new__(_ProbeAdapter)
    adapter._env = SimpleNamespace(num_envs=1)  # pylint: disable=protected-access
    adapter._cfgs = SimpleNamespace(  # pylint: disable=protected-access
        algo_cfgs=SimpleNamespace(use_cost=True),
    )
    buffer = _ProbeBuffer()
    adapter.rollout(1, _ProbeAgent(), buffer, _ProbeLogger())
    return {
        "terminal_unresolved": True,
        "fake_final_cost_value": 7.0,
        "observed_last_value_r": buffer.last_value_r,
        "observed_last_value_c": buffer.last_value_c,
        "omnisafe_timeout_bootstraps_cost_value": math.isclose(
            float(buffer.last_value_c),
            7.0,
        ),
        "project_episode_settlement_requires_last_value_c": 0.0,
        "semantic_mismatch": not math.isclose(float(buffer.last_value_c), 0.0),
    }


def inspect_runtime_contract(protocol_path: Path = DEFAULT_PROTOCOL) -> Dict[str, Any]:
    """Return declared and effective settings with source/hash evidence."""

    protocol_path = protocol_path.resolve()
    protocol = _load_protocol(protocol_path)
    omnisafe = protocol["omnisafe"]
    algo = omnisafe["algo_cfgs"]
    logger = omnisafe["logger_cfgs"]
    model = omnisafe["model_cfgs"]
    lagrange = omnisafe["lagrange_cfgs_shared"]

    rollout_source = inspect.getsource(OnPolicyAdapter.rollout)
    init_source = inspect.getsource(PolicyGradient._init)
    log_source = inspect.getsource(PolicyGradient._init_log)
    buffer_get_source = inspect.getsource(OnPolicyBuffer.get)
    learn_source = inspect.getsource(PolicyGradient.learn)
    actor_critic_source = inspect.getsource(ActorCritic.__init__)
    pdo_update_source = inspect.getsource(PDO._update)

    window_match = re.search(
        r"register_key\('Metrics/EpCost',\s*window_length=(\d+)\)",
        log_source,
    )
    if window_match is None:
        raise RuntimeError("cannot identify effective Metrics/EpCost window")
    effective_window = int(window_match.group(1))

    timeout_bootstrap_source = all(
        token in rollout_source
        for token in ("if time_out:", "info['final_observation'][idx]", "last_value_c")
    )
    cost_gamma_used = "cost_gamma" in init_source
    shared_gamma_used = "gamma=self._cfgs.algo_cfgs.gamma" in init_source
    cost_adv_mean_only = (
        "data['adv_c'] = data['adv_c'] - cadv_mean" in buffer_get_source
        and "cadv_std" not in buffer_get_source
    )
    reward_adv_zscore = "(data['adv_r'] - adv_mean) / (adv_std + 1e-8)" in buffer_get_source
    epochs = int(omnisafe["train_cfgs"]["total_steps"] / algo["steps_per_epoch"])
    actor_lr = float(model["actor"]["lr"])
    linear_scheduler = all(
        token in actor_critic_source
        for token in ("LinearLR(", "start_factor=1.0", "end_factor=0.0")
    )
    scheduler_steps_after_update = "self._actor_critic.actor_scheduler.step()" in learn_source
    lagrange_reads_epcost = "get_stats('Metrics/EpCost')[0]" in pdo_update_source

    monitor = BoundedRecoveryMonitor(0.45, 0.55, 79)
    monitor.reset(0.44)
    terminal = monitor.step(0.50, truncated=True)
    monitor_settlement = {
        "terminal_unresolved": terminal.stl_terminal_unresolved,
        "stl_cost": terminal.stl_cost,
        "state_after_final_sample": terminal.stl_status,
        "policy_state_after_final_sample": list(monitor.policy_state()),
    }

    contract = {
        "schema_version": 1,
        "scope": "installed-runtime diagnosis; no package patch and no new training",
        "package_versions": {
            "omnisafe": metadata.version("omnisafe"),
            "torch": torch.__version__,
        },
        "protocol": {"path": str(protocol_path), "sha256": _sha256(protocol_path)},
        "source_files": {
            "onpolicy_adapter": _source_record(OnPolicyAdapter),
            "policy_gradient": _source_record(PolicyGradient),
            "onpolicy_buffer": _source_record(OnPolicyBuffer),
            "actor_critic": _source_record(ActorCritic),
            "pdo_lagrange": _source_record(PDO),
            "lagrange": _source_record(Lagrange),
        },
        "episode_cost_window": {
            "declared_logger_window_lens": int(logger["window_lens"]),
            "effective_metrics_epcost_window": effective_window,
            "declaration_matches_runtime": int(logger["window_lens"]) == effective_window,
        },
        "discount": {
            "declared_reward_gamma": float(algo["gamma"]),
            "declared_cost_gamma": float(algo["cost_gamma"]),
            "onpolicy_init_uses_shared_gamma": shared_gamma_used,
            "onpolicy_init_reads_cost_gamma": cost_gamma_used,
            "effective_cost_gamma": float(algo["gamma"]) if shared_gamma_used else None,
            "current_numeric_difference": float(algo["cost_gamma"] - algo["gamma"]),
        },
        "advantage_transform": {
            "declared_reward_standardized": bool(algo["standardized_rew_adv"]),
            "declared_cost_standardized": bool(algo["standardized_cost_adv"]),
            "effective_reward_zscore": reward_adv_zscore,
            "effective_cost_mean_center_only": cost_adv_mean_only,
        },
        "optimization_schedule": {
            "epoch_count": epochs,
            "actor_lr_initial": actor_lr,
            "linear_lr_decay_declared": bool(model["linear_lr_decay"]),
            "linear_scheduler_effective": linear_scheduler,
            "scheduler_steps_after_each_epoch_update": scheduler_steps_after_update,
            "actor_lr_after_first_scheduler_step": actor_lr * (epochs - 1) / epochs,
            "actor_lr_after_final_scheduler_step": 0.0,
            "nonzero_lr_floor": None,
            "lagrangian_multiplier_init": float(lagrange["lagrangian_multiplier_init"]),
            "lambda_lr": float(lagrange["lambda_lr"]),
            "lambda_optimizer": str(lagrange["lambda_optimizer"]),
            "lagrange_update_reads_metrics_epcost": lagrange_reads_epcost,
            "lagrange_effective_episode_window": effective_window,
        },
        "timeout_bootstrap": {
            "installed_source_bootstraps_reward_and_cost_on_timeout": timeout_bootstrap_source,
            "executable_probe": probe_timeout_cost_bootstrap(),
            "monitor_episode_settlement": monitor_settlement,
        },
        "delayed_credit": {
            "deadline_steps": 79,
            "gamma_times_lam_c_power_k": float(
                (float(algo["gamma"]) * float(algo["lam_c"])) ** 79
            ),
            "gamma_power_k": float(float(algo["gamma"]) ** 79),
        },
        "interpretation": {
            "confirmed_runtime_differences": [
                "Metrics/EpCost uses a hard-coded 50-episode window, not declared 100",
                "cost advantage is mean-centered but not divided by its standard deviation",
                "the on-policy buffer receives algo_cfgs.gamma rather than cost_gamma",
                "actor learning rate is linearly scheduled to zero by the final pilot epoch",
                "the Lagrange update reads the same rolling-50 Metrics/EpCost statistic",
            ],
            "confirmed_semantic_risk": (
                "terminal-unresolved is settled with event cost 1, while OmniSafe also "
                "bootstraps a nonzero cost value from the active final state"
            ),
            "causal_effect_on_pilot": "not isolated by this audit",
        },
    }
    return contract


__all__ = ["DEFAULT_PROTOCOL", "inspect_runtime_contract", "probe_timeout_cost_bootstrap"]
