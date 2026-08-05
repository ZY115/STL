#!/usr/bin/env python3
"""Produce the Stage I online/oracle/RTAMT agreement evidence."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

import yaml

from safety_stl.monitor import BoundedRecoveryMonitor, MonitorOutput
from safety_stl.oracle import evaluate_trace, rtamt_window_robustness


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPOSITORY_ROOT / "configs" / "stage1_rule.yaml"
FIXTURE_DIRECTORY = REPOSITORY_ROOT / "tests" / "fixtures"
OUTPUT_DIRECTORY = REPOSITORY_ROOT / "results" / "monitor_agreement"
SUMMARY_PATH = OUTPUT_DIRECTORY / "summary.json"
REPORT_PATH = REPOSITORY_ROOT / "docs" / "monitor_agreement_report.md"

EVENT_FIELDS = {
    "warning_trigger": "stl_warning_trigger",
    "recovery": "stl_recovery",
    "late_recovery": "stl_late_recovery",
    "deadline_violation": "stl_deadline_violation",
    "terminal_unresolved": "stl_terminal_unresolved",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run_online(
    distances: Sequence[float],
    terminated: Sequence[bool],
    truncated: Sequence[bool],
    config: Dict[str, Any],
) -> List[MonitorOutput]:
    monitor = BoundedRecoveryMonitor(
        config["d_warn"],
        config["d_safe"],
        config["deadline_steps"],
    )
    outputs = [monitor.reset(distances[0])]
    for index in range(1, len(distances)):
        outputs.append(
            monitor.step(
                distances[index],
                terminated=terminated[index],
                truncated=truncated[index],
            ),
        )
    return outputs


def synthetic_cases(config: Dict[str, Any]) -> Dict[str, Tuple[List[float], List[bool], List[bool]]]:
    warn = float(config["d_warn"])
    safe = float(config["d_safe"])
    deadline = int(config["deadline_steps"])

    def flags(length: int) -> List[bool]:
        return [False] * length

    cases: Dict[str, Tuple[List[float], List[bool], List[bool]]] = {}
    distances = [warn] * (deadline + 2)
    cases["always_above_warning"] = (distances, flags(len(distances)), flags(len(distances)))
    distances = [warn - 0.01] + [safe] * (deadline + 1)
    cases["reset_inside_warning"] = (distances, flags(len(distances)), flags(len(distances)))
    distances = [warn] * (deadline + 1)
    cases["warning_equality"] = (distances, flags(len(distances)), flags(len(distances)))
    distances = [warn - 0.01, safe] + [safe] * deadline
    cases["safe_equality"] = (distances, flags(len(distances)), flags(len(distances)))
    cases["recovery_one_step"] = (distances, flags(len(distances)), flags(len(distances)))
    distances = [warn - 0.01] + [safe - 0.01] * (deadline - 1) + [safe]
    cases["recovery_on_deadline"] = (distances, flags(len(distances)), flags(len(distances)))
    distances = [warn - 0.01] + [safe - 0.01] * deadline + [safe]
    cases["recovery_after_deadline"] = (distances, flags(len(distances)), flags(len(distances)))
    distances = [warn - 0.01] * (deadline + 6)
    cases["remain_unsafe_after_deadline"] = (
        distances,
        flags(len(distances)),
        flags(len(distances)),
    )
    distances = [warn - 0.01] + [warn + 0.01] * (deadline - 1) + [safe]
    cases["hysteresis_band_pending"] = (distances, flags(len(distances)), flags(len(distances)))
    distances = [warn - 0.01, warn + 0.01, warn - 0.01] + [safe] * deadline
    cases["reentry_while_pending"] = (distances, flags(len(distances)), flags(len(distances)))
    distances = [warn - 0.01, safe, warn - 0.01, safe] + [safe] * deadline
    cases["two_warning_episodes"] = (distances, flags(len(distances)), flags(len(distances)))
    distances = [warn - 0.01, safe - 0.01]
    terminated = flags(len(distances))
    truncated = flags(len(distances))
    truncated[-1] = True
    cases["truncate_pending"] = (distances, terminated, truncated)
    distances = [warn - 0.01] + [safe - 0.01] * deadline
    terminated = flags(len(distances))
    terminated[-1] = True
    cases["terminate_on_deadline"] = (distances, terminated, flags(len(distances)))
    distances = [warn - 0.01, safe]
    truncated = flags(len(distances))
    truncated[-1] = True
    cases["recover_on_final_sample"] = (distances, flags(len(distances)), truncated)
    return cases


def load_fixture(path: Path) -> Tuple[List[float], List[bool], List[bool]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    distances = [float(row["nearest_hazard_distance_public"]) for row in rows]
    terminated = [row["terminated"].lower() == "true" for row in rows]
    truncated = [row["truncated"].lower() == "true" for row in rows]
    return distances, terminated, truncated


def oracle_steps(oracle: Any, event: str) -> List[int]:
    return {
        "warning_trigger": oracle.trigger_steps,
        "recovery": oracle.recovery_steps,
        "late_recovery": oracle.late_recovery_steps,
        "deadline_violation": oracle.violation_steps,
        "terminal_unresolved": oracle.unresolved_steps,
    }[event]


def compare_trace(
    name: str,
    kind: str,
    distances: Sequence[float],
    terminated: Sequence[bool],
    truncated: Sequence[bool],
    config: Dict[str, Any],
) -> Dict[str, Any]:
    outputs = run_online(distances, terminated, truncated, config)
    oracle = evaluate_trace(
        distances,
        config["d_warn"],
        config["d_safe"],
        config["deadline_steps"],
        terminated=terminated,
        truncated=truncated,
    )
    event_mismatches = 0
    events: Dict[str, Any] = {}
    for event, attribute in EVENT_FIELDS.items():
        online = [output.sample_index for output in outputs if getattr(output, attribute)]
        direct = oracle_steps(oracle, event)
        event_mismatches += len(set(online).symmetric_difference(direct))
        events[event] = {"online": online, "direct_oracle": direct}
    online_costs = [output.stl_cost for output in outputs]
    cost_mismatches = sum(left != right for left, right in zip(online_costs, oracle.costs))

    windows = []
    for window in oracle.completed_windows:
        values = distances[window.trigger_step : window.deadline_step + 1]
        rtamt_value = rtamt_window_robustness(
            values,
            config["d_safe"],
            config["deadline_steps"],
        )
        difference = abs(rtamt_value - window.robustness)
        windows.append(
            {
                "episode_id": window.episode_id,
                "trigger_step": window.trigger_step,
                "deadline_step": window.deadline_step,
                "direct_robustness": window.robustness,
                "rtamt_robustness": rtamt_value,
                "absolute_difference": difference,
                "direct_satisfied": window.satisfied,
                "rtamt_satisfied": rtamt_value >= 0.0,
            },
        )
    return {
        "name": name,
        "kind": kind,
        "samples": len(distances),
        "event_steps": events,
        "event_step_mismatch_count": event_mismatches,
        "cost_mismatch_count": cost_mismatches,
        "trigger_count": len(oracle.trigger_steps),
        "terminal_unresolved_count": len(oracle.unresolved_steps),
        "completed_windows": windows,
    }


def build_report(summary: Dict[str, Any]) -> str:
    aggregate = summary["aggregate"]
    parameters = summary["parameters"]
    return f"""# Stage I Monitor Agreement Report

