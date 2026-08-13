"""Direct causal Gold evaluators for the frozen D37 Stage II formula families."""

from __future__ import annotations

import math
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import rtamt

from safety_stl.monitor import BoundedRecoveryMonitor
from safety_stl.oracle import evaluate_trace, rtamt_window_robustness


TOLERANCE = 1e-9


def _rtamt_robustness(distances: Sequence[float], formula: str) -> float:
    specification = rtamt.StlDiscreteTimeSpecification()
    specification.name = "stage2_d37_completed_window"
    specification.declare_var("d", "float")
    specification.spec = formula
    specification.parse()
    values = [float(value) for value in distances]
    evaluated = specification.evaluate({"time": list(range(len(values))), "d": values})
    if not evaluated:
        raise RuntimeError("RTAMT returned no robustness samples")
    return float(evaluated[0][1])


def _validate_trace_inputs(
    distances: Sequence[float],
    terminated: Sequence[bool],
    truncated: Sequence[bool],
) -> List[float]:
    values = [float(value) for value in distances]
    if not values or len(terminated) != len(values) or len(truncated) != len(values):
        raise ValueError("distance and terminal arrays must be non-empty and equal length")
    if any(not math.isfinite(value) or value < 0.0 or value > 3.0 for value in values):
        raise ValueError("distances must be finite values in [0, 3]")
    if any(bool(a) and bool(b) for a, b in zip(terminated, truncated)):
        raise ValueError("one sample cannot be both terminated and truncated")
    if any(bool(a) or bool(b) for a, b in zip(terminated[:-1], truncated[:-1])):
        raise ValueError("terminal flags are allowed only on the final sample")
    return values


def _counts(
    *,
    trigger_steps: Sequence[int],
    recovery_steps: Sequence[int],
    late_recovery_steps: Sequence[int],
    violation_steps: Sequence[int],
    unresolved_steps: Sequence[int],
    costs: Sequence[int],
) -> Dict[str, Any]:
    return {
        "trigger_steps": list(trigger_steps),
        "recovery_steps": list(recovery_steps),
        "late_recovery_steps": list(late_recovery_steps),
        "violation_steps": list(violation_steps),
        "unresolved_steps": list(unresolved_steps),
        "costs": list(costs),
        "trigger_count": len(trigger_steps),
        "recovery_count": len(recovery_steps),
        "late_recovery_count": len(late_recovery_steps),
        "deadline_violation_count": len(violation_steps),
        "unresolved_count": len(unresolved_steps),
        "stl_event_cost_total": int(sum(costs)),
    }


