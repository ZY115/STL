"""OmniSafe environment integration for the fixed Stage I STL rule.

The four registered environment IDs expose exactly the same augmented policy
observation.  They differ only in the scalar cost returned to OmniSafe:

* task-only: zero cost;
* native-cost: Safety-Gymnasium's native hazard cost;
* STL-cost: the bounded-recovery monitor's sparse binary event cost.
* STL-dense-cost: D38's causal learner surrogate, logged separately from Gold.

Safety-Gymnasium auto-resets vector environments.  On a terminal transition,
this wrapper therefore evaluates ``info['final_observation']`` first, augments
that final observation for value bootstrapping, and only then resets the
corresponding monitor from the new observation returned by the base env.
"""

from __future__ import annotations

from collections import deque
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any, ClassVar, Deque, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import safety_gymnasium
import torch
import yaml
from gymnasium import spaces
from gymnasium.spaces import Dict as DictSpace

from omnisafe.envs.core import CMDP, env_register
from omnisafe.envs.safety_gymnasium_env import SafetyGymnasiumEnv

from safety_stl.fixed_route import (
    FixedRouteScenario,
    install_on_omnisafe_base_env,
    load_fixed_route_scenario,
)
from safety_stl.monitor import BoundedRecoveryMonitor, MonitorOutput
from safety_stl.learner_cost import causal_dense_surrogate
from safety_stl.signals import distance_from_observation


BASE_ENVIRONMENT_ID = "SafetyPointGoal1-v0"
TASK_ONLY_ENV_ID = "Stage1SafetyPointGoal1TaskOnly-v0"
NATIVE_COST_ENV_ID = "Stage1SafetyPointGoal1NativeCost-v0"
STL_COST_ENV_ID = "Stage1SafetyPointGoal1STLCost-v0"
STL_DENSE_COST_ENV_ID = "Stage2SafetyPointGoal1STLDenseCost-v0"
REGISTERED_ENV_IDS = (
    TASK_ONLY_ENV_ID,
    NATIVE_COST_ENV_ID,
    STL_COST_ENV_ID,
    STL_DENSE_COST_ENV_ID,
)
DEFAULT_RULE_CONFIG = Path(__file__).resolve().parents[2] / "configs" / "stage1_rule.yaml"

TEMPORAL_OBSERVATION_FIELDS = (
    "active_obligation",
    "overdue_indicator",
    "normalized_remaining_deadline",
)

ENV_SPEC_KEYS = (
    "Metrics/NativeCost",
    "Metrics/STLCost",
    "Metrics/STLDenseCost",
    "Metrics/SelectedAlgorithmCost",
    "Metrics/STLTriggers",
    "Metrics/STLRecoveries",
    "Metrics/STLLateRecoveries",
    "Metrics/STLDeadlineViolations",
    "Metrics/STLTerminalUnresolved",
    "Metrics/GoalEvents",
)


class CostMode(str, Enum):
    """Cost routed to the constrained learner."""

    TASK_ONLY = "task_only"
    NATIVE = "native_cost"
    STL = "stl_cost"
    STL_DENSE = "stl_dense_cost"


ENV_ID_TO_COST_MODE = {
    TASK_ONLY_ENV_ID: CostMode.TASK_ONLY,
    NATIVE_COST_ENV_ID: CostMode.NATIVE,
    STL_COST_ENV_ID: CostMode.STL,
    STL_DENSE_COST_ENV_ID: CostMode.STL_DENSE,
}


def select_algorithm_cost(
    mode: CostMode,
    native_cost: torch.Tensor,
    stl_cost: torch.Tensor,
    stl_dense_cost: Optional[torch.Tensor] = None,
) -> torch.Tensor:
    """Return the learner cost without modifying either diagnostic cost."""

    if native_cost.shape != stl_cost.shape:
        raise ValueError("native_cost and stl_cost must have the same shape")
    if mode is CostMode.TASK_ONLY:
        return torch.zeros_like(native_cost)
    if mode is CostMode.NATIVE:
        return native_cost.clone()
    if mode is CostMode.STL:
        return stl_cost.clone()
    if mode is CostMode.STL_DENSE:
        if stl_dense_cost is None or stl_dense_cost.shape != stl_cost.shape:
            raise ValueError("STL dense mode requires a same-shaped dense cost tensor")
        return stl_dense_cost.clone()
    raise ValueError(f"unsupported cost mode: {mode!r}")


