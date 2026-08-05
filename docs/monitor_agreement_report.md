# Stage I Monitor Agreement Report

## Result

The rule-and-monitor agreement checks passed for the calibrated Stage I rule:

```text
d_warn = 0.45
d_safe = 0.55
K = 79 environment steps
```

- synthetic semantic traces: 14;
- stable environment fixtures: 3;
- completed obligation windows checked with RTAMT: 13;
- online/direct-oracle event-step mismatches: 0;
- online/direct-oracle per-sample cost mismatches: 0;
- RTAMT/direct Boolean mismatches: 0;
- maximum RTAMT/direct robustness difference: 0.

The required tolerance is `1e-09`. Pending windows
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