def evaluate_bounded_recovery(
    distances: Sequence[float],
    terminated: Sequence[bool],
    truncated: Sequence[bool],
    *,
    d_warn: float,
    d_safe: float,
    deadline_steps: int,
) -> Dict[str, Any]:
    values = _validate_trace_inputs(distances, terminated, truncated)
    oracle = evaluate_trace(
        values,
        d_warn,
        d_safe,
        deadline_steps,
        terminated=terminated,
        truncated=truncated,
    )
    states: List[str] = []
    state = "inactive"
    deadline: Optional[int] = None
    for step, value in enumerate(values):
        if state == "inactive" and value < d_warn:
            state = "pending"
            deadline = step + deadline_steps
        elif state == "pending" and value >= d_safe:
            state = "inactive"
            deadline = None
        elif state == "pending" and step == deadline:
            state = "overdue"
        elif state == "overdue" and value >= d_safe:
            state = "inactive"
            deadline = None
        states.append(state)
    monitor = BoundedRecoveryMonitor(d_warn, d_safe, deadline_steps)
    online_rows = []
    for step, value in enumerate(values):
        if step == 0:
            output = monitor.reset(value)
        else:
            output = monitor.step(
                value,
                terminated=bool(terminated[step]),
                truncated=bool(truncated[step]),
            )
        online_rows.append(output.as_dict())
    comparisons = {
        "trigger_steps": [row["sample_index"] for row in online_rows if row["stl_warning_trigger"]],
        "recovery_steps": [row["sample_index"] for row in online_rows if row["stl_recovery"]],
        "late_recovery_steps": [row["sample_index"] for row in online_rows if row["stl_late_recovery"]],
        "violation_steps": [row["sample_index"] for row in online_rows if row["stl_deadline_violation"]],
        "unresolved_steps": [row["sample_index"] for row in online_rows if row["stl_terminal_unresolved"]],
        "costs": [int(row["stl_cost"]) for row in online_rows],
        "states": [str(row["stl_status"]) for row in online_rows],
    }
    expected = {
        "trigger_steps": oracle.trigger_steps,
        "recovery_steps": oracle.recovery_steps,
        "late_recovery_steps": oracle.late_recovery_steps,
        "violation_steps": oracle.violation_steps,
        "unresolved_steps": oracle.unresolved_steps,
        "costs": oracle.costs,
        "states": states,
    }
    if comparisons != expected:
        raise AssertionError("bounded-recovery online/direct evaluator disagreement")
    rtamt_rows = []
    for window in oracle.completed_windows:
        window_values = values[window.trigger_step : window.deadline_step + 1]
        rtamt_value = rtamt_window_robustness(window_values, d_safe, deadline_steps)
        difference = abs(float(window.robustness) - rtamt_value)
        if difference > TOLERANCE:
            raise AssertionError("bounded-recovery direct/RTAMT disagreement")
        rtamt_rows.append(
            {
                "kind": "bounded_recovery",
                "trigger_step": window.trigger_step,
                "decision_step": window.deadline_step,
                "direct_robustness": float(window.robustness),
                "rtamt_robustness": rtamt_value,
                "absolute_difference": difference,
            },
        )
    oracle_dict = oracle.as_dict()
    oracle_dict["late_recovery_count"] = len(oracle.late_recovery_steps)
    oracle_dict["stl_event_cost_total"] = int(sum(oracle.costs))
    return {
        "agreement": True,
        "oracle": oracle_dict,
        "online": {
            "trigger_steps": oracle.trigger_steps,
            "recovery_steps": oracle.recovery_steps,
            "late_recovery_steps": oracle.late_recovery_steps,
            "violation_steps": oracle.violation_steps,
            "unresolved_steps": oracle.unresolved_steps,
            "costs": oracle.costs,
            "states": states,
        },
        "rtamt_completed_windows": rtamt_rows,
        "rtamt_max_robustness_difference": max(
            (row["absolute_difference"] for row in rtamt_rows),
            default=0.0,
        ),
    }


def evaluate_recovery_persistence(
    distances: Sequence[float],
    terminated: Sequence[bool],
    truncated: Sequence[bool],
    *,
    d_warn: float,
    d_safe: float,
    deadline_steps: int,
    persistence_steps: int,
) -> Dict[str, Any]:
    """Evaluate F[0,K]G[0,H] recovery using causal completion events."""

    values = _validate_trace_inputs(distances, terminated, truncated)
    trigger_steps: List[int] = []
    recovery_steps: List[int] = []
    late_recovery_steps: List[int] = []
    violation_steps: List[int] = []
    unresolved_steps: List[int] = []
    costs = [0] * len(values)
    states: List[str] = []
    active_trigger: Optional[int] = None
    overdue = False
    safe_run_start: Optional[int] = None

    for step, value in enumerate(values):
        if active_trigger is None and value < d_warn:
            active_trigger = step
            overdue = False
            safe_run_start = None
            trigger_steps.append(step)
        if active_trigger is not None:
            if value >= d_safe:
                if safe_run_start is None:
                    safe_run_start = step
            else:
                safe_run_start = None
            persistent = (
                safe_run_start is not None
                and step - safe_run_start >= persistence_steps
            )
            if persistent:
                if safe_run_start <= active_trigger + deadline_steps:
                    recovery_steps.append(step)
                else:
                    late_recovery_steps.append(step)
                active_trigger = None
                overdue = False
                safe_run_start = None
            elif not overdue and step == active_trigger + deadline_steps + persistence_steps:
                violation_steps.append(step)
                costs[step] = 1
                overdue = True
        terminal = bool(terminated[step]) or bool(truncated[step])
        if terminal and active_trigger is not None and not overdue:
            unresolved_steps.append(step)
            costs[step] = 1
            active_trigger = None
            safe_run_start = None
        states.append("overdue" if overdue else "pending" if active_trigger is not None else "inactive")

    rtamt_rows = []
    complete_horizon = deadline_steps + persistence_steps
    for trigger in trigger_steps:
        decision = trigger + complete_horizon
        if decision >= len(values):
            continue
        window = values[trigger : decision + 1]
        direct_value = max(
            min(window[start + offset] - d_safe for offset in range(persistence_steps + 1))
            for start in range(deadline_steps + 1)
        )
        formula = (
            f"eventually[0:{deadline_steps}]"
            f"(always[0:{persistence_steps}](d >= {d_safe:.17g}))"
        )
        rtamt_value = _rtamt_robustness(window, formula)
        difference = abs(direct_value - rtamt_value)
        if difference > TOLERANCE:
            raise AssertionError("recovery-persistence direct/RTAMT disagreement")
        rtamt_rows.append(
            {
                "kind": "recovery_plus_persistence",
                "trigger_step": trigger,
                "decision_step": decision,
                "direct_robustness": direct_value,
                "rtamt_robustness": rtamt_value,
                "absolute_difference": difference,
            },
        )
    oracle = _counts(
        trigger_steps=trigger_steps,
        recovery_steps=recovery_steps,
        late_recovery_steps=late_recovery_steps,
        violation_steps=violation_steps,
        unresolved_steps=unresolved_steps,
        costs=costs,
    )
    return {
        "agreement": True,
        "oracle": oracle,
        "online": {**oracle, "states": states},
        "rtamt_completed_windows": rtamt_rows,
        "rtamt_max_robustness_difference": max(
            (row["absolute_difference"] for row in rtamt_rows),
            default=0.0,
        ),
    }