def _load_rule_config(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, Mapping):
        raise ValueError("rule configuration must be a mapping")
    required = {"environment_id", "lidar_range", "d_warn", "d_safe", "deadline_steps"}
    missing = sorted(required - set(config))
    if missing:
        raise ValueError(f"rule configuration is missing: {', '.join(missing)}")
    if config["environment_id"] != BASE_ENVIRONMENT_ID:
        raise ValueError(
            f"Stage I wrapper requires {BASE_ENVIRONMENT_ID}, got {config['environment_id']!r}",
        )
    required_semantics = {
        "distance_source": "hazards_lidar",
        "warning_comparison": "lt",
        "safe_comparison": "ge",
        "trigger_mode": "hysteretic_warning_episode",
        "deadline_inclusive": True,
        "pending_terminal": "unresolved_with_binary_cost",
        "cost_mode": "binary_deadline_event",
        "robustness_cost_enabled": False,
    }
    mismatches = {
        key: (config.get(key), expected)
        for key, expected in required_semantics.items()
        if config.get(key) != expected
    }
    if mismatches:
        raise ValueError(f"unsupported Stage I rule semantics: {mismatches}")
    deadline_steps = config["deadline_steps"]
    if isinstance(deadline_steps, bool) or not isinstance(deadline_steps, int):
        raise TypeError("deadline_steps must be an integer in the rule configuration")
    BoundedRecoveryMonitor(
        float(config["d_warn"]),
        float(config["d_safe"]),
        deadline_steps,
    )
    return dict(config)


@lru_cache(maxsize=1)
def _public_observation_schema() -> DictSpace:
    """Inspect the public flattened-observation schema once per process."""

    environment = safety_gymnasium.make(BASE_ENVIRONMENT_ID)
    try:
        schema = environment.unwrapped.task.obs_info.obs_space_dict
        if not isinstance(schema, DictSpace):
            raise TypeError("SafetyPointGoal1-v0 public observation schema is not a Dict space")
        return schema
    finally:
        environment.close()


def _augmented_box(original: spaces.Box) -> spaces.Box:
    low = np.concatenate(
        [np.asarray(original.low, dtype=np.float32), np.zeros(3, dtype=np.float32)],
    )
    high = np.concatenate(
        [np.asarray(original.high, dtype=np.float32), np.ones(3, dtype=np.float32)],
    )
    return spaces.Box(low=low, high=high, dtype=np.float32)


def _optional_int(value: Optional[int]) -> int:
    return -1 if value is None else int(value)


def _monitor_scalar_diagnostics(output: MonitorOutput) -> Dict[str, Any]:
    return {
        "stl_sample_index": int(output.sample_index),
        "stl_distance": float(output.stl_distance),
        "stl_unsafe": bool(output.stl_unsafe),
        "stl_safe": bool(output.stl_safe),
        "stl_status": output.stl_status,
        "stl_warning_trigger": bool(output.stl_warning_trigger),
        "stl_recovery": bool(output.stl_recovery),
        "stl_late_recovery": bool(output.stl_late_recovery),
        "stl_deadline_violation": bool(output.stl_deadline_violation),
        "stl_terminal_unresolved": bool(output.stl_terminal_unresolved),
        "stl_trigger_step": _optional_int(output.stl_trigger_step),
        "stl_deadline_step": _optional_int(output.stl_deadline_step),
        "stl_elapsed_steps": _optional_int(output.stl_elapsed_steps),
        "stl_remaining_steps": _optional_int(output.stl_remaining_steps),
        "stl_episode_id": int(output.stl_episode_id),
    }