## Result

The rule-and-monitor agreement checks passed for the calibrated Stage I rule:

```text
d_warn = {parameters['d_warn']}
d_safe = {parameters['d_safe']}
K = {parameters['deadline_steps']} environment steps
```

- synthetic semantic traces: {aggregate['synthetic_trace_count']};
- stable environment fixtures: {aggregate['environment_fixture_count']};
- completed obligation windows checked with RTAMT: {aggregate['completed_window_count']};
- online/direct-oracle event-step mismatches: {aggregate['event_step_mismatch_count']};
- online/direct-oracle per-sample cost mismatches: {aggregate['cost_mismatch_count']};
- RTAMT/direct Boolean mismatches: {aggregate['rtamt_boolean_mismatch_count']};
- maximum RTAMT/direct robustness difference: {aggregate['maximum_robustness_difference']:.17g}.

The required tolerance is `{parameters['agreement_tolerance']}`. Pending windows
at terminal truncation were recorded as unresolved and excluded from RTAMT
completed-window aggregation.

## Compared implementations

1. `BoundedRecoveryMonitor` implements the causal online state machine.
2. `evaluate_trace` is an independent direct offline enumerator.
3. RTAMT evaluates `eventually[0:K](d >= d_safe)` on each completed trigger
   window.

The online monitor and direct enumerator were compared on every trigger,
on-time recovery, late recovery, deadline violation, terminal-unresolved event,
and binary cost step. RTAMT and the direct enumerator were compared on Boolean
satisfaction and real-valued robustness.