def evaluate_bounded_avoidance(
    distances: Sequence[float],
    terminated: Sequence[bool],
    truncated: Sequence[bool],
    *,
    avoidance_threshold: float,
    avoidance_horizon_steps: int,
) -> Dict[str, Any]:
    """Evaluate the episode-start-anchored inclusive G[0,H] predicate."""

    values = _validate_trace_inputs(distances, terminated, truncated)
    costs = [0] * len(values)
    violation_steps: List[int] = []
    unresolved_steps: List[int] = []
    states: List[str] = []
    failed = False
    resolved = False
    for step, value in enumerate(values):
        if not failed and not resolved and step <= avoidance_horizon_steps:
            if value < avoidance_threshold:
                failed = True
                violation_steps.append(step)
                costs[step] = 1
            elif step == avoidance_horizon_steps:
                resolved = True
        terminal = bool(terminated[step]) or bool(truncated[step])
        if terminal and not failed and not resolved:
            unresolved_steps.append(step)
            costs[step] = 1
            failed = True
        states.append("violated" if failed else "satisfied" if resolved else "pending")
    rtamt_rows = []
    if avoidance_horizon_steps < len(values):
        window = values[: avoidance_horizon_steps + 1]
        direct_value = min(value - avoidance_threshold for value in window)
        rtamt_value = _rtamt_robustness(
            window,
            f"always[0:{avoidance_horizon_steps}](d >= {avoidance_threshold:.17g})",
        )
        difference = abs(direct_value - rtamt_value)
        if difference > TOLERANCE:
            raise AssertionError("bounded-avoidance direct/RTAMT disagreement")
        rtamt_rows.append(
            {
                "kind": "bounded_avoidance",
                "trigger_step": 0,
                "decision_step": avoidance_horizon_steps,
                "direct_robustness": direct_value,
                "rtamt_robustness": rtamt_value,
                "absolute_difference": difference,
            },
        )
    oracle = _counts(
        trigger_steps=[0],
        recovery_steps=[avoidance_horizon_steps] if resolved else [],
        late_recovery_steps=[],
        violation_steps=violation_steps,
        unresolved_steps=unresolved_steps,
        costs=costs,
    )
    return {
        "agreement": True,
        "oracle": oracle,
        "online": {**oracle, "states": states},
        "rtamt_completed_windows": rtamt_rows,
        "rtamt_max_robustness_difference": max(
            (row["absolute_difference"] for row in rtamt_rows),
            default=0.0,
        ),
    }


