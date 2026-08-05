# Stage I Bounded-Recovery Rule and Monitor Specification

## Document status

- **Status:** normative Stage I specification
- **Version:** 1.1 (calibration result and completion status added; semantics unchanged)
- **Implementation status:** completion gate passed on 2026-08-05
- **Scope:** rule calibration, online monitoring, offline checking, and the
  STL-cost contract
- **Not in scope:** Safe RL training, natural-language translation, robustness
  shaping, shielding, or formal guarantees

This document separates decisions that require new Ubuntu-machine data from
decisions that can be fixed before those data are available. It is the
authoritative specification for the next Stage I milestone. If a later
implementation conflicts with this document, either the implementation must be
corrected or the change must first be justified in `DECISIONS.md`.

---

## 1. What is blocked and what is not

The current repository does not contain the raw environment-inspection CSV
trajectories or the scripts that generated them. The summary statistics are
useful evidence, but they are not sufficient to select a defensible recovery
deadline. This creates two data-dependent tasks, but it does not block the
formal rule or monitor design.

| Item | Current status | Where it must be completed | Does it block monitor design? |
|---|---|---|---|
| A. Parameter-calibration trajectories | Completed; summary/hashes tracked | Ubuntu work computer | No |
| B. Reproducible collection scripts and stable fixtures | Completed and tracked | Ubuntu work computer | No |
| C. Exact rule and temporal boundary semantics | Fixed in this document | Repository documentation | No |
| D. Monitor state, outputs, cost, and test contract | Fixed in this document | Repository documentation | No |

Item A selected \(d_{\mathrm{warn}}=0.45\), \(d_{\mathrm{safe}}=0.55\), and
\(K=79\) environment steps. Every semantic choice needed to implement and test
the monitor is fixed below.

---

## 2. Fixed signal and parameter domain

At environment step \(t\), the safety signal is

\[
d_t = 3\left(1-\max(\mathrm{hazards\_lidar}_t)\right).
\]

It is the public-observation estimate of the nearest
agent-origin-to-hazard-center distance, capped at 3 simulator length units.
Privileged simulator geometry may be used only to validate a data-collection
script; it must not be the deployed monitor input.

The final parameters must satisfy

\[
0.2 < d_{\mathrm{warn}} < d_{\mathrm{safe}} < 3,
\qquad
K \in \mathbb{N}^{+}.
\]

The calibrated Stage I values are:

\[
d_{\mathrm{warn}}=0.45,
\qquad
d_{\mathrm{safe}}=0.55,
\qquad
K=79.
\]

The lower reference value 0.2 is the inspected hazard size used by the
benchmark. Requiring \(d_{\mathrm{warn}}>0.2\) makes the STL warning occur
before the native hazard region. Requiring
\(d_{\mathrm{safe}}>d_{\mathrm{warn}}\) creates hysteresis and prevents the
same threshold from representing both danger and recovery.

\(K\) is measured in **environment steps**, not seconds. No conversion to
physical time is claimed in Stage I.

---

## 3. Exact safety requirement

### 3.1 Predicates

Define

\[
u_t := [d_t < d_{\mathrm{warn}}],
\qquad
s_t := [d_t \ge d_{\mathrm{safe}}].
\]

The equality semantics are therefore fixed:

- \(d_t=d_{\mathrm{warn}}\) is **not** inside the warning zone;
- \(d_t=d_{\mathrm{safe}}\) **does** count as recovery.

These comparisons use the reconstructed public distance directly. An epsilon
must not be added to either predicate, because doing so would silently change
the rule. Numerical tolerance is used only when comparing independently
computed real-valued robustness results.

### 3.2 Warning episodes

Stage I evaluates **warning episodes**, not a new obligation at every unsafe
sample.

A warning episode begins when:

1. no previous warning episode is active; and
2. \(d_t < d_{\mathrm{warn}}\).

