# Stage I Pre-Main Engineering Gate Report

## Status

- **Completed:** 2026-08-11
- **Result:** engineering portion passed
- **Subsequent status:** O6 was approved for the pilot by D31 and the
  matched-condition sanity later passed
- **Still not performed:** full 1M pilot training

This milestone closes the two implementation gaps named in the updated handoff:
a nonzero STL event cost inside an actual PPOLag rollout and one common
checkpoint evaluator using the gold offline oracle. At the time of this run it
did not close the owner-decision portion of O6; D31 and
`docs/stage1_pilot_sanity_report.md` record the later resolution.

## Explicit cost-limit enforcement

`run_ppo_update` now rejects PPOLag configurations that omit
`lagrange_cfgs.cost_limit`, rejects non-finite/negative values, and passes the
declared block into OmniSafe. The earlier 64-transition integration smoke now
also records its legacy interface-only `cost_limit=25.0` explicitly rather
than silently inheriting the OmniSafe default.

The later D31 pilot budgets are separate and frozen under
`configs/stage1_pilot/`; they are not the final main-study standard.

## On-policy positive STL-cost sanity

Command:

```bash
./scripts/run_on_policy_sanity.sh
```

Fixed sanity configuration:

| Setting | Value |
|---|---:|
| Algorithm | PPOLag |
| Environment | `Stage1SafetyPointGoal1STLCost-v0` |
| Seed | `20260811` |
| Vector environments | 2 |
| Episode horizon | 1000 |
| Transitions | 2000 |
| Per-vector rollout | 1000 |
| Explicit `cost_limit` | 0.1 |
| Epochs / update iterations | 1 / 1 |

Both vector slots completed a full episode before the epoch boundary. The
reported episode metrics are means across the two completed episodes:

| Metric | Result |
|---|---:|
| `Metrics/STLTriggers` | 0.5 |
| `Metrics/STLDeadlineViolations` | 0.5 |
| `Metrics/STLTerminalUnresolved` | 0.0 |
| `Metrics/STLCost` | 0.5 |
| `Metrics/SelectedAlgorithmCost` | 0.5 |
| `Metrics/NativeCost` | 26.0 |
| Lagrange multiplier after update | 0.0359999947 |

Thus at least one of the two actor-sampled episodes contained a warning trigger
and a deadline violation, producing `stl_cost=1` on an actual PPOLag rollout.
The same event reached the selected learner cost, and the multiplier responded
to the explicit 0.1 budget. The run contains only one update and cannot support
a learning or safety conclusion.

Tracked evidence: `results/on_policy_sanity/summary.json`. Raw progress and
checkpoints remain under the ignored `omnisafe_runs/` directory; the tracked
summary stores the progress SHA-256 hash.

## Common checkpoint evaluation runner

New entry point:

```bash
./scripts/evaluate_stage1_checkpoint.sh \
  --run-dir PATH_TO_OMNISAFE_RUN \
  --checkpoint epoch-N.pt \
  --episodes N \
  --seed-start FIRST_SEED \
  --max-episode-steps 1000 \
  --output-dir PATH_TO_OUTPUT
```

The runner:

1. reconstructs the actor from the saved OmniSafe config and checkpoint;
2. applies saved observation-normalization statistics without updating them;
3. evaluates every policy through the same gold-STL wrapper, regardless of its
   training cost condition;
4. preserves return, native cost, goal events, trigger/recovery/deadline/
   unresolved events, distances, and gold STL cost;
5. re-evaluates each complete trajectory with the independent direct oracle;
6. checks completed windows with RTAMT at tolerance `1e-9`;
7. fails on any event-step or cost mismatch;
8. writes aggregate JSON, episode CSV, and optional trajectory JSONL.

The three-episode smoke used deterministic evaluation seeds `12000--12002` and
the one-update sanity checkpoint. All three episodes had one trigger and one
on-time recovery; online/oracle mismatches were zero, all three RTAMT windows
agreed, and maximum robustness difference was 0. Goal success was 0 because
this is an effectively untrained checkpoint. These values validate the
evaluator only and are not a comparison result.

Tracked evidence is under `results/evaluation_smoke/`.

## Automated verification

Two new tests cover direct-oracle/RTAMT evaluation and pooled metric
denominators. The repository-wide suite passed all 40 tests on 2026-08-11, and
`pip check` reported `No broken requirements found.` All 135 packaged-file
checks passed after `CHECKSUMS.sha256` was regenerated.

## Subsequent gate closure

D31 later approved these values for the Stage I pilot only. The frozen configs
were validated and the three-condition 10k-per-condition sanity passed. See
`docs/stage1_pilot_sanity_report.md` and `results/pilot_sanity/summary.json`.
The full 1M pilot remains unrun, and O8 keeps the final main-study standard open.
