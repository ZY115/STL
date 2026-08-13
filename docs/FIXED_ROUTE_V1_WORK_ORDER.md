# Fixed-Route v1 Controlled Experiment

- **Decision:** D42
- **Base environment:** `SafetyPointGoal1-v0`
- **Configuration:** `configs/fixed_route_v1/scenario.yaml`
- **Status:** geometry and thresholds fixed; D43 quick-turn authorized after
  deadline calibration and D41 hardware recovery

## 1. Purpose

The completed Stage I pilot mixed several sources of variation: the start,
hazard layout and repeated goals changed with the evaluation seed, while the
old `d_warn=0.45` and `d_safe=0.55` disks covered a large part of the map. The
new controlled experiment removes that geometric variation so the three policy
conditions can be compared on the same understandable navigation problem.

This experiment fixes the **route request**, not the realized trajectory:

```text
fixed start + fixed ordered goals + fixed hazard layout
  -> policy chooses every action
  -> task/native/STL policies may learn different paths
```

If agent coordinates were fixed step by step, there would be no RL problem and
no behavioral comparison. Therefore, `route` here means the same start and
ordered targets for all conditions.

## 2. Controlled scenario

The simulator dynamics, Point agent, native goal reward, eight physical hazards
and native hazard cost remain those of `SafetyPointGoal1-v0`. The scenario fixes:

- start: `(0.95, -0.30)`, heading north;
- four ordered goals: `(1.15, 1.35)`, `(-0.20, 1.30)`,
  `(-0.70, -1.30)`, `(1.20, -1.00)`;
- the eight-hazard layout copied from the already valid seed-10001 Stage I
  geometry;
- the unconstrained vase at `(-1.30, -1.30)`;
- cyclic goal order within a 1,000-step episode.

The straight start-to-goal segments have minimum hazard-center clearances of
approximately `0.188`, `0.269`, `0.144` and `0.191`. Three direct segments enter
the proposed warning band and one enters only the `0.25--0.28` recovery band.
The learned policy remains free to detour.

## 3. Candidate STL rule

The new center-distance thresholds are:

```text
physical hazard: d <= 0.20
warning entry:   d < 0.25
recovery:        d >= 0.28
```

The 0.03 hysteresis band is intentionally much narrower than the historical
0.10 band. It must be checked for rapid re-triggering and sensitivity to one-step
dynamics. The old `K=79` was calibrated for `0.45 -> 0.55` and must not be
reused. `deadline_steps` therefore remains `null` in the scenario configuration.

## 4. Why all three plots use the warning and safe circles

The circles are a **common Gold evaluation overlay**, not part of the physical
environment and not proof that every condition trained with STL cost. Every
saved trajectory is judged afterward by the same rule so rates are comparable:

| Condition | Cost returned to the learner | STL events retained for evaluation |
|---|---|---|
| Task only | zero | yes |
| Native safety | native physical-hazard cost | yes |
| STL safety | STL monitor learner cost | yes |

Removing the circles and STL events from the task/native panels would hide the
common outcome criterion. Figures must label them `common Gold evaluation
overlay`. The agent does not observe the drawn circles as privileged geometry.

The existing controlled Stage I design also gives all three learners the same
three causal temporal-state fields (`active`, `overdue`, remaining deadline).
This deliberately holds the observation representation constant so the primary
comparison isolates the selected cost. Therefore Task-only and Native-safety are
controlled cost baselines, not untouched stock-environment baselines. If a pure
stock baseline is needed, add it as a fourth ablation; do not silently remove
temporal fields from only two of the three primary conditions.

## 5. Required execution order

### A. CPU geometry and lifecycle gate

1. Run `python scripts/validate_fixed_route_scenario.py`.
2. Run `python scripts/plot_fixed_route_scenario.py` and inspect the planned
   geometry before simulator integration.
3. In the pinned Ubuntu environment, instantiate one untrained environment and
   verify exact start, hazard coordinates and goal order across two resets.
4. Verify that reaching a goal selects the next listed goal rather than a
   random location, and that the fourth goal cycles to the first.
5. Render at least one complete route attempt and save coordinates plus a
   top-down figure.
6. Confirm initial native cost is zero and all start/goal endpoints are outside
   `d_safe=0.28`.

### B. Recalibrate the deadline

Use the existing deterministic approach/retreat calibration principle with the
new `0.25 -> 0.28` thresholds. Record trigger depth, inward velocity, recovery
time and failures. Select `K` prospectively from the recovery-time distribution
using the same declared quantile-plus-margin rule, then create a separate
executable rule YAML. Do not edit the historical `configs/stage1_rule.yaml`.

Before accepting `K`, verify:

- enough warning entries occur on the fixed route;
- the controller can recover from representative entry states;
- the 0.03 band does not cause pathological trigger/recovery chattering;
- online monitor, direct oracle and RTAMT agree at the new boundaries.

### C. Thirty-minute quick-turn experiment

The first run is the owner-authorized exploratory protocol in
`configs/fixed_route_v1/quick_turn.yaml`, not a long pilot. Only after B and the
D41 hardware recovery gate pass, run one matched training seed for:

1. Task-only: selected learner cost is zero;
2. Native-safety: selected learner cost is the simulator hazard cost;
3. STL-dense-safety: selected learner cost is the existing C1 causal dense
   surrogate; unchanged binary Gold STL events remain the evaluation truth.

Use `150,000` transitions per condition, `10,000` steps per epoch and one final
checkpoint. At the historical throughput this should leave useful margin
inside a 30-minute aggregate training budget. Before launching all three cells,
measure the actual fixed-route throughput with a 10k preflight. If the projected
aggregate exceeds 30 minutes, reduce **all three** conditions to the same largest
10k multiple that fits, but never below 50k. The reduction may depend only on
measured speed, never on observed policy results.

