"""Frozen C0/C1 learner-cost adapters over unchanged Gold monitor outputs."""

from __future__ import annotations

from enum import Enum

from safety_stl.monitor import MonitorOutput, MonitorState


class GoldLearnerCost(str, Enum):
    """Predeclared D38 learner-cost candidates; neither changes Gold truth."""

    C0_BINARY_EVENT = "c0_binary_event"
    C1_CAUSAL_DENSE = "c1_causal_dense"


def causal_dense_surrogate(output: MonitorOutput, d_warn: float, d_safe: float) -> float:
    """Return D38 C1 from the current public distance and causal monitor state.

    An actual missed-obligation event always emits one.  Otherwise, inactive
    obligations emit zero and pending/overdue obligations use the frozen equal
    mixture of distance deficit and deadline urgency.  This is a learner
    surrogate, not an STL truth value.
    """

    if not d_warn < d_safe:
        raise ValueError("C1 requires d_warn < d_safe")
    if output.stl_cost:
        return 1.0
    if output.stl_status == MonitorState.INACTIVE.value:
        return 0.0
    remaining = 0 if output.stl_remaining_steps is None else output.stl_remaining_steps
    if output.stl_deadline_step is None or output.stl_trigger_step is None:
        raise ValueError("active Gold output is missing its temporal bounds")
    deadline = output.stl_deadline_step - output.stl_trigger_step
    if deadline <= 0:
        raise ValueError("active Gold output has a non-positive deadline")
    q_distance = min(max((d_safe - output.stl_distance) / (d_safe - d_warn), 0.0), 1.0)
    q_urgency = min(max(1.0 - remaining / deadline, 0.0), 1.0)
    return float(min(max(0.5 * q_distance + 0.5 * q_urgency, 0.0), 1.0))


def gold_learner_cost(
    candidate: GoldLearnerCost,
    output: MonitorOutput,
    d_warn: float,
    d_safe: float,
) -> float:
    """Adapt the same monitor output to one predeclared learner-cost unit."""

    candidate = GoldLearnerCost(candidate)
    if candidate is GoldLearnerCost.C0_BINARY_EVENT:
        return float(output.stl_cost)
    return causal_dense_surrogate(output, d_warn, d_safe)


__all__ = ["GoldLearnerCost", "causal_dense_surrogate", "gold_learner_cost"]
