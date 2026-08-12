# O8 Proposal: Stage I Final-Main-Study Decision

- **Prepared:** 2026-08-12
- **Status:** proposal only; owner decision required
- **Evidence:** `docs/stage1_pilot_result_report.md`
- **Does not authorize:** additional GPU training or a change to D31

## 1. Decision now required

D31 defined the completed 1M-transition experiment as a pilot, not the final
main-study standard. O8 must now decide whether to:

1. close Stage I with the negative pilot and proceed to the offline Stage II
   representation benchmark;
2. repeat or extend the same sparse-cost configuration;
3. run a bounded diagnostic that prospectively tests why the gold-STL cost did
   not change behavior, then freeze a final Stage I standard.

## 2. Evidence that constrains the choice

- Gold-STL versus task-only relative reduction was `−0.71%`, with 95% interval
  `[−24.92%, +21.88%]`; the +30% pilot target was not reached.
- Goal success was 100% for both primary conditions, so the failure is not
  explained by task collapse.
- Gold-STL selected cost averaged 1.650 missed events/episode over the final 20
  epochs versus a 0.1 limit.
- The gold multiplier averaged 3.217 in that window and continued to rise in
  four of five seeds.
- The final learning-rate schedule had decayed to zero at 1M transitions.
  Continuing the existing checkpoints without redefining the schedule would
  not be a valid longer-budget study.
- Monitor/direct-oracle/RTAMT agreement was exact on all 1,500 evaluations, so
  monitor disagreement is not the observed bottleneck.

## 3. Options

### Option A — close Stage I at the pilot

Treat the result as a negative downstream finding and move to WP2/WP3 offline
representation work. The gold oracle remains useful for label generation even
though this PPOLag configuration did not improve policy behavior.

**Benefit:** no additional GPU cost; preserves the negative result.

**Risk:** Stage II online comparisons would use a gold-cost control that has not
shown behavioral efficacy, weakening interpretation of later policy results.

### Option B — rerun the same settings at larger scale

Start new runs from initialization with a longer total-step schedule, leaving
the sparse event cost, cost limit and optimizer otherwise unchanged.

**Benefit:** directly tests whether the main limitation was the 1M budget.

**Risk:** current cost curves and rising multipliers provide no evidence that
scale alone will solve the issue. Adding seeds or evaluation episodes improves
precision but cannot make the learner satisfy the constraint.

### Option C — bounded diagnostic before the final standard (recommended)

Run a small, explicitly non-confirmatory diagnostic matrix that separates
three mechanisms before committing to a final main study:

1. **Optimization diagnostic:** retain the exact binary gold cost and test a
   prospectively specified stronger multiplier schedule or longer from-scratch
   training schedule.
2. **Budget diagnostic:** test a small semantic-unit sweep of missed events per
   episode. The values must be declared before running and must not be compared
   numerically with native-cost limits.
3. **Credit-assignment diagnostic:** compare the frozen binary event cost with
   one explicitly labeled, causal, semantics-preserving shaping candidate while
   continuing to evaluate every policy with the unchanged binary gold oracle.

Use non-pilot seeds and a bounded transition budget for this diagnostic. Select
the final setting by a predeclared curve/routing gate, not by final evaluation
performance. Then rerun the chosen final standard from initialization on five
matched seeds; do not reuse the current pilot as confirmatory evidence.

**Benefit:** directly addresses the observed failure mechanisms and protects the
final study from another expensive, uninformative repeat.

**Risk:** adds method/configuration search and must be reported as pilot-driven.
Any selected setting requires a new confirmatory run and cannot reuse D31's
confidence interval as independent confirmation.

## 4. Candidate diagnostic contract for approval

The following values are deliberately marked **candidate**, not fixed:

| Item | Candidate |
|---|---|
| Seeds | 3 non-pilot seeds |
| Budget | 300k–500k transitions per diagnostic cell |
| Binary-cost control | frozen rule, event cost and gold evaluator unchanged |
| Optimization cells | current PPOLag versus one stronger prospective multiplier setting |
| Budget cells | at most three STL event-cost limits in missed-events/episode units |
| Shaping cells | binary event cost versus at most one causal shaping ablation |
| Evaluation | 30–50 paired episodes per cell for screening only |
| Gate | exact routing/oracle agreement; lower missed/trigger trend; no material goal collapse; multiplier/cost behavior plausibly stabilizing |

The exact multiplier parameter, cost-limit values, shaping equation and cell
count require a separate written freeze before execution. They must be chosen
from the pilot's observed scale and semantic meaning, not copied from native
cost or selected after viewing diagnostic evaluation results.

## 5. Recommended O8 decision

Approve Option C as a bounded diagnostic design phase, while allowing WP2/O7
schema and benchmark work to proceed without GPU. Do not authorize a larger
Stage I final run yet.

This recommendation is based on the combination of a missed primary target,
preserved goal success, costs far above budget and non-stationary multiplier
dynamics. It does not change the current recorded pilot or claim that shaping
will work.

## 6. Explicit owner decision needed

Before additional training, record one of:

```text
O8-A approved: close Stage I with the completed negative pilot.
O8-B approved: prepare a longer same-method final-study protocol.
O8-C approved: freeze and run the bounded optimization/budget/credit diagnostic.
```

Until then, all three choices remain proposals and no additional GPU package is
authorized.