It ends only when \(d_t \ge d_{\mathrm{safe}}\). Movement in the hysteresis
band

\[
d_{\mathrm{warn}} \le d_t < d_{\mathrm{safe}}
\]

does not end the episode and does not create a new episode.

If an episode begins with the initial reset observation already satisfying
\(d_0<d_{\mathrm{warn}}\), the trigger time is \(t_0=0\).

Let \(q_{t^-}\) be the monitor state immediately before sample \(t\) is
processed. The causal event signal is

\[
e_t := [q_{t^-}=\mathrm{INACTIVE}] \land u_t.
\]

The normative Stage I requirement is

\[
\varphi_{\mathrm{BR}}
=
\mathbf{G}\left(
e_t \rightarrow
\mathbf{F}_{[0,K]} s_t
\right).
\]

In words:

> Whenever a new warning episode begins, the agent must reach the safe
> distance no later than \(K\) environment steps after that trigger.

The earlier expression

\[
\mathbf{G}\left(
d_t<d_{\mathrm{warn}}
\rightarrow
\mathbf{F}_{[0,K]}(d_t\ge d_{\mathrm{safe}})
\right)
\]

is retained only as an intuitive shorthand in older materials. Under literal
pointwise STL semantics, it creates a new future obligation at every unsafe
sample. That behavior is not the Stage I experiment defined here. The derived
event signal \(e_t\) makes the intended entry-triggered semantics explicit and
keeps one inspectable obligation per warning episode.

This is STL over a causally derived event proposition, with a small hysteretic
event detector in front of the future-time formula. It must not be described as
pure distance-only pointwise STL. The event detector is part of the grounding
and monitoring contract.

### 3.3 Deadline indexing

If an episode begins at \(t_0\), recovery is successful when there exists a
sample

\[
j \in \{t_0,t_0+1,\ldots,t_0+K\}
\]

such that \(d_j\ge d_{\mathrm{safe}}\).

The deadline is inclusive. The monitor must evaluate the sample at
\(t_0+K\) before declaring a deadline violation. Recovery at exactly
\(t_0+K\) succeeds; first recovery at \(t_0+K+1\) is late.

---

## 4. Online monitor state machine

Each environment instance owns an independent monitor. Its state is reset on
every environment reset and must never be shared across vectorized
environments.

### 4.1 States

| State | Meaning |
|---|---|
| `INACTIVE` | No warning episode is active. |
| `PENDING` | A warning episode is active and its deadline has not been missed. |
| `OVERDUE` | The deadline was missed; the episode remains open until safe distance is reached. |

The monitor stores:

- current state;
- current environment-step index \(t\);
- trigger step \(t_0\), when active;
- deadline step \(t_0+K\), when active;
- previous unsafe predicate, for diagnostics;
- cumulative trigger, recovery, deadline-violation, and unresolved counts.

### 4.2 Step processing order

For every observation, the monitor processes events in this order:

1. compute \(d_t\), \(u_t\), and \(s_t\);
2. update the state using the transition table below;
3. produce per-step events and `stl_cost`;
4. after processing the sample, handle `terminated` or `truncated`;
5. return diagnostics with the environment transition.

The reset observation is sample \(t=0\) and is processed immediately during
`reset()`. The first observation returned by `step(action)` is sample \(t=1\).
If reset begins inside the warning zone, the returned augmented observation
must already show an active obligation. The environment action count and the
monitor sample index must both be logged so this convention is testable.

This ordering is mandatory. In particular, it guarantees that recovery on the
deadline sample is recognized before a violation and that recovery on the final
episode sample is recognized before an unresolved terminal event.

### 4.3 Transitions