class Stage1TemporalCostWrapper(CMDP):
    """Add the Stage I monitor, temporal policy state, costs, and diagnostics."""

    need_auto_reset_wrapper = False
    need_time_limit_wrapper = False

    def __init__(
        self,
        base_env: CMDP,
        *,
        cost_mode: CostMode,
        observation_space_dict: DictSpace,
        lidar_range: float,
        d_warn: float,
        d_safe: float,
        deadline_steps: int,
        max_episode_steps: int,
        device: torch.device,
    ) -> None:
        self._base_env = base_env
        self._cost_mode = CostMode(cost_mode)
        self._observation_space_dict = observation_space_dict
        self._lidar_range = float(lidar_range)
        self._device = torch.device(device)
        self._d_warn = float(d_warn)
        self._d_safe = float(d_safe)
        self._num_envs = int(base_env.num_envs)
        self._max_episode_steps = int(max_episode_steps)
        self._action_space = base_env.action_space
        if not isinstance(base_env.observation_space, spaces.Box):
            raise TypeError("Stage I wrapper requires a flat Box observation space")
        self._observation_space = _augmented_box(base_env.observation_space)
        self._metadata = base_env.metadata
        self._monitors = [
            BoundedRecoveryMonitor(d_warn, d_safe, deadline_steps)
            for _ in range(self._num_envs)
        ]
        self._episode_metrics = np.zeros((self._num_envs, len(ENV_SPEC_KEYS)), dtype=np.float64)
        self._completed_records: Deque[Dict[str, float]] = deque()
        self.env_spec_log = {key: 0.0 for key in ENV_SPEC_KEYS}

    @property
    def max_episode_steps(self) -> int:
        return self._max_episode_steps

    @property
    def cost_mode(self) -> CostMode:
        return self._cost_mode

    @property
    def monitors(self) -> Tuple[BoundedRecoveryMonitor, ...]:
        """Expose monitor identities for integration diagnostics and tests."""

        return tuple(self._monitors)

    def _rows(self, observation: torch.Tensor) -> List[torch.Tensor]:
        if self._num_envs == 1:
            if observation.ndim != 1:
                raise ValueError("single-environment observation must be one-dimensional")
            return [observation]
        if observation.ndim != 2 or observation.shape[0] != self._num_envs:
            raise ValueError("vector observation must have shape (num_envs, observation_dim)")
        return [observation[index] for index in range(self._num_envs)]

    def _distance(self, observation: torch.Tensor) -> float:
        return distance_from_observation(
            observation.detach().cpu().numpy(),
            self._observation_space_dict,
            self._lidar_range,
        )

    def _augment(
        self,
        observation: torch.Tensor,
        states: Sequence[Tuple[float, float, float]],
    ) -> torch.Tensor:
        temporal = torch.as_tensor(states, dtype=observation.dtype, device=observation.device)
        if self._num_envs == 1:
            temporal = temporal[0]
        return torch.cat((observation, temporal), dim=-1)

    def _tensor(self, values: Sequence[Any], *, dtype: torch.dtype) -> torch.Tensor:
        tensor = torch.as_tensor(values, dtype=dtype, device=self._device)
        return tensor[0] if self._num_envs == 1 else tensor

    def _attach_monitor_info(
        self,
        info: Dict[str, Any],
        outputs: Sequence[MonitorOutput],
        native_cost: torch.Tensor,
        stl_cost: torch.Tensor,
        stl_dense_cost: torch.Tensor,
        selected_cost: torch.Tensor,
    ) -> None:
        scalar_rows = [_monitor_scalar_diagnostics(output) for output in outputs]
        float_fields = {"stl_distance"}
        bool_fields = {
            "stl_unsafe",
            "stl_safe",
            "stl_warning_trigger",
            "stl_recovery",
            "stl_late_recovery",
            "stl_deadline_violation",
            "stl_terminal_unresolved",
        }
        for key in scalar_rows[0]:
            values = [row[key] for row in scalar_rows]
            if key == "stl_status":
                info[key] = values[0] if self._num_envs == 1 else tuple(values)
            elif key in bool_fields:
                info[key] = self._tensor(values, dtype=torch.bool)
            elif key in float_fields:
                info[key] = self._tensor(values, dtype=torch.float32)
            else:
                info[key] = self._tensor(values, dtype=torch.int64)
        info["native_cost"] = native_cost.clone()
        info["stl_cost"] = stl_cost.clone()
        info["stl_dense_cost"] = stl_dense_cost.clone()
        info["selected_algorithm_cost"] = selected_cost.clone()
        info["stl_cost_mode"] = self._cost_mode.value

    def _attach_final_info(
        self,
        info: Dict[str, Any],
        outputs: Sequence[MonitorOutput],
        native_values: Sequence[float],
        stl_values: Sequence[float],
        stl_dense_values: Sequence[float],
        selected_values: Sequence[float],
        done: Sequence[bool],
    ) -> None:
        final_info = info.get("final_info")
        if final_info is None:
            return
        for index, is_done in enumerate(done):
            if not is_done:
                continue
            target = final_info if self._num_envs == 1 else final_info[index]
            if target is None:
                target = {}
                if self._num_envs == 1:
                    info["final_info"] = target
                else:
                    final_info[index] = target
            target.update(_monitor_scalar_diagnostics(outputs[index]))
            target["native_cost"] = native_values[index]
            target["stl_cost"] = stl_values[index]
            target["stl_dense_cost"] = stl_dense_values[index]
            target["selected_algorithm_cost"] = selected_values[index]
            target["stl_cost_mode"] = self._cost_mode.value

    def _reset_episode_metrics(self) -> None:
        self._episode_metrics.fill(0.0)
        self._completed_records.clear()

    def reset(
        self,
        seed: Optional[int] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Tuple[torch.Tensor, Dict[str, Any]]:
        observation, base_info = self._base_env.reset(seed=seed, options=options)
        rows = self._rows(observation)
        outputs = [
            monitor.reset(self._distance(row))
            for monitor, row in zip(self._monitors, rows)
        ]
        augmented = self._augment(observation, [monitor.policy_state() for monitor in self._monitors])
        self._reset_episode_metrics()
        info = dict(base_info)
        zero = (
            torch.zeros((), dtype=torch.float32, device=self._device)
            if self._num_envs == 1
            else torch.zeros(self._num_envs, dtype=torch.float32, device=self._device)
        )
        self._attach_monitor_info(info, outputs, zero, zero, zero, zero)
        zero_values = [0.0] * self._num_envs
        self._record_episode_metrics(
            outputs,
            zero_values,
            zero_values,
            zero_values,
            zero_values,
            zero_values,
            [False] * self._num_envs,
        )
        return augmented, info

    def step(
        self,
        action: torch.Tensor,
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, Dict[str, Any]]:
        observation, reward, native_cost, terminated, truncated, base_info = self._base_env.step(
            action,
        )
        info = dict(base_info)
        rows = self._rows(observation)
        terminated_values = [bool(value) for value in terminated.detach().cpu().reshape(-1)]
        truncated_values = [bool(value) for value in truncated.detach().cpu().reshape(-1)]
        done = [a or b for a, b in zip(terminated_values, truncated_values)]
        final_observation = info.get("final_observation")
        if any(done) and final_observation is None:
            raise RuntimeError(
                "base environment ended without final_observation; monitor-safe auto-reset is impossible",
            )

        final_rows: Optional[List[torch.Tensor]] = None
        final_states: Optional[List[Optional[Tuple[float, float, float]]]] = None
        if final_observation is not None:
            final_rows = self._rows(final_observation)
            final_states = [None] * self._num_envs

        outputs: List[MonitorOutput] = []
        returned_states: List[Tuple[float, float, float]] = []
        for index, monitor in enumerate(self._monitors):
            if done[index]:
                assert final_rows is not None and final_states is not None
                output = monitor.step(
                    self._distance(final_rows[index]),
                    terminated=terminated_values[index],
                    truncated=truncated_values[index],
                )
                final_states[index] = monitor.policy_state()
                monitor.reset(self._distance(rows[index]))
                returned_states.append(monitor.policy_state())
            else:
                output = monitor.step(self._distance(rows[index]))
                returned_states.append(monitor.policy_state())
                if final_states is not None:
                    # Vector APIs carry placeholder final-observation rows for
                    # non-terminal environments.  They are masked downstream,
                    # but still require the augmented shape.
                    final_states[index] = monitor.policy_state()
            outputs.append(output)

        augmented = self._augment(observation, returned_states)
        if final_rows is not None and final_states is not None:
            if any(state is None for state in final_states):
                raise AssertionError("every final-observation row requires temporal state")
            final_augmented_rows = [
                torch.cat(
                    (
                        row,
                        torch.as_tensor(state, dtype=row.dtype, device=row.device),
                    ),
                )
                for row, state in zip(final_rows, final_states)
            ]
            if self._num_envs == 1:
                info["final_observation"] = final_augmented_rows[0]
            else:
                info["final_observation"] = torch.stack(final_augmented_rows)

        stl_values = [float(output.stl_cost) for output in outputs]
        stl_cost = self._tensor(stl_values, dtype=torch.float32)
        stl_dense_values = [
            causal_dense_surrogate(output, self._d_warn, self._d_safe) for output in outputs
        ]
        stl_dense_cost = self._tensor(stl_dense_values, dtype=torch.float32)
        native_cost = native_cost.to(dtype=torch.float32, device=self._device)
        selected_cost = select_algorithm_cost(
            self._cost_mode,
            native_cost,
            stl_cost,
            stl_dense_cost,
        )
        native_values = [float(value) for value in native_cost.detach().cpu().reshape(-1)]
        selected_values = [float(value) for value in selected_cost.detach().cpu().reshape(-1)]
        goal_met = info.get("goal_met", False)
        if isinstance(goal_met, torch.Tensor):
            goal_values = [float(value) for value in goal_met.detach().cpu().reshape(-1)]
        elif isinstance(goal_met, (list, tuple, np.ndarray)):
            goal_values = [float(value) for value in np.asarray(goal_met).reshape(-1)]
        else:
            goal_values = [float(goal_met)] * self._num_envs
        final_info = info.get("final_info")
        if final_info is not None:
            for index, is_done in enumerate(done):
                if not is_done:
                    continue
                target = final_info if self._num_envs == 1 else final_info[index]
                if isinstance(target, Mapping) and "goal_met" in target:
                    goal_values[index] = float(target["goal_met"])

        self._attach_monitor_info(
            info,
            outputs,
            native_cost,
            stl_cost,
            stl_dense_cost,
            selected_cost,
        )
        self._attach_final_info(
            info,
            outputs,
            native_values,
            stl_values,
            stl_dense_values,
            selected_values,
            done,
        )
        self._record_episode_metrics(
            outputs,
            native_values,
            stl_values,
            stl_dense_values,
            selected_values,
            goal_values,
            done,
        )
        return augmented, reward, selected_cost, terminated, truncated, info

    def _record_episode_metrics(
        self,
        outputs: Sequence[MonitorOutput],
        native_values: Sequence[float],
        stl_values: Sequence[float],
        stl_dense_values: Sequence[float],
        selected_values: Sequence[float],
        goal_values: Sequence[float],
        done: Sequence[bool],
    ) -> None:
        for index, output in enumerate(outputs):
            increments = (
                native_values[index],
                stl_values[index],
                stl_dense_values[index],
                selected_values[index],
                float(output.stl_warning_trigger),
                float(output.stl_recovery),
                float(output.stl_late_recovery),
                float(output.stl_deadline_violation),
                float(output.stl_terminal_unresolved),
                goal_values[index],
            )
            self._episode_metrics[index] += np.asarray(increments, dtype=np.float64)
            if done[index]:
                self._completed_records.append(
                    {
                        key: float(value)
                        for key, value in zip(ENV_SPEC_KEYS, self._episode_metrics[index])
                    },
                )
                self._episode_metrics[index].fill(0.0)

    def spec_log(self, logger: Any) -> None:
        """Store one completed episode's independent cost/monitor totals."""

        if not self._completed_records:
            raise RuntimeError("OmniSafe requested environment metrics without a completed episode")
        logger.store(self._completed_records.popleft())

    def set_seed(self, seed: int) -> None:
        self.reset(seed=seed)

    def render(self) -> Any:
        return self._base_env.render()

    def close(self) -> None:
        self._base_env.close()

    def validation_task(self) -> Any:
        """Return single-env simulator state for diagnostics, never policy input."""

        if self._num_envs != 1:
            raise RuntimeError("privileged validation task is available only for one environment")
        return self._base_env._env.unwrapped.task  # pylint: disable=protected-access


@env_register
class Stage1SafetyPointGoalEnv(Stage1TemporalCostWrapper):
    """Registered construction surface for Stage I and the D38 dense diagnostic."""

    _support_envs: ClassVar[List[str]] = list(REGISTERED_ENV_IDS)

    def __init__(
        self,
        env_id: str,
        num_envs: int = 1,
        device: torch.device = torch.device("cpu"),
        rule_config_path: Optional[str] = None,
        scenario_config_path: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        if env_id not in ENV_ID_TO_COST_MODE:
            raise ValueError(f"unsupported Stage I environment ID: {env_id}")
        if num_envs <= 0:
            raise ValueError("num_envs must be positive")
        config_path = DEFAULT_RULE_CONFIG if rule_config_path is None else Path(rule_config_path)
        config = _load_rule_config(config_path)
        scenario: Optional[FixedRouteScenario] = None
        if scenario_config_path is not None:
            scenario = load_fixed_route_scenario(Path(scenario_config_path))
            if not (
                np.isclose(float(config["d_warn"]), scenario.d_warn)
                and np.isclose(float(config["d_safe"]), scenario.d_safe)
            ):
                raise ValueError(
                    "fixed-route thresholds must match the executable rule configuration; "
                    "recalibrate K and provide a matching rule_config_path before training",
                )
            if bool(kwargs.get("asynchronous", False)):
                raise ValueError("fixed-route environments require asynchronous=False")
            if num_envs > 1:
                kwargs["asynchronous"] = False
            else:
                # Safety-Gymnasium's scalar make() does not accept the vector
                # constructor's asynchronous keyword.
                kwargs.pop("asynchronous", None)
        max_episode_steps = int(kwargs.get("max_episode_steps", 1000))
        base_env = SafetyGymnasiumEnv(
            BASE_ENVIRONMENT_ID,
            num_envs=num_envs,
            device=device,
            **kwargs,
        )
        if scenario is not None:
            installed = install_on_omnisafe_base_env(base_env, scenario)
            if installed != num_envs:
                raise RuntimeError(
                    f"fixed route installed on {installed} environments, expected {num_envs}",
                )
        super().__init__(
            base_env,
            cost_mode=ENV_ID_TO_COST_MODE[env_id],
            observation_space_dict=_public_observation_schema(),
            lidar_range=float(config["lidar_range"]),
            d_warn=float(config["d_warn"]),
            d_safe=float(config["d_safe"]),
            deadline_steps=int(config["deadline_steps"]),
            max_episode_steps=max_episode_steps,
            device=torch.device(device),
        )
        self.fixed_route_scenario = scenario


def register_stage1_envs() -> Tuple[str, ...]:
    """Return registered IDs; importing this module performs registration."""

    return REGISTERED_ENV_IDS


__all__ = [
    "BASE_ENVIRONMENT_ID",
    "CostMode",
    "NATIVE_COST_ENV_ID",
    "REGISTERED_ENV_IDS",
    "STL_COST_ENV_ID",
    "STL_DENSE_COST_ENV_ID",
    "Stage1SafetyPointGoalEnv",
    "Stage1TemporalCostWrapper",
    "TASK_ONLY_ENV_ID",
    "TEMPORAL_OBSERVATION_FIELDS",
    "register_stage1_envs",
    "select_algorithm_cost",
]
