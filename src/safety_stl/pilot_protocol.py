"""Validation and composition for the frozen Stage I pilot protocol."""

from __future__ import annotations

import copy
import math
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence

import yaml


PILOT_PROTOCOL_ID = "stage1_gold_stl_pilot_v1"
PILOT_STATUS = "frozen_stage1_pilot_not_final_main_study_standard"
CONDITION_CONTRACTS = {
    "task_only": {
        "environment_id": "Stage1SafetyPointGoal1TaskOnly-v0",
        "selected_algorithm_cost": "identically_zero",
        "cost_limit": 0.0,
        "semantic_unit": "selected_learner_cost_is_identically_zero",
    },
    "native_cost": {
        "environment_id": "Stage1SafetyPointGoal1NativeCost-v0",
        "selected_algorithm_cost": "native_cost",
        "cost_limit": 25.0,
        "semantic_unit": "native_hazard_cost_steps_per_1000_step_episode",
    },
    "gold_stl_cost": {
        "environment_id": "Stage1SafetyPointGoal1STLCost-v0",
        "selected_algorithm_cost": "stl_cost",
        "cost_limit": 0.1,
        "semantic_unit": "missed_recovery_obligation_events_per_1000_step_episode",
    },
}


def load_yaml_mapping(path: Path) -> Dict[str, Any]:
    """Load one YAML mapping or fail with a path-specific error."""

    with path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle)
    if not isinstance(loaded, Mapping):
        raise ValueError(f"expected a YAML mapping: {path}")
    return dict(loaded)