| Current state | Condition at step \(t\) | Event and next state |
|---|---|---|
| `INACTIVE` | \(u_t\) | Emit `warning_trigger`; set \(t_0=t\); enter `PENDING`. |
| `INACTIVE` | not \(u_t\) | Remain `INACTIVE`. |
| `PENDING` | \(s_t\) | Emit `recovery`; close the episode; enter `INACTIVE`. |
| `PENDING` | not \(s_t\) and \(t<t_0+K\) | Remain `PENDING`. |
| `PENDING` | not \(s_t\) and \(t=t_0+K\) | Emit one `deadline_violation`; enter `OVERDUE`. |
| `OVERDUE` | \(s_t\) | Emit `late_recovery`; close the episode; enter `INACTIVE`. |
| `OVERDUE` | not \(s_t\) | Remain `OVERDUE`; emit no additional violation event. |

No additional warning obligation is created while the monitor is `PENDING` or
`OVERDUE`. Oscillation between the warning zone and the hysteresis band remains
part of the same warning episode.

### 4.4 Episode termination and truncation

After the final sample is processed:

- if the state is `INACTIVE`, no terminal monitor event is added;
- if a deadline violation was already emitted on that sample, no duplicate
  terminal event is added;
- if the state is `PENDING` and \(t<t_0+K\), emit
  `terminal_unresolved`;
- if the state is `OVERDUE`, retain the existing deadline-violation result and
  emit no second violation.

`terminated` and `truncated` use the same rule semantics but must be logged
separately. A pending obligation at an early episode end is not falsely labeled
as a completed temporal violation in analysis. It is reported as unresolved.
For training only, it receives a conservative binary cost so that ending an
episode cannot erase a pending obligation.

---

## 5. Monitor output contract

The online monitor must expose at least the following fields for every
environment step:

| Field | Type | Meaning |
|---|---|---|
| `stl_distance` | float | \(d_t\) from public hazard lidar |
| `stl_unsafe` | bool | \(d_t<d_{\mathrm{warn}}\) |
| `stl_safe` | bool | \(d_t\ge d_{\mathrm{safe}}\) |
| `stl_status` | enum | `inactive`, `pending`, or `overdue` after processing the sample |
| `stl_warning_trigger` | bool | A warning episode began on this sample |
| `stl_recovery` | bool | On-time recovery occurred on this sample |
| `stl_late_recovery` | bool | Recovery occurred after a missed deadline |
| `stl_deadline_violation` | bool | The deadline was missed on this sample |
| `stl_terminal_unresolved` | bool | The episode ended before a pending deadline |
| `stl_trigger_step` | int or null | \(t_0\) for the active or just-closed episode |
| `stl_deadline_step` | int or null | \(t_0+K\) for the active or just-closed episode |
| `stl_elapsed_steps` | int or null | \(t-t_0\) while active |
| `stl_remaining_steps` | int or null | \(\max(t_0+K-t,0)\) while active |
| `stl_cost` | 0 or 1 | Binary training cost defined below |
| `stl_episode_id` | int | Monotone warning-episode identifier |

Environment-native reward and cost remain separate fields. `stl_cost` must
never overwrite or be added into `native_cost` inside the monitor.

---

## 6. Initial STL-to-cost mapping

The first experiment uses a sparse binary event cost:

\[
c^{\mathrm{STL}}_t
=
\begin{cases}
1, & \text{if a deadline violation occurs at }t,\\
1, & \text{if a pending obligation becomes terminal-unresolved at }t,\\
0, & \text{otherwise.}
\end{cases}
\]

The two positive cases are mutually exclusive on a correctly processed sample.

Consequences:

- entering the warning zone does not itself produce cost;
- remaining pending does not produce cost;
- one missed deadline produces exactly one cost, not one cost per overdue step;
- late recovery is logged but does not remove the earlier cost;
- robustness is diagnostic only and is not used as training cost in the first
  monitor experiment.

This mapping is intentionally simple. It isolates monitor correctness before
testing denser shaping. Its weakness is delayed and sparse learning feedback;
that limitation must be reported rather than hidden. Robustness-based or
active-obligation costs are later ablations, not silent replacements.

---

## 7. Policy observation contract