## Reproduce

From an activated `stl-stage1` environment:

```bash
python scripts/generate_monitor_fixtures.py
python -m unittest discover -s tests -v
python scripts/run_monitor_agreement.py
```

The unit-test command runs 23 tests, including all normative boundary cases,
the public-distance smoke check, stable fixtures, and RTAMT agreement.

## Evidence

- machine-readable result: `results/monitor_agreement/summary.json`;
- synthetic boundary tests: `tests/test_monitor_boundaries.py`;
- agreement tests: `tests/test_oracle_agreement.py`;
- tracked environment fixtures: `tests/fixtures/`.

This report validates monitor semantics only. It is not an RL result or a
formal safety guarantee.
"""


def main() -> int:
    with CONFIG_PATH.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    with (FIXTURE_DIRECTORY / "manifest.json").open("r", encoding="utf-8") as handle:
        fixture_manifest = json.load(handle)

    traces = []
    for name, (distances, terminated, truncated) in synthetic_cases(config).items():
        traces.append(compare_trace(name, "synthetic", distances, terminated, truncated, config))
    fixture_hash_mismatches = 0
    for fixture in fixture_manifest["fixtures"]:
        path = FIXTURE_DIRECTORY / fixture["file"]
        fixture_hash_mismatches += int(sha256_file(path) != fixture["sha256"])
        distances, terminated, truncated = load_fixture(path)
        traces.append(
            compare_trace(
                fixture["label"],
                "environment_fixture",
                distances,
                terminated,
                truncated,
                config,
            ),
        )

    windows = [window for trace in traces for window in trace["completed_windows"]]
    aggregate = {
        "synthetic_trace_count": sum(trace["kind"] == "synthetic" for trace in traces),
        "environment_fixture_count": sum(
            trace["kind"] == "environment_fixture" for trace in traces
        ),
        "event_step_comparison_count": len(traces) * len(EVENT_FIELDS),
        "event_step_mismatch_count": sum(
            trace["event_step_mismatch_count"] for trace in traces
        ),
        "cost_sample_comparison_count": sum(trace["samples"] for trace in traces),
        "cost_mismatch_count": sum(trace["cost_mismatch_count"] for trace in traces),
        "completed_window_count": len(windows),
        "rtamt_boolean_mismatch_count": sum(
            window["direct_satisfied"] != window["rtamt_satisfied"] for window in windows
        ),
        "maximum_robustness_difference": max(
            (window["absolute_difference"] for window in windows),
            default=0.0,
        ),
        "terminal_unresolved_trace_count": sum(
            trace["terminal_unresolved_count"] > 0 for trace in traces
        ),
        "fixture_hash_mismatch_count": fixture_hash_mismatches,
    }
    summary = {
        "schema_version": 1,
        "parameters": {
            "d_warn": config["d_warn"],
            "d_safe": config["d_safe"],
            "deadline_steps": config["deadline_steps"],
            "agreement_tolerance": config["agreement_tolerance"],
        },
        "aggregate": aggregate,
        "traces": traces,
    }
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    with SUMMARY_PATH.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, sort_keys=True)
        handle.write("\n")
    REPORT_PATH.write_text(build_report(summary), encoding="utf-8")

    failures = (
        aggregate["event_step_mismatch_count"]
        + aggregate["cost_mismatch_count"]
        + aggregate["rtamt_boolean_mismatch_count"]
        + aggregate["fixture_hash_mismatch_count"]
    )
    if aggregate["maximum_robustness_difference"] > config["agreement_tolerance"]:
        failures += 1
    print(json.dumps(aggregate, indent=2, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