def _composite_result(
    operator: str,
    left: Mapping[str, Any],
    right: Mapping[str, Any],
) -> Dict[str, Any]:
    left_costs = [int(value) for value in left["oracle"]["costs"]]
    right_costs = [int(value) for value in right["oracle"]["costs"]]
    if len(left_costs) != len(right_costs):
        raise ValueError("Boolean child traces differ in length")
    left_events = [index for index, value in enumerate(left_costs) if value]
    right_events = [index for index, value in enumerate(right_costs) if value]
    if operator == "and":
        event_steps = sorted({*left_events, *right_events})[:1]
    elif operator == "or":
        event_steps = [max(left_events[0], right_events[0])] if left_events and right_events else []
    else:
        raise ValueError(f"invalid Boolean operator: {operator}")
    costs = [int(step in event_steps) for step in range(len(left_costs))]
    left_unresolved = set(left["oracle"].get("unresolved_steps", []))
    right_unresolved = set(right["oracle"].get("unresolved_steps", []))
    unresolved_steps = [
        step for step in event_steps if step in left_unresolved or step in right_unresolved
    ]
    violation_steps = [step for step in event_steps if step not in unresolved_steps]
    trigger_steps = sorted(
        {
            *[int(step) for step in left["oracle"].get("trigger_steps", [])],
            *[int(step) for step in right["oracle"].get("trigger_steps", [])],
        },
    )
    states = [
        (
            "violated"
            if any(event <= step for event in event_steps)
            else f"{operator}:{left['online']['states'][step]}:{right['online']['states'][step]}"
        )
        for step in range(len(costs))
    ]
    rtamt_rows = [*left["rtamt_completed_windows"], *right["rtamt_completed_windows"]]
    oracle = _counts(
        trigger_steps=trigger_steps,
        recovery_steps=[],
        late_recovery_steps=[],
        violation_steps=violation_steps,
        unresolved_steps=unresolved_steps,
        costs=costs,
    )
    return {
        "agreement": True,
        "oracle": oracle,
        "online": {**oracle, "states": states},
        "rtamt_completed_windows": rtamt_rows,
        "rtamt_max_robustness_difference": max(
            float(left["rtamt_max_robustness_difference"]),
            float(right["rtamt_max_robustness_difference"]),
        ),
        "boolean_child_event_steps": {
            "left": left_events,
            "right": right_events,
            "operator": operator,
        },
    }


def evaluate_specification_trace(
    specification: Mapping[str, Any],
    distances: Sequence[float],
    terminated: Sequence[bool],
    truncated: Sequence[bool],
) -> Dict[str, Any]:
    """Dispatch one trace to the direct evaluator for its frozen family."""

    family = str(specification["formula_family"])
    parameters = specification["parameter_values"]
    if family == "hysteretic_bounded_recovery":
        return evaluate_bounded_recovery(
            distances,
            terminated,
            truncated,
            d_warn=float(parameters["d_warn"]),
            d_safe=float(parameters["d_safe"]),
            deadline_steps=int(parameters["deadline_steps"]),
        )
    if family == "recovery_plus_persistence":
        return evaluate_recovery_persistence(
            distances,
            terminated,
            truncated,
            d_warn=float(parameters["d_warn"]),
            d_safe=float(parameters["d_safe"]),
            deadline_steps=int(parameters["deadline_steps"]),
            persistence_steps=int(parameters["persistence_steps"]),
        )
    if family == "bounded_avoidance":
        return evaluate_bounded_avoidance(
            distances,
            terminated,
            truncated,
            avoidance_threshold=float(parameters["avoidance_threshold"]),
            avoidance_horizon_steps=int(parameters["avoidance_horizon_steps"]),
        )
    if family in {"conjunction", "disjunction"}:
        recovery = evaluate_bounded_recovery(
            distances,
            terminated,
            truncated,
            d_warn=float(parameters["d_warn"]),
            d_safe=float(parameters["d_safe"]),
            deadline_steps=int(parameters["deadline_steps"]),
        )
        avoidance = evaluate_bounded_avoidance(
            distances,
            terminated,
            truncated,
            avoidance_threshold=float(parameters["avoidance_threshold"]),
            avoidance_horizon_steps=int(parameters["avoidance_horizon_steps"]),
        )
        return _composite_result(
            "and" if family == "conjunction" else "or",
            recovery,
            avoidance,
        )
    raise ValueError(f"unsupported Stage II formula family: {family}")


__all__ = [
    "evaluate_bounded_avoidance",
    "evaluate_bounded_recovery",
    "evaluate_recovery_persistence",
    "evaluate_specification_trace",
]
