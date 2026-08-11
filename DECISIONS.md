# Decision Log

This file distinguishes fixed decisions, open decisions, and deferred questions. It should be updated whenever the project scope or experiment definition changes.

## Confirmed decisions

### D1. The research remains an NL-to-STL-to-Safe-RL project

The long-term objective has not changed. The current experiment is a controlled prerequisite, not a replacement research problem.

### D2. The task objective and safety requirement are separated

The benchmark's native reward represents goal reaching. STL is initially used to express and evaluate the safety requirement.

The entire natural-language task does not need to become a single STL formula in Stage I.

### D3. STL is not passed directly to RL as text

An STL monitor evaluates trajectory signals. Its output is converted into a safety cost that a Safe RL algorithm can consume.

### D4. The complete study is divided into three stages

- Stage I: manual gold STL;
- Stage II: controlled language with explicit parameters;
- Stage III: broader language and environments.

This order isolates independent failure sources.

### D5. Stage I uses `SafetyPointGoal1-v0`

The environment provides a simple point-navigation task, hazards, a native cost, and compatibility with existing Safe RL tooling.

It is selected to minimize unrelated perception and simulator engineering in the first experiment.

### D6. Stage I uses one temporal rule

The rule is bounded recovery over a derived warning-episode event:

```text
G(e_t -> F_[0,K](d_t >= d_safe))
```

`e_t` is true when the monitor is inactive and the distance first becomes
smaller than `d_warn`. A warning episode remains active until the distance
reaches `d_safe`; oscillation in between does not create overlapping
obligations.

The earlier pointwise formula is only an intuitive shorthand. Its literal
semantics would create an obligation at every unsafe sample, which is not the
fixed Stage I experiment.

Using one event-triggered rule keeps monitor semantics and behavioral
interpretation inspectable.

### D7. The initial Safe RL implementation uses OmniSafe

PPO-Lagrangian is the initial constrained algorithm. The project will reuse an established optimizer rather than implement Safe RL from scratch.

### D8. RTAMT is the reference monitor

RTAMT is intended for offline or reference evaluation of saved trajectories. A small custom stateful monitor may be used online if necessary, but it must agree with the reference monitor on declared test cases.

### D9. Stage I is empirical, not a zero-violation guarantee

The STL rule defines the desired temporal condition. A cost-based Safe RL learner may still violate that condition during training or evaluation.

### D10. The repository remained documentation-first until environment inspection

No experiment directories were created before the Ubuntu environment and available signals were inspected.

The inspection is complete. The later normative specification defined and the
rule-and-monitor milestone created the limited source, test, configuration,
script, fixture, and evidence directories. Wrapper and training surfaces remain
deferred to the next work package.

### D11. Stage I distance uses the public hazard pseudo-lidar

For Stage I:

```text
d_t = 3 * (1 - max(hazards_lidar))
```

This is the nearest agent-origin-to-hazard-center distance capped at the default
pseudo-lidar range of 3 simulator length units.

Rationale:

- `hazards_lidar` is part of the public policy observation;
- the reconstruction agreed with privileged simulator center distance to
  floating-point precision on 3500 collected steps;
- center distance aligns directly with the benchmark's native hazard-distance
  calculation;
- no privileged simulator state is required by the monitor.

Expected impact:

- later thresholds must satisfy `d_warn < d_safe < 3`;
- `d_t` must not be described as physical boundary-to-boundary clearance;
- simulator positions remain available only as a validation diagnostic.

### D12. Equality and deadline semantics are fixed

- `d_t == d_warn` is not warning;
- `d_t == d_safe` is recovery;
- a deadline at `t_0 + K` is inclusive;
- recovery on the deadline sample succeeds;
- recovery one sample later is late;
- predicate comparisons do not use an epsilon.

A tolerance of `1e-9` is used only to compare independently computed
real-valued robustness values.

### D13. The monitor uses one hysteretic warning episode

Each environment has one of three monitor states:

- `INACTIVE`;
- `PENDING`;
- `OVERDUE`.

