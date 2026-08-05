"""Independent offline oracle and RTAMT checks for bounded recovery."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Sequence

import math

import rtamt


@dataclass(frozen=True)
class OracleEvent:
    """Final outcome of one warning episode."""

    episode_id: int
    trigger_step: int
    deadline_step: int
    outcome: str
    outcome_step: int


@dataclass(frozen=True)
class CompletedWindow:
    """A trigger with all samples through its inclusive deadline available."""

    episode_id: int
    trigger_step: int
    deadline_step: int
    robustness: float
    satisfied: bool


@dataclass(frozen=True)
class OracleResult:
    """Trajectory-level reference result."""

    trigger_steps: List[int]
    recovery_steps: List[int]
    late_recovery_steps: List[int]
    violation_steps: List[int]
    unresolved_steps: List[int]
    costs: List[int]
    events: List[OracleEvent]
    completed_windows: List[CompletedWindow]

    def as_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["trigger_count"] = len(self.trigger_steps)
        data["recovery_count"] = len(self.recovery_steps)
        data["deadline_violation_count"] = len(self.violation_steps)
        data["unresolved_count"] = len(self.unresolved_steps)
        complete = self.completed_windows
        data["trace_robustness"] = min(w.robustness for w in complete) if complete else None
        return data


def evaluate_trace(
    distances: Sequence[float],
    d_warn: float,
    d_safe: float,
    deadline_steps: int,
    *,
    terminated: Optional[Sequence[bool]] = None,
    truncated: Optional[Sequence[bool]] = None,
) -> OracleResult:
    """Evaluate a finite trace without calling the online monitor implementation."""

    values = [float(value) for value in distances]
    if not values:
        raise ValueError("distances must contain at least the reset sample")
    if any(not math.isfinite(value) for value in values):
        raise ValueError("distances must be finite")
    if not 0.2 < d_warn < d_safe < 3.0:
        raise ValueError("thresholds must satisfy 0.2 < d_warn < d_safe < 3")
    if deadline_steps <= 0:
        raise ValueError("deadline_steps must be positive")

    terminal = list(terminated) if terminated is not None else [False] * len(values)
    trunc = list(truncated) if truncated is not None else [False] * len(values)
    if len(terminal) != len(values) or len(trunc) != len(values):
        raise ValueError("terminal flag lengths must match distances")
    if any(a and b for a, b in zip(terminal, trunc)):
        raise ValueError("a sample cannot be both terminated and truncated")
    if any(terminal[index] or trunc[index] for index in range(len(values) - 1)):
        raise ValueError("terminal flags may appear only on the final sample")

    state = "inactive"
    trigger_step: Optional[int] = None
    deadline_step: Optional[int] = None
    episode_id = 0
    trigger_steps: List[int] = []
    recovery_steps: List[int] = []
    late_recovery_steps: List[int] = []
    violation_steps: List[int] = []
    unresolved_steps: List[int] = []
    costs = [0] * len(values)
    events: List[OracleEvent] = []

    for step, distance in enumerate(values):
        unsafe = distance < d_warn
        safe = distance >= d_safe
        violation_now = False
        if state == "inactive" and unsafe:
            episode_id += 1
            trigger_step = step
            deadline_step = step + deadline_steps
            trigger_steps.append(step)
            state = "pending"
        elif state == "pending" and safe:
            recovery_steps.append(step)
            events.append(
                OracleEvent(episode_id, int(trigger_step), int(deadline_step), "recovery", step),
            )
            state = "inactive"
            trigger_step = None
            deadline_step = None
        elif state == "pending" and step == deadline_step:
            violation_steps.append(step)
            costs[step] = 1
            violation_now = True
            events.append(
                OracleEvent(
                    episode_id,
                    int(trigger_step),
                    int(deadline_step),
                    "deadline_violation",
                    step,
                ),
            )
            state = "overdue"
        elif state == "overdue" and safe:
            late_recovery_steps.append(step)
            state = "inactive"
            trigger_step = None
            deadline_step = None

        is_final_terminal = step == len(values) - 1 and (terminal[step] or trunc[step])
        if is_final_terminal and state == "pending" and not violation_now:
            unresolved_steps.append(step)
            costs[step] = 1
            events.append(
                OracleEvent(
                    episode_id,
                    int(trigger_step),
                    int(deadline_step),
                    "terminal_unresolved",
                    step,
                ),
            )

    completed_windows: List[CompletedWindow] = []
    for current_episode, start in enumerate(trigger_steps, start=1):
        deadline = start + deadline_steps
        if deadline < len(values):
            robustness = max(value - d_safe for value in values[start : deadline + 1])
            completed_windows.append(
                CompletedWindow(
                    episode_id=current_episode,
                    trigger_step=start,
                    deadline_step=deadline,
                    robustness=float(robustness),
                    satisfied=robustness >= 0.0,
                ),
            )

    return OracleResult(
        trigger_steps=trigger_steps,
        recovery_steps=recovery_steps,
        late_recovery_steps=late_recovery_steps,
        violation_steps=violation_steps,
        unresolved_steps=unresolved_steps,
        costs=costs,
        events=events,
        completed_windows=completed_windows,
    )


def rtamt_window_robustness(
    distances: Sequence[float],
    d_safe: float,
    deadline_steps: int,
) -> float:
    """Evaluate one complete trigger window with RTAMT discrete-time semantics."""

    values = [float(value) for value in distances]
    if len(values) != deadline_steps + 1:
        raise ValueError("a completed window must contain deadline_steps + 1 samples")
    specification = rtamt.StlDiscreteTimeSpecification()
    specification.name = "stage1_completed_recovery_window"
    specification.declare_var("d", "float")
    specification.spec = f"eventually[0:{deadline_steps}](d >= {d_safe:.17g})"
    specification.parse()
    evaluated = specification.evaluate({"time": list(range(len(values))), "d": values})
    if not evaluated:
        raise RuntimeError("RTAMT returned no robustness samples")
    return float(evaluated[0][1])