def validate_protocol(protocol: Mapping[str, Any]) -> None:
    """Require the owner-approved scientific and rollout invariants."""

    if protocol.get("protocol_id") != PILOT_PROTOCOL_ID:
        raise ValueError("unexpected pilot protocol_id")
    if protocol.get("status") != PILOT_STATUS:
        raise ValueError("pilot protocol must remain explicitly non-final")
    safety = protocol["primary_safety_metric"]
    if list(safety["numerator"]) != ["deadline_violation", "terminal_unresolved"]:
        raise ValueError("primary safety numerator does not match D31")
    if safety["denominator"] != "warning_trigger":
        raise ValueError("primary safety denominator does not match D31")
    if not math.isclose(float(safety["target_relative_reduction"]), 0.30):
        raise ValueError("pilot relative-reduction target must be 0.30")
    if not bool(safety["always_report_absolute_difference"]):
        raise ValueError("the absolute safety difference must always be reported")
    if safety["absolute_reduction_definition"] != "task_only_rate_minus_gold_stl_rate":
        raise ValueError("absolute safety reduction must be positive when gold STL improves")
    if safety["relative_reduction_definition"] != (
        "absolute_reduction_divided_by_task_only_rate"
    ):
        raise ValueError("relative safety reduction definition does not match D31")
    if "undefined" not in str(safety["if_task_only_baseline_rate_is_zero"]):
        raise ValueError("zero-baseline behavior must make relative reduction undefined")

    noninferiority = protocol["goal_success_noninferiority"]
    if int(noninferiority["absolute_margin_percentage_points"]) != 10:
        raise ValueError("goal-success non-inferiority margin must be 10 percentage points")
    design = protocol["matched_design"]
    if list(design["training_seeds"]) != [1101, 2202, 3303, 4404, 5505]:
        raise ValueError("pilot training seeds do not match D31")
    if int(design["evaluation_episodes_per_training_seed_and_condition"]) != 100:
        raise ValueError("pilot evaluation count must be 100 per seed and condition")
    if design["checkpoint_selection"] != "fixed_final_checkpoint":
        raise ValueError("pilot primary evaluation must use the fixed final checkpoint")
    if design["policy_mode"] != "deterministic":
        raise ValueError("pilot policy mode must be deterministic")
    uncertainty = design["uncertainty"]
    if int(uncertainty["replicates"]) != 10000:
        raise ValueError("paired hierarchical bootstrap must use 10,000 replicates")
    if not (
        bool(uncertainty["resample_training_seeds"])
        and bool(uncertainty["resample_matched_evaluation_episodes_within_training_seed"])
    ):
        raise ValueError("hierarchical bootstrap levels do not match D31")

    budgets = protocol["condition_budget_contract"]
    if not bool(budgets["units_are_different"]):
        raise ValueError("native and STL units must remain explicitly different")
    for condition, contract in CONDITION_CONTRACTS.items():
        declared = budgets[condition]
        if not math.isclose(float(declared["cost_limit"]), float(contract["cost_limit"])):
            raise ValueError(f"{condition} cost limit does not match D31")
        if declared["semantic_unit"] != contract["semantic_unit"]:
            raise ValueError(f"{condition} semantic unit does not match D31")

    pilot_budget = protocol["pilot_budget"]
    if int(pilot_budget["transitions_per_condition_and_training_seed"]) != 1_000_000:
        raise ValueError("frozen pilot budget must be 1M transitions")
    if not bool(pilot_budget["require_learning_curve_review_before_convergence_claim"]):
        raise ValueError("learning-curve review guard is missing")
    if not bool(pilot_budget["full_runs_require_small_budget_sanity_gate"]):
        raise ValueError("small-budget sanity gate is missing")
    if pilot_budget["cuda_determinism_environment"].get("CUBLAS_WORKSPACE_CONFIG") != (
        ":4096:8"
    ):
        raise ValueError("D32 CUDA runs require the deterministic cuBLAS workspace setting")

    omnisafe_cfg = protocol["omnisafe"]
    train_cfgs = omnisafe_cfg["train_cfgs"]
    algo_cfgs = omnisafe_cfg["algo_cfgs"]
    env_cfgs = omnisafe_cfg["env_cfgs"]
    steps_per_epoch = int(algo_cfgs["steps_per_epoch"])
    vector_env_nums = int(train_cfgs["vector_env_nums"])
    episode_horizon = int(env_cfgs["max_episode_steps"])
    if int(train_cfgs["total_steps"]) != 1_000_000:
        raise ValueError("OmniSafe total_steps must match the 1M pilot budget")
    if train_cfgs["device"] != "cuda:0":
        raise ValueError("D32 requires the frozen pilot training backend to use cuda:0")
    if steps_per_epoch % vector_env_nums:
        raise ValueError("steps_per_epoch must divide evenly across vector environments")
    if (steps_per_epoch // vector_env_nums) % episode_horizon:
        raise ValueError("each rollout slot must contain complete episode horizons")


def validate_condition_overlay(overlay: Mapping[str, Any]) -> str:
    """Validate one immutable condition-specific environment/cost overlay."""

    if overlay.get("protocol_id") != PILOT_PROTOCOL_ID:
        raise ValueError("condition overlay uses the wrong protocol_id")
    if overlay.get("status") != "frozen_condition_overlay":
        raise ValueError("condition overlay is not frozen")
    condition = str(overlay.get("condition"))
    if condition not in CONDITION_CONTRACTS:
        raise ValueError(f"unexpected pilot condition: {condition}")
    contract = CONDITION_CONTRACTS[condition]
    comparisons = {
        "environment_id": overlay.get("environment_id") == contract["environment_id"],
        "selected_algorithm_cost": (
            overlay.get("selected_algorithm_cost") == contract["selected_algorithm_cost"]
        ),
        "lagrange_cost_limit": math.isclose(
            float(overlay.get("lagrange_cost_limit")),
            float(contract["cost_limit"]),
        ),
        "cost_semantic_unit": overlay.get("cost_semantic_unit") == contract["semantic_unit"],
    }
    if not all(comparisons.values()):
        raise ValueError(f"{condition} overlay violates D31: {comparisons}")
    if condition == "gold_stl_cost" and "10_percent" not in str(
        overlay.get("interpretation_guard"),
    ):
        raise ValueError("STL cost limit requires the non-percentage interpretation guard")
    return condition


def load_and_validate_pilot(
    protocol_path: Path,
    condition_paths: Sequence[Path],
) -> tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
    """Load the frozen protocol and exactly one overlay for each condition."""

    protocol = load_yaml_mapping(protocol_path)
    validate_protocol(protocol)
    conditions: Dict[str, Dict[str, Any]] = {}
    for path in condition_paths:
        overlay = load_yaml_mapping(path)
        condition = validate_condition_overlay(overlay)
        if condition in conditions:
            raise ValueError(f"duplicate pilot condition overlay: {condition}")
        conditions[condition] = overlay
    if set(conditions) != set(CONDITION_CONTRACTS):
        raise ValueError("pilot requires task-only, native-cost, and gold-STL overlays")
    return protocol, conditions


def compose_omnisafe_config(
    protocol: Mapping[str, Any],
    overlay: Mapping[str, Any],
    *,
    seed: int,
    log_dir: Path,
    overrides: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    """Compose one exact OmniSafe config, optionally applying sanity-only scale overrides."""

    validate_protocol(protocol)
    validate_condition_overlay(overlay)
    omnisafe_cfg = copy.deepcopy(dict(protocol["omnisafe"]))
    custom = {
        "seed": int(seed),
        "train_cfgs": omnisafe_cfg["train_cfgs"],
        "algo_cfgs": omnisafe_cfg["algo_cfgs"],
        "logger_cfgs": {**omnisafe_cfg["logger_cfgs"], "log_dir": str(log_dir)},
        "model_cfgs": omnisafe_cfg["model_cfgs"],
        "lagrange_cfgs": {
            **omnisafe_cfg["lagrange_cfgs_shared"],
            "cost_limit": float(overlay["lagrange_cost_limit"]),
        },
        "env_cfgs": omnisafe_cfg["env_cfgs"],
    }
    if overrides:
        custom["train_cfgs"]["total_steps"] = int(overrides["total_steps"])
        custom["train_cfgs"]["vector_env_nums"] = int(overrides["vector_env_nums"])
        custom["algo_cfgs"]["steps_per_epoch"] = int(overrides["steps_per_epoch"])
        custom["algo_cfgs"]["update_iters"] = int(overrides["update_iters"])
        custom["algo_cfgs"]["batch_size"] = int(overrides["batch_size"])
        custom["logger_cfgs"]["save_model_freq"] = int(overrides["save_model_freq"])
    return {
        "algorithm": str(omnisafe_cfg["algorithm"]),
        "environment_id": str(overlay["environment_id"]),
        "condition": str(overlay["condition"]),
        "custom_cfgs": custom,
    }


__all__ = [
    "CONDITION_CONTRACTS",
    "PILOT_PROTOCOL_ID",
    "compose_omnisafe_config",
    "load_and_validate_pilot",
    "load_yaml_mapping",
    "validate_condition_overlay",
    "validate_protocol",
]
