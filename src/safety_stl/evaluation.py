"""Common gold-oracle checkpoint evaluation for Stage I policies."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, stdev
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import torch
import yaml
from omnisafe.envs.core import make
from omnisafe.models.actor import ActorBuilder
from omnisafe.models.base import Actor

from safety_stl.omnisafe_env import STL_COST_ENV_ID
from safety_stl.oracle import evaluate_trace, rtamt_window_robustness


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RULE_CONFIG = REPOSITORY_ROOT / "configs" / "stage1_rule.yaml"


@dataclass(frozen=True)
class LoadedPolicy:
    """Actor and immutable preprocessing state loaded from an OmniSafe run."""

    actor: Actor
    run_config: Dict[str, Any]
    checkpoint_path: Path
    normalizer_state: Optional[Dict[str, torch.Tensor]]

    def policy_observation(self, observation: torch.Tensor) -> torch.Tensor:
        """Apply the saved observation transform without updating its statistics."""

        if self.normalizer_state is None:
            return observation
        count = int(self.normalizer_state["_count"].item())
        if count <= 1:
            return observation
        normalized = (observation - self.normalizer_state["_mean"]) / self.normalizer_state["_std"]
        clip = self.normalizer_state["_clip"]
        return torch.maximum(torch.minimum(normalized, clip), -clip)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_json_mapping(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, Mapping):
        raise ValueError(f"expected a mapping in {path}")
    return dict(value)


def _torch_load_weights(path: Path) -> Dict[str, Any]:
    try:
        value = torch.load(path, map_location="cpu", weights_only=True)
    except TypeError:  # pragma: no cover - compatibility with older PyTorch
        value = torch.load(path, map_location="cpu")
    if not isinstance(value, Mapping) or "pi" not in value:
        raise ValueError(f"checkpoint does not contain an OmniSafe 'pi' state: {path}")
    return dict(value)


def load_policy(run_dir: Path, checkpoint_name: str, observation_space: Any, action_space: Any) -> LoadedPolicy:
    """Load one on-policy OmniSafe actor and any saved observation statistics."""

    run_dir = run_dir.resolve()
    config = _load_json_mapping(run_dir / "config.json")
    checkpoint_path = run_dir / "torch_save" / checkpoint_name
    checkpoint = _torch_load_weights(checkpoint_path)
    model_cfgs = config["model_cfgs"]
    actor_cfgs = model_cfgs["actor"]
    actor = ActorBuilder(
        obs_space=observation_space,
        act_space=action_space,
        hidden_sizes=list(actor_cfgs["hidden_sizes"]),
        activation=str(actor_cfgs["activation"]),
        weight_initialization_mode=str(model_cfgs["weight_initialization_mode"]),
    ).build_actor(str(model_cfgs["actor_type"]))
    actor.load_state_dict(checkpoint["pi"])
    actor.eval()

    normalizer_state: Optional[Dict[str, torch.Tensor]] = None
    if bool(config["algo_cfgs"].get("obs_normalize", False)):
        if "obs_normalizer" not in checkpoint:
            raise ValueError("run config enables obs_normalize but checkpoint has no normalizer")
        normalizer_state = {
            key: tensor.detach().cpu().clone()
            for key, tensor in checkpoint["obs_normalizer"].items()
        }
    return LoadedPolicy(actor, config, checkpoint_path, normalizer_state)


def _scalar(value: Any) -> float:
    if isinstance(value, torch.Tensor):
        return float(value.detach().cpu().item())
    return float(value)


def _boolean(value: Any) -> bool:
    if isinstance(value, torch.Tensor):
        return bool(value.detach().cpu().item())
    return bool(value)


def _optional_monitor_int(value: Any) -> Optional[int]:
    parsed = int(_scalar(value))
    return None if parsed < 0 else parsed


def _trajectory_row(
    info: Mapping[str, Any],
    *,
    action_index: int,
    action: Optional[torch.Tensor],
    reward: float,
    native_cost: float,
    selected_algorithm_cost: float,
    terminated: bool,
    truncated: bool,
    goal_met: bool,
) -> Dict[str, Any]:
    """Build one complete public-signal/monitor record for diagnostic replay."""

    action_values: List[Optional[float]] = [None, None]
    if action is not None:
        flattened = action.detach().cpu().reshape(-1).tolist()
        for index, value in enumerate(flattened[:2]):
            action_values[index] = float(value)
    return {
        "action_index": int(action_index),
        "sample_index": int(_scalar(info["stl_sample_index"])),
        "action_forward": action_values[0],
        "action_turn": action_values[1],
        "distance": _scalar(info["stl_distance"]),
        "unsafe": _boolean(info["stl_unsafe"]),
        "safe": _boolean(info["stl_safe"]),
        "monitor_state": str(info["stl_status"]),
        "warning_trigger": _boolean(info["stl_warning_trigger"]),
        "recovery": _boolean(info["stl_recovery"]),
        "late_recovery": _boolean(info["stl_late_recovery"]),
        "deadline_violation": _boolean(info["stl_deadline_violation"]),
        "terminal_unresolved": _boolean(info["stl_terminal_unresolved"]),
        "trigger_step": _optional_monitor_int(info["stl_trigger_step"]),
        "deadline_step": _optional_monitor_int(info["stl_deadline_step"]),
        "elapsed_steps": _optional_monitor_int(info["stl_elapsed_steps"]),
        "remaining_steps": _optional_monitor_int(info["stl_remaining_steps"]),
        "warning_episode_id": int(_scalar(info["stl_episode_id"])),
        "reward": float(reward),
        "native_cost": float(native_cost),
        "stl_cost": int(_scalar(info["stl_cost"])),
        "selected_algorithm_cost": float(selected_algorithm_cost),
        "goal_met": bool(goal_met),
        "terminated": bool(terminated),
        "truncated": bool(truncated),
    }


def _fixed_route_geometry(environment: Any) -> Dict[str, Any]:
    """Return privileged geometry used only by fixed-route diagnostic plots."""

    task = environment._base_env._env.unwrapped.task  # pylint: disable=protected-access
    row: Dict[str, Any] = {
        "agent_x": float(task.agent.pos[0]),
        "agent_y": float(task.agent.pos[1]),
        "goal_index": int(getattr(task, "fixed_route_goal_index", -1)),
        "goal_x": float(task.goal.pos[0]),
        "goal_y": float(task.goal.pos[1]),
    }
    for index, hazard in enumerate(task.hazards.pos):
        row[f"hazard_{index}_x"] = float(hazard[0])
        row[f"hazard_{index}_y"] = float(hazard[1])
    return row


def _goal_met(info: Mapping[str, Any], done: bool) -> bool:
    if done and isinstance(info.get("final_info"), Mapping):
        final_info = info["final_info"]
        if "goal_met" in final_info:
            return bool(final_info["goal_met"])
    return bool(info.get("goal_met", False))


def _event_steps(rows: Sequence[Mapping[str, Any]], field: str) -> List[int]:
    return [int(row["sample_index"]) for row in rows if bool(row[field])]


def verify_gold_oracle(
    rows: Sequence[Mapping[str, Any]],
    *,
    d_warn: float,
    d_safe: float,
    deadline_steps: int,
    tolerance: float,
) -> Dict[str, Any]:
    """Re-evaluate one episode independently and require exact event/cost agreement."""

    distances = [float(row["distance"]) for row in rows]
    terminated = [bool(row["terminated"]) for row in rows]
    truncated = [bool(row["truncated"]) for row in rows]
    oracle = evaluate_trace(
        distances,
        d_warn,
        d_safe,
        deadline_steps,
        terminated=terminated,
        truncated=truncated,
    )
    comparisons = {
        "trigger_steps": (_event_steps(rows, "warning_trigger"), oracle.trigger_steps),
        "recovery_steps": (_event_steps(rows, "recovery"), oracle.recovery_steps),
        "late_recovery_steps": (_event_steps(rows, "late_recovery"), oracle.late_recovery_steps),
        "violation_steps": (_event_steps(rows, "deadline_violation"), oracle.violation_steps),
        "unresolved_steps": (_event_steps(rows, "terminal_unresolved"), oracle.unresolved_steps),
        "costs": ([int(row["stl_cost"]) for row in rows], oracle.costs),
    }
    mismatches = {
        name: {"online": online, "oracle": expected}
        for name, (online, expected) in comparisons.items()
        if online != expected
    }
    rtamt_differences: List[float] = []
    for window in oracle.completed_windows:
        values = distances[window.trigger_step : window.deadline_step + 1]
        rtamt_value = rtamt_window_robustness(values, d_safe, deadline_steps)
        difference = abs(rtamt_value - window.robustness)
        rtamt_differences.append(difference)
        if difference > tolerance:
            mismatches[f"rtamt_window_{window.episode_id}"] = {
                "direct_robustness": window.robustness,
                "rtamt_robustness": rtamt_value,
                "absolute_difference": difference,
            }
    if mismatches:
        raise AssertionError(f"online/offline gold-oracle mismatch: {mismatches}")
    return {
        "trigger_count": len(oracle.trigger_steps),
        "recovery_count": len(oracle.recovery_steps),
        "late_recovery_count": len(oracle.late_recovery_steps),
        "deadline_violation_count": len(oracle.violation_steps),
        "terminal_unresolved_count": len(oracle.unresolved_steps),
        "stl_event_cost_total": int(sum(oracle.costs)),
        "on_time_recovery_latency_sum": sum(
            event.outcome_step - event.trigger_step
            for event in oracle.events
            if event.outcome == "recovery"
        ),
        "deadline_violation_delay_sum": sum(
            event.outcome_step - event.trigger_step
            for event in oracle.events
            if event.outcome == "deadline_violation"
        ),
        "terminal_unresolved_delay_sum": sum(
            event.outcome_step - event.trigger_step
            for event in oracle.events
            if event.outcome == "terminal_unresolved"
        ),
        "completed_window_count": len(oracle.completed_windows),
        "trace_robustness": (
            min(window.robustness for window in oracle.completed_windows)
            if oracle.completed_windows
            else None
        ),
        "rtamt_max_robustness_difference": max(rtamt_differences, default=0.0),
        "agreement": True,
    }


def _metric_summary(values: Sequence[float]) -> Dict[str, Optional[float]]:
    return {
        "mean": float(mean(values)),
        "sample_std": float(stdev(values)) if len(values) > 1 else None,
        "min": float(min(values)),
        "max": float(max(values)),
    }


def summarize_episodes(episodes: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """Aggregate episode records without hiding the per-seed data."""

    if not episodes:
        raise ValueError("at least one episode is required")
    scalar_fields = (
        "episode_return",
        "native_cost_total",
        "gold_stl_cost_total",
        "goal_events",
        "episode_length",
        "minimum_distance",
        "trigger_count",
        "recovery_count",
        "deadline_violation_count",
        "terminal_unresolved_count",
    )
    optional_diagnostic_fields = (
        "on_time_recovery_latency_sum",
        "deadline_violation_delay_sum",
        "terminal_unresolved_delay_sum",
        "positive_cost_step_count",
    )
    metrics = {
        field: _metric_summary([float(episode[field]) for episode in episodes])
        for field in scalar_fields
    }
    metrics.update(
        {
            field: _metric_summary([float(episode.get(field, 0.0)) for episode in episodes])
            for field in optional_diagnostic_fields
        },
    )
    triggers = sum(int(episode["trigger_count"]) for episode in episodes)
    recoveries = sum(int(episode["recovery_count"]) for episode in episodes)
    violations = sum(int(episode["deadline_violation_count"]) for episode in episodes)
    unresolved = sum(int(episode["terminal_unresolved_count"]) for episode in episodes)
    return {
        "episode_count": len(episodes),
        "metrics": metrics,
        "goal_success_rate": sum(bool(episode["goal_success"]) for episode in episodes)
        / len(episodes),
        "triggered_episode_rate": sum(int(episode["trigger_count"]) > 0 for episode in episodes)
        / len(episodes),
        "pooled_counts": {
            "triggers": triggers,
            "on_time_recoveries": recoveries,
            "deadline_violations": violations,
            "terminal_unresolved": unresolved,
        },
        "pooled_rates_per_trigger": {
            "on_time_recovery": recoveries / triggers if triggers else None,
            "deadline_violation": violations / triggers if triggers else None,
            "terminal_unresolved": unresolved / triggers if triggers else None,
            "missed_recovery_obligation": (
                (violations + unresolved) / triggers if triggers else None
            ),
            # Backward-compatible diagnostic alias; the D31 primary name is
            # missed_recovery_obligation.
            "adverse_outcome": (violations + unresolved) / triggers if triggers else None,
        },
        "all_online_oracle_agree": all(bool(episode["online_oracle_agreement"]) for episode in episodes),
        "rtamt_completed_window_count": sum(
            int(episode["completed_window_count"]) for episode in episodes
        ),
        "rtamt_max_robustness_difference": max(
            float(episode["rtamt_max_robustness_difference"]) for episode in episodes
        ),
    }


def _load_rule(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    if not isinstance(value, Mapping):
        raise ValueError("rule configuration must be a mapping")
    return dict(value)


def evaluate_checkpoint(
    run_dir: Path,
    checkpoint_name: str,
    episode_seeds: Sequence[int],
    *,
    max_episode_steps: int = 1000,
    deterministic: bool = True,
    rule_config_path: Path = DEFAULT_RULE_CONFIG,
    scenario_config_path: Optional[Path] = None,
    save_trajectories: bool = False,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Evaluate a checkpoint with the same gold monitor and offline oracle."""

    if not episode_seeds:
        raise ValueError("episode_seeds must not be empty")
    if max_episode_steps <= 0:
        raise ValueError("max_episode_steps must be positive")
    rule = _load_rule(rule_config_path)
    environment_kwargs: Dict[str, Any] = {
        "num_envs": 1,
        "device": torch.device("cpu"),
        "max_episode_steps": max_episode_steps,
        "rule_config_path": str(rule_config_path.resolve()),
    }
    if scenario_config_path is not None:
        environment_kwargs.update(
            {
                "scenario_config_path": str(scenario_config_path.resolve()),
                "asynchronous": False,
            },
        )
    environment = make(STL_COST_ENV_ID, **environment_kwargs)
    episodes: List[Dict[str, Any]] = []
    trajectory_records: List[Dict[str, Any]] = []
    try:
        policy = load_policy(
            run_dir,
            checkpoint_name,
            environment.observation_space,
            environment.action_space,
        )
        for episode_index, seed in enumerate(episode_seeds):
            torch.manual_seed(int(seed))
            observation, reset_info = environment.reset(seed=int(seed))
            rows: List[Dict[str, Any]] = [
                _trajectory_row(
                    reset_info,
                    action_index=-1,
                    action=None,
                    reward=0.0,
                    native_cost=0.0,
                    selected_algorithm_cost=0.0,
                    terminated=False,
                    truncated=False,
                    goal_met=False,
                ),
            ]
            if scenario_config_path is not None:
                rows[0].update(_fixed_route_geometry(environment))
            episode_return = 0.0
            native_cost_total = 0.0
            online_stl_cost_total = 0.0
            goal_events = 0
            action_count = 0
            done = False
            while not done:
                actor_observation = policy.policy_observation(observation)
                with torch.no_grad():
                    action = policy.actor.predict(actor_observation, deterministic=deterministic)
                observation, reward, selected_cost, terminated, truncated, info = environment.step(
                    action,
                )
                term = _boolean(terminated)
                trunc = _boolean(truncated)
                done = term or trunc
                action_count += 1
                episode_return += _scalar(reward)
                native_cost_total += _scalar(info["native_cost"])
                online_stl_cost_total += _scalar(info["stl_cost"])
                goal_met = _goal_met(info, done)
                goal_events += int(goal_met)
                row = _trajectory_row(
                    info,
                    action_index=action_count - 1,
                    action=action,
                    reward=_scalar(reward),
                    native_cost=_scalar(info["native_cost"]),
                    selected_algorithm_cost=_scalar(selected_cost),
                    terminated=term,
                    truncated=trunc,
                    goal_met=goal_met,
                )
                if scenario_config_path is not None:
                    if done:
                        row.update(
                            {
                                key: value
                                for key, value in rows[-1].items()
                                if key.startswith(("agent_", "goal_", "hazard_"))
                            },
                        )
                    else:
                        row.update(_fixed_route_geometry(environment))
                rows.append(row)
                if action_count > max_episode_steps + 1:
                    raise RuntimeError("evaluation episode exceeded its declared horizon")

            oracle = verify_gold_oracle(
                rows,
                d_warn=float(rule["d_warn"]),
                d_safe=float(rule["d_safe"]),
                deadline_steps=int(rule["deadline_steps"]),
                tolerance=float(rule["agreement_tolerance"]),
            )
            if not math.isclose(
                online_stl_cost_total,
                float(oracle["stl_event_cost_total"]),
                rel_tol=0.0,
                abs_tol=1e-9,
            ):
                raise AssertionError("online STL-cost total differs from the offline gold oracle")
            record = {
                "episode_index": episode_index,
                "evaluation_seed": int(seed),
                "episode_length": action_count,
                "episode_return": episode_return,
                "native_cost_total": native_cost_total,
                "gold_stl_cost_total": int(oracle["stl_event_cost_total"]),
                "goal_events": goal_events,
                "goal_success": goal_events > 0,
                "minimum_distance": min(float(row["distance"]) for row in rows),
                "trigger_count": int(oracle["trigger_count"]),
                "recovery_count": int(oracle["recovery_count"]),
                "late_recovery_count": int(oracle["late_recovery_count"]),
                "deadline_violation_count": int(oracle["deadline_violation_count"]),
                "terminal_unresolved_count": int(oracle["terminal_unresolved_count"]),
                "on_time_recovery_latency_sum": int(oracle["on_time_recovery_latency_sum"]),
                "deadline_violation_delay_sum": int(oracle["deadline_violation_delay_sum"]),
                "terminal_unresolved_delay_sum": int(oracle["terminal_unresolved_delay_sum"]),
                "positive_cost_step_count": sum(int(row["stl_cost"]) for row in rows),
                "completed_window_count": int(oracle["completed_window_count"]),
                "trace_robustness": oracle["trace_robustness"],
                "online_oracle_agreement": bool(oracle["agreement"]),
                "rtamt_max_robustness_difference": float(
                    oracle["rtamt_max_robustness_difference"],
                ),
            }
            episodes.append(record)
            if save_trajectories:
                for row in rows:
                    trajectory_records.append(
                        {"episode_index": episode_index, "evaluation_seed": int(seed), **row},
                    )

        summary = {
            "schema_version": 1,
            "evaluation_environment_id": STL_COST_ENV_ID,
            "policy_training_environment_id": str(policy.run_config["env_id"]),
            "checkpoint": str(policy.checkpoint_path),
            "checkpoint_sha256": sha256_file(policy.checkpoint_path),
            "deterministic_policy": bool(deterministic),
            "max_episode_steps": max_episode_steps,
            "episode_seeds": [int(seed) for seed in episode_seeds],
            "rule": {
                "d_warn": float(rule["d_warn"]),
                "d_safe": float(rule["d_safe"]),
                "deadline_steps": int(rule["deadline_steps"]),
            },
            "primary_safety_metric": {
                "name": "missed_recovery_obligations_per_triggered_recovery_obligation",
                "numerator": ["deadline_violation", "terminal_unresolved"],
                "denominator": "warning_trigger",
            },
            "aggregate": summarize_episodes(episodes),
            "scope": "checkpoint evaluation only; no comparison or safety claim",
        }
        return summary, episodes, trajectory_records
    finally:
        environment.close()


def write_evaluation_outputs(
    output_dir: Path,
    summary: Mapping[str, Any],
    episodes: Sequence[Mapping[str, Any]],
    trajectories: Sequence[Mapping[str, Any]],
) -> Dict[str, str]:
    """Write machine-readable aggregate, episode, and optional trajectory records."""

    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "summary.json"
    episode_path = output_dir / "episodes.csv"
    with summary_path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, sort_keys=True)
        handle.write("\n")
    with episode_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(episodes[0]))
        writer.writeheader()
        writer.writerows(episodes)
    paths = {"summary": str(summary_path), "episodes": str(episode_path)}
    if trajectories:
        trajectory_path = output_dir / "trajectories.jsonl"
        with trajectory_path.open("w", encoding="utf-8") as handle:
            for row in trajectories:
                handle.write(json.dumps(row, sort_keys=True) + "\n")
        paths["trajectories"] = str(trajectory_path)
    return paths


__all__ = [
    "LoadedPolicy",
    "evaluate_checkpoint",
    "load_policy",
    "summarize_episodes",
    "verify_gold_oracle",
    "write_evaluation_outputs",
]