A warning episode begins only from `INACTIVE`, remains active through the band
between `d_warn` and `d_safe`, and closes only at `d_t >= d_safe`. Missing the
deadline emits one violation event and moves the episode to `OVERDUE`; it does
not emit a new violation on every later step.

### D14. Unfinished terminal obligations are explicit

If an episode terminates or truncates before a pending deadline, the result is
reported as `terminal_unresolved`, not silently satisfied or retroactively
called a completed deadline violation.

For training, this unresolved event receives one conservative binary cost so
that ending the episode cannot erase an active obligation. A deadline violation
already emitted on the final sample is not counted again.

### D15. The first STL cost is a sparse binary event cost

`stl_cost` is 1 only when:

- a recovery deadline is missed; or
- a pending obligation becomes terminal-unresolved.

It is 0 on warning entry, ordinary pending steps, recovery, and overdue steps
after the first violation. Robustness is diagnostic only in the first
implementation.

### D16. Temporal monitor state is added to every policy condition

The wrapper will append:

- active-obligation indicator;
- overdue indicator;
- normalized remaining deadline.

Task-only, native-cost, and STL-cost conditions receive the same augmented
observation. This avoids both hidden temporal state and an observation advantage
for only one condition.

### D17. Incomplete traces do not inherit undocumented library semantics

The custom online monitor is checked against a direct offline enumerator.
RTAMT is used on completed obligation windows. Pending terminal windows are
classified explicitly as unresolved rather than relying on a monitor library's
finite-trace default.

### D18. Rule semantics are frozen before numerical calibration

`docs/stage1_rule_monitor_spec.md` is the normative rule and monitor contract.
The Ubuntu machine must supply calibration evidence for `d_warn`, `d_safe`, and
`K`, but no further semantic choice is required before implementing synthetic
tests.

### D19. Stage I numerical rule parameters are calibrated

The formal 2026-08-05 run selected:

```text
d_warn = 0.45
d_safe = 0.55
K = 79 environment steps
```

All 30 controlled trials produced valid recoveries. The selected recovery-time
Q95 was 63 steps, so the predeclared equation produced
`ceil(1.25 * 63) = 79`. Its random-policy trigger rate was 17/30 (56.67%), the
eligible primary-grid rate closest to 50%.

### D20. The rule-and-monitor completion gate passed

The online monitor, independent direct oracle, stable environment fixtures, and
RTAMT completed-window checks passed with zero event-step, Boolean, cost, or
robustness mismatches. The next work package may implement the OmniSafe wrapper,
but this result is not an RL result or safety guarantee.

### D21. The OmniSafe wrapper and integration-smoke gate passed

The three registered conditions are:

```text
Stage1SafetyPointGoal1TaskOnly-v0
Stage1SafetyPointGoal1NativeCost-v0
Stage1SafetyPointGoal1STLCost-v0
```

Every condition receives the same original 60-dimensional observation plus
`active`, `overdue`, and normalized remaining-deadline state. The environment
always logs native cost, STL cost, and selected algorithm cost separately; only
the selected cost returned to OmniSafe differs.

Terminal vector transitions are evaluated from `final_observation` before the
corresponding monitor is reset from the auto-reset observation. Eleven new
wrapper tests passed. A real positive-cost probe and a 64-transition,
single-epoch PPO-Lagrangian CPU update passed on 2026-08-10. This closes the
interface milestone but is not a main training result or safety guarantee.

## Open decisions

### O6. Quantitative success criterion

Before the main training study, predeclare:

- required reduction in bounded-recovery violation rate;
- acceptable loss in goal success or return;
- number of seeds;
- evaluation episode count;
- uncertainty reporting.

## Deferred to Stage II

- controlled natural-language command format;
- language-to-STL model choice;
- translation accuracy metric;
- atomic proposition and parameter grounding;
- handling syntactically valid but semantically wrong formulas;
- separating translation error from downstream control error.

## Deferred to Stage III or later

- vague or missing numerical safety requirements;
- automatic requirement completion;
- perception uncertainty;
- dynamic obstacles;
- multiple agents;
- UAV applications;
- MILP formula repair;
- shielding and runtime intervention;
- counterexample feedback to the language model;
- formal guarantees and real-robot deployment.