The temporal cost depends on history. Current distance alone does not reveal
whether a recovery deadline is active or how much time remains. The wrapped
policy observation must therefore append:

\[
m_t =
[
\mathrm{active}_t,\;
\mathrm{overdue}_t,\;
\mathrm{remaining\_fraction}_t
],
\]

where:

- `active` is 1 in `PENDING` or `OVERDUE`, otherwise 0;
- `overdue` is 1 only in `OVERDUE`;
- `remaining_fraction` is
  \(\max(t_0+K-t,0)/K\) in `PENDING`, otherwise 0.

To preserve a fair comparison, task-only, native-cost, and STL-cost conditions
must all receive the same augmented observation. Only the cost supplied to the
learner changes between conditions. Native and STL diagnostics are logged in
all conditions.

This contract is fixed now, although the environment wrapper itself belongs to
the following work package.

---

## 8. Offline oracle and robustness

For each warning episode \(i\) triggered at \(t_i\), define the completed-window
robustness

\[
\rho_i
=
\max_{j\in\{t_i,\ldots,t_i+K\}}
(d_j-d_{\mathrm{safe}}).
\]

For a full window:

- \(\rho_i\ge 0\) means recovery occurred by the inclusive deadline;
- \(\rho_i<0\) means the deadline was missed.

For a trace whose complete warning episodes are indexed by \(\mathcal{I}\),

\[
\rho_{\mathrm{trace}} = \min_{i\in\mathcal{I}}\rho_i.
\]

If there is no warning trigger, the logical property is vacuously satisfied.
Reports must nevertheless show `trigger_count = 0` and record robustness as
`N/A` rather than presenting vacuity as evidence of learned recovery.

If an episode ends before a pending deadline, its robustness is not final. It
is classified as `terminal_unresolved` and excluded from completed-window
robustness aggregation.

The reference check has three layers:

1. a direct offline enumerator implements the definitions above;
2. RTAMT evaluates completed event windows using the same discrete-step
   predicates;
3. the online stateful monitor is compared with both.

The online monitor and direct enumerator must have identical trigger,
recovery, violation, and unresolved event steps. RTAMT and the direct
enumerator must agree on Boolean satisfaction for every complete window.
Real-valued robustness values must agree within \(10^{-9}\). Finite,
incomplete windows are classified by the explicit rule above rather than by an
undocumented library default.

---

## 9. Required semantic tests

Synthetic distance traces are authoritative for semantic tests. They do not
depend on simulator data and should be implemented before monitor integration.

| Case | Required result |
|---|---|
| Always above \(d_{\mathrm{warn}}\) | No trigger, no cost, vacuous satisfaction |
| Reset inside warning zone | Trigger at \(t=0\) |
| \(d_t=d_{\mathrm{warn}}\) | No warning |
| \(d_t=d_{\mathrm{safe}}\) while pending | Recovery |
| Recovery one step after trigger | On-time recovery, no cost |
| Recovery exactly at \(t_0+K\) | On-time recovery, no cost |
| First recovery at \(t_0+K+1\) | One cost at \(t_0+K\), then late recovery |
| Remain unsafe after deadline | One violation event only |
| Move into hysteresis band while pending | Obligation remains pending |
| Leave and re-enter warning while pending | No second obligation |
| Recover, then enter warning again | Two distinct warning episodes |
| Truncate before deadline while pending | One unresolved event and one training cost |
| Terminate on deadline without recovery | One deadline violation, no duplicate unresolved event |
| Recover on final sample before truncation | Recovery, no unresolved event |
| Two vectorized environments | Independent states and resets |

The implementation must also enforce these invariants:

1. at most one warning episode is active per environment;
2. each trigger has exactly one final outcome: on-time recovery, deadline
   violation, or terminal unresolved;