Use the minimum throughput measured across the three preflights and reserve 20%
of the nominal wall-clock capacity:

```text
N = min(150000,
        floor_to_10000(0.80 * 1800 seconds * minimum_throughput / 3))
```

If `N < 50,000`, stop before reported training and document the measured
throughput. Do not violate the wall-clock cap by silently switching to CPU,
restarting failed cells from zero, or giving one condition fewer transitions.

Train Task-only first. Evaluate its final checkpoint for 20 stochastic episodes,
then freeze separate provisional Native and C1 limits at 70% of their own
Task-only means. Never copy one numerical limit into the other cost unit. Use
the same seed, route, observation, reward, backend, initial multiplier and
effective transition count for all three conditions.

The 30-minute cap covers training for the three reported cells. Preflight,
calibration, final evaluation and plotting are separate setup/reporting work,
but no training may be extended after seeing an intermediate result. This run
answers only whether the implementation works and whether a visible behavioral
separation appears quickly. It cannot establish convergence, significance or
generalization.

Report both task behavior and common-Gold safety behavior. At minimum include
goal count/return, native cost, warning triggers, missed recovery obligations,
time in the physical/warning/recovery bands and paired top-down trajectories.

### D. Immediate replay and figures

As soon as all three final checkpoints exist, do not start another training
round. Run:

- 20 stochastic 1,000-step evaluation episodes per condition for exploratory
  summary metrics;
- one deterministic 1,000-step episode per condition for the main trajectory
  figure.

Create `results/fixed_route_v1/quick_turn/fixed_route_quick_turn_trajectories.png`
as one row with three columns in the fixed order Task-only, Native-safety and
STL-dense-safety. Every panel must use identical axes and show the physical
hazards, common Gold warning/safe overlay, fixed start, ordered goals, actual
agent path split by goal, triggers, recoveries, misses and terminal endpoint.
The dashed waypoint route may appear faintly as a reference, but it must not be
presented as the actual policy trajectory.

Also save the underlying per-step coordinates, one compact learning-curve
figure and `docs/fixed_route_v1_quick_turn_report.md`. The report must state:

- whether each expected learner cost became positive and reached PPOLag;
- whether the three final paths visibly differ;
- whether STL-dense reduces Gold misses, physical incursions or warning-zone
  occupancy relative to Task-only;
- the corresponding change in return and goal events;
- whether a null result means no signal, no learned response, or simply an
  inconclusive short budget.

### E. Generalization check

The fixed scenario is a controlled diagnostic, not a replacement for the
benchmark distribution. Any promising result must later be evaluated on held-
out randomized layouts or additional fixed routes. Failure there means the
policy memorized one geometry rather than learning a generally useful safety
behavior.

## 6. Work-computer handoff and hard stops

The repository contains the scenario loader, task installer and OmniSafe entry
point. The OmniSafe entry point rejects a fixed-route launch unless a separate
rule configuration has matching `d_warn=0.25`, `d_safe=0.28` and a calibrated
integer `K`. D41 also continues to block new GPU training until the host passes
its administrator-level hardware stability gate.

The Ubuntu work computer should begin immediately with A and B, implement a
resumable quick-turn runner plus deterministic replay/plotting entry points, and
run all static/dry-run checks. After D41 clears, it may execute C and D without
another owner question. It must stop after the quick-turn report and must not
automatically resume the old 15-job pilot, the 300k D38 matrix or a longer
fixed-route run.

## 7. Exact work-computer implementation order

Use the project-owned D40 PPOLag runtime and adapter rather than modifying
installed OmniSafe files. Implement these entry points:

- `scripts/run_fixed_route_quick_turn.py`: `--phase preflight`, `task-control`,
  `cost-cells`, `evaluate`, `plot` and resumable `all`;
- `scripts/replay_fixed_route_quick_turn.py`: load the three final checkpoints
  and write public signals plus diagnostic-only true geometry;
- `scripts/plot_fixed_route_quick_turn.py`: build the required trajectory and
  learning-curve figures from saved files, never by retraining.

Every environment construction must pass both
`scenario_config_path=configs/fixed_route_v1/scenario.yaml` and the newly
calibrated `rule_config_path=configs/fixed_route_v1/rule.yaml`; vector execution
must use `asynchronous=False`. Do not edit `configs/stage1_rule.yaml` or any
historical Stage I output.

Execute in this order:

1. validate scenario geometry and exact reset/goal lifecycle;
2. calibrate `K`, write `rule.yaml`, and pass online/oracle/RTAMT agreement;
3. pass the D41 host stability gate;
4. run 10k preflights for all three conditions and freeze one effective `N`;
5. train Task-only to `N` and derive/freeze the two provisional cost limits;
6. train Native-safety and STL-dense-safety to the same `N`;
7. evaluate final checkpoints, save raw trajectories and create both figures;
8. write the quick-turn report, update status/changelog/checksums, and stop.

The run manifest must record commit, Python/package/GPU versions, scenario/rule/
protocol hashes, calibrated `K`, preflight throughput, effective `N`, cost
limits, commands, cumulative training wall time and final checkpoint hashes.

After the three preflights, calculate the frozen budget with:

```bash
python scripts/validate_fixed_route_quick_turn.py \
  --throughput TASK_TPS NATIVE_TPS STL_DENSE_TPS
```

The runner must use the returned `effective_transitions_per_condition` exactly
and refuse launch when `training_may_start` is false.
