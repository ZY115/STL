"""Causal online monitor for the fixed Stage I bounded-recovery rule."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict, Optional

import math


class MonitorState(str, Enum):
    """State of one environment's warning episode."""

    INACTIVE = "inactive"
    PENDING = "pending"
    OVERDUE = "overdue"


@dataclass(frozen=True)
class MonitorOutput:
    """Per-sample output contract from the normative specification."""

    sample_index: int
    stl_distance: float
    stl_unsafe: bool
    stl_safe: bool
    stl_status: str
    stl_warning_trigger: bool
    stl_recovery: bool
    stl_late_recovery: bool
    stl_deadline_violation: bool
    stl_terminal_unresolved: bool
    stl_trigger_step: Optional[int]
    stl_deadline_step: Optional[int]
    stl_elapsed_steps: Optional[int]
    stl_remaining_steps: Optional[int]
    stl_cost: int
    stl_episode_id: int
    terminated: bool
    truncated: bool

    def as_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable dictionary."""

        return asdict(self)


class BoundedRecoveryMonitor:
    """One-obligation hysteretic monitor with an inclusive deadline."""

    def __init__(self, d_warn: float, d_safe: float, deadline_steps: int) -> None:
        if not math.isfinite(d_warn) or not math.isfinite(d_safe):
            raise ValueError("distance thresholds must be finite")
        if not 0.2 < d_warn < d_safe < 3.0:
            raise ValueError("thresholds must satisfy 0.2 < d_warn < d_safe < 3")
        if isinstance(deadline_steps, bool) or not isinstance(deadline_steps, int):
            raise TypeError("deadline_steps must be an integer")
        if deadline_steps <= 0:
            raise ValueError("deadline_steps must be positive")

        self.d_warn = float(d_warn)
        self.d_safe = float(d_safe)
        self.deadline_steps = deadline_steps
        self._initialized = False
        self._episode_ended = False
        self._clear_runtime()

    def _clear_runtime(self) -> None:
        self.state = MonitorState.INACTIVE
        self.sample_index = -1
        self.trigger_step: Optional[int] = None
        self.deadline_step: Optional[int] = None
        self.previous_unsafe = False
        self.trigger_count = 0
        self.recovery_count = 0
        self.deadline_violation_count = 0
        self.unresolved_count = 0
        self.episode_id = 0

    def reset(self, distance: float) -> MonitorOutput:
        """Clear all state and process the reset observation as sample ``t=0``."""

        self._clear_runtime()
        self._initialized = True
        self._episode_ended = False
        return self._process(distance, terminated=False, truncated=False)

    def step(
        self,
        distance: float,
        *,
        terminated: bool = False,
        truncated: bool = False,
    ) -> MonitorOutput:
        """Process the next public distance sample and optional terminal flags."""

        if not self._initialized:
            raise RuntimeError("reset(distance) must be called before step(distance)")
        if self._episode_ended:
            raise RuntimeError("the episode has ended; call reset(distance) before another step")
        if terminated and truncated:
            raise ValueError("a sample cannot be both terminated and truncated")
        return self._process(distance, terminated=terminated, truncated=truncated)

    def _process(self, distance: float, *, terminated: bool, truncated: bool) -> MonitorOutput:
        if not math.isfinite(distance):
            raise ValueError("distance must be finite")

        self.sample_index += 1
        unsafe = distance < self.d_warn
        safe = distance >= self.d_safe
        warning_trigger = False
        recovery = False
        late_recovery = False
        deadline_violation = False
        terminal_unresolved = False
        closed_trigger_step: Optional[int] = None
        closed_deadline_step: Optional[int] = None

        if self.state is MonitorState.INACTIVE:
            if unsafe:
                warning_trigger = True
                self.trigger_count += 1
                self.episode_id += 1
                self.trigger_step = self.sample_index
                self.deadline_step = self.sample_index + self.deadline_steps
                self.state = MonitorState.PENDING
        elif self.state is MonitorState.PENDING:
            if safe:
                recovery = True
                self.recovery_count += 1
                closed_trigger_step = self.trigger_step
                closed_deadline_step = self.deadline_step
                self.state = MonitorState.INACTIVE
                self.trigger_step = None
                self.deadline_step = None
            elif self.sample_index == self.deadline_step:
                deadline_violation = True
                self.deadline_violation_count += 1
                self.state = MonitorState.OVERDUE
            elif self.sample_index > self.deadline_step:
                raise AssertionError("pending monitor advanced past its deadline")
        elif self.state is MonitorState.OVERDUE:
            if safe:
                late_recovery = True
                closed_trigger_step = self.trigger_step
                closed_deadline_step = self.deadline_step
                self.state = MonitorState.INACTIVE
                self.trigger_step = None
                self.deadline_step = None
        else:  # pragma: no cover - Enum exhaustiveness guard
            raise AssertionError(f"unknown monitor state {self.state}")

        if (terminated or truncated) and self.state is MonitorState.PENDING:
            terminal_unresolved = True
            self.unresolved_count += 1

        stl_cost = int(deadline_violation or terminal_unresolved)
        active_trigger = self.trigger_step
        active_deadline = self.deadline_step
        output_trigger = active_trigger if active_trigger is not None else closed_trigger_step
        output_deadline = active_deadline if active_deadline is not None else closed_deadline_step
        if self.state in (MonitorState.PENDING, MonitorState.OVERDUE):
            elapsed = self.sample_index - int(self.trigger_step)
            remaining = max(int(self.deadline_step) - self.sample_index, 0)
        else:
            elapsed = None
            remaining = None

        output = MonitorOutput(
            sample_index=self.sample_index,
            stl_distance=float(distance),
            stl_unsafe=unsafe,
            stl_safe=safe,
            stl_status=self.state.value,
            stl_warning_trigger=warning_trigger,
            stl_recovery=recovery,
            stl_late_recovery=late_recovery,
            stl_deadline_violation=deadline_violation,
            stl_terminal_unresolved=terminal_unresolved,
            stl_trigger_step=output_trigger,
            stl_deadline_step=output_deadline,
            stl_elapsed_steps=elapsed,
            stl_remaining_steps=remaining,
            stl_cost=stl_cost,
            stl_episode_id=self.episode_id,
            terminated=bool(terminated),
            truncated=bool(truncated),
        )
        self.previous_unsafe = unsafe
        if terminated or truncated:
            self._episode_ended = True
        return output

    def policy_state(self) -> tuple:
        """Return ``(active, overdue, remaining_fraction)`` after the latest sample."""

        active = float(self.state in (MonitorState.PENDING, MonitorState.OVERDUE))
        overdue = float(self.state is MonitorState.OVERDUE)
        if self.state is MonitorState.PENDING:
            remaining = max(int(self.deadline_step) - self.sample_index, 0)
            remaining_fraction = remaining / self.deadline_steps
        else:
            remaining_fraction = 0.0
        return active, overdue, float(remaining_fraction)