3. cumulative deadline violations never exceed cumulative triggers;
4. a warning episode emits at most one positive cost;
5. `stl_cost` is always 0 or 1;
6. reset clears prior state and counters before processing the new \(t=0\)
   observation; the resulting state may be `PENDING` if that observation is
   inside the warning zone;
7. all state transitions belong to the transition table in Section 4.

---

## 10. Ubuntu-only parameter calibration

### 10.1 Why calibration is still required

The rule semantics do not determine suitable numerical values. The parameters
must make the warning earlier than native hazard contact, recovery physically
achievable, and the deadline neither trivial nor impossible.

The existing summary establishes only:

- native hazard proximity was reached by one scripted trajectory;
- public distance reconstruction is correct;
- random-policy minimum distances ranged from approximately 0.39 to 0.65 in
  three seeds.

It does not contain recovery-time distributions. Therefore \(K\) must not be
guessed from the summary.

### 10.2 Data-collection protocol

On the Ubuntu work computer:

1. recreate the pinned `stl-stage1` environment;
2. commit the collection script before treating its outputs as evidence;
3. collect 30 seeded approach-and-escape trajectories using reset seeds
   1000--1029;
4. approach a selected hazard to a center distance near 0.25, then execute a
   deterministic escape controller until distance exceeds 0.9 or the episode
   ends;
5. collect 30 seeded random-policy episodes as an event-incidence diagnostic;
6. record public \(d_t\), action, reward, native cost, termination flags, and
   privileged distance only as a validation column.

A scripted controller may use privileged geometry to create calibration
trajectories. This does not violate the monitor-input restriction because the
controller is a data-generation instrument, not the learned policy or monitor.
Its access and control law must be stated in the calibration report.

The initial post-hoc candidate grid is:

\[
d_{\mathrm{warn}}\in\{0.35,0.45,0.55\},
\qquad
d_{\mathrm{safe}}-d_{\mathrm{warn}}\in\{0.10,0.20\}.
\]

The grid is a calibration search space, not a final scientific claim. It is
derived from the native 0.2 hazard size, the public lidar range, and the
observed smoke-test distances.

For every candidate pair and every approach-and-escape trajectory, compute the
first recovery time

\[
R_i =
\min\{j-t_i \mid j\ge t_i,\ d_j\ge d_{\mathrm{safe}}\},
\]

where \(t_i\) is the first warning trigger for that trial.

### 10.3 Selection rule

A candidate is eligible when:

1. it satisfies \(0.2<d_{\mathrm{warn}}<d_{\mathrm{safe}}<3\);
2. at least 27 of the 30 controlled trials contain a valid trigger followed by
   recovery;
3. the resulting deadline below is no more than 100 steps.

The 100-step upper bound keeps the first recovery requirement within 10% of the
benchmark's 1000-step episode horizon. It is a Stage I scope limit, not a
physical claim.

For each eligible candidate, set

\[
K =
\max\left(5,\left\lceil1.25\,
Q_{0.95}(R_1,\ldots,R_n)\right\rceil\right),
\]

where \(Q_{0.95}\) is the empirical 95th percentile over valid controlled
recoveries.

Define random-policy trigger rate as the fraction of random episodes containing
at least one warning trigger. Use it only as a diagnostic. Among multiple
eligible candidates, prefer:

1. a random-policy trigger rate between 10% and 80%;
2. the rate closest to 50%;
3. the larger hysteresis margin;
4. the smaller \(K\), as the final tie-breaker.

If no candidate is eligible, run one declared fallback grid:

\[
d_{\mathrm{warn}}\in\{0.30,0.60,0.75\},
\qquad
d_{\mathrm{safe}}-d_{\mathrm{warn}}\in\{0.10,0.20,0.30\}.
\]

If the fallback also has no eligible candidate, do not invent parameters.
Report the failure, controller behavior, and recovery distributions. That
outcome means the present rule or calibration controller needs review before
monitor integration.

### 10.4 Required calibration artifacts

Git must contain:

- the exact collection script;
- a machine-readable summary with all candidate statistics;
- a short calibration report explaining the chosen values;
- the final fixed rule configuration;
- a minimal set of stable trajectory fixtures covering at least one on-time
  recovery, one deadline violation, and one unresolved episode.

Bulk raw CSV files may remain ignored if their generator, schema, hashes, and
summary are tracked. Stable test fixtures must not be ignored.

---

## 11. One-pass implementation work order

The worker on the Ubuntu machine should perform the next milestone in this
order.

### Step 1: Reproduce the environment

- pull the latest repository state;
- recreate `stl-stage1` from `environment.stage1.yml`;
- rerun one reset/step smoke test;
- confirm the public distance reconstruction still matches the recorded
  environment contract.

### Step 2: Create reproducible calibration assets

Add:

```text
scripts/collect_rule_calibration.py
scripts/generate_monitor_fixtures.py
results/rule_calibration/summary.json
docs/rule_calibration_report.md
```

Run the protocol in Section 10, select the parameters, and record the result in
both the final configuration and `DECISIONS.md`.

### Step 3: Create the rule configuration

Add a machine-readable configuration equivalent to:

```yaml
environment_id: SafetyPointGoal1-v0
distance_source: hazards_lidar
lidar_range: 3.0
d_warn: 0.45
d_safe: 0.55
deadline_steps: 79
warning_comparison: lt
safe_comparison: ge
trigger_mode: hysteretic_warning_episode
deadline_inclusive: true
pending_terminal: unresolved_with_binary_cost
cost_mode: binary_deadline_event
robustness_cost_enabled: false
agreement_tolerance: 1.0e-9
```

The three numerical values above are the calibration result. Do not modify them
or any semantic field without a recorded decision change.

### Step 4: Implement the monitor and oracle

The expected project surface is:

```text
src/safety_stl/signals.py
src/safety_stl/monitor.py
src/safety_stl/oracle.py
tests/test_distance_signal.py
tests/test_monitor_boundaries.py
tests/test_oracle_agreement.py
tests/fixtures/
```

The exact package layout may follow repository conventions established during
implementation, but every interface and test in Sections 4--9 is required.

### Step 5: Verify agreement

- run all synthetic boundary cases;
- run the online monitor over stable environment fixtures;
- compare event steps with the direct offline enumerator;
- compare complete-window satisfaction and robustness with RTAMT;
- save an agreement report containing test counts, mismatch counts, and the
  maximum robustness difference.

### Step 6: Deliver and stop at the gate

Update `README.md`, `DECISIONS.md`, and the manifest. Commit:

- collection and fixture-generation code;
- selected parameters and rationale;
- monitor and oracle code;
- semantic tests and stable fixtures;
- calibration and agreement summaries.

Do **not** begin PPO-Lagrangian training in this milestone.

---

## 12. Completion gate

The rule-and-monitor milestone is complete only when:

1. \(d_{\mathrm{warn}}\), \(d_{\mathrm{safe}}\), and \(K\) are supported by
   tracked calibration evidence;
2. all semantic boundary tests pass;
3. the online monitor and direct offline oracle have zero event-step
   mismatches;
4. RTAMT agrees on every complete obligation window;
5. maximum robustness disagreement is at most \(10^{-9}\);
6. incomplete terminal obligations are reported separately;
7. generator scripts and stable fixtures are present in Git;
8. no RL result or safety guarantee is claimed.

Only after this gate should the project implement the OmniSafe wrapper and
begin a small integration smoke test. Quantitative training success thresholds,
seed counts, and task-performance tolerances remain a separate pre-main-study
decision.

**Completion record:** all eight conditions passed on 2026-08-05. Evidence is
stored in `docs/rule_calibration_report.md`,
`docs/monitor_agreement_report.md`, `results/rule_calibration/summary.json`,
`results/monitor_agreement/summary.json`, and `tests/fixtures/`.
