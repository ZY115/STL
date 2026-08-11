# Stage I pilot protocol freeze and three-condition sanity report

- **Date:** 2026-08-11
- **Decision:** D31, approved for the Stage I pilot only
- **Sanity result:** passed
- **Full 1M runs:** not started
- **Machine-readable evidence:** `results/pilot_sanity/summary.json`

## Frozen pilot protocol

The project owner approved O6 as a pilot protocol, not as the final main-study
standard. The primary safety metric is:

```text
(deadline violations + terminal unresolved obligations) / warning triggers
```

The primary comparison is gold-STL cost versus task-only. The pilot target is a
30% relative reduction and the absolute difference is always reported. If the
task-only rate is zero, relative reduction is undefined and only the absolute
difference is used. Absolute reduction is defined as task-only rate minus
gold-STL rate, so positive values indicate improvement. Goal success uses a
10-percentage-point non-inferiority margin.

The matched design fixes five training seeds, 100 paired deterministic
evaluation episodes per training seed and condition, fixed final checkpoints,
the common gold-STL evaluator, and 10,000 paired hierarchical bootstrap
replicates. One million transitions per condition and training seed is only a
pilot budget; learning curves must be reviewed before any convergence claim.

Frozen files:

- `configs/stage1_pilot/protocol.yaml`;
- `configs/stage1_pilot/task_only.yaml`;
- `configs/stage1_pilot/native_cost.yaml`;
- `configs/stage1_pilot/gold_stl_cost.yaml`.

The condition limits are `0.0`, `25.0`, and `0.1`. Native cost counts hazard-
cost steps per episode, while STL cost counts missed-obligation events per
episode. `STL cost_limit=0.1` is not automatically a 10% violation rate.

## Sanity design

Command:

```bash
./scripts/run_stage1_pilot_sanity.sh
```

The sanity used seed `20260811`, which is explicitly excluded from pilot
inference. Each condition used:

| Setting | Value |
|---|---:|
| Training backend | `cuda:0`, RTX 4090, deterministic cuBLAS workspace |
| Transitions | 10,000 |
| Vector environments | 2 |
| Steps per epoch | 2,000 |
| Steps per vector slot per epoch | 1,000 |
| Epochs | 5 |
| PPO update iterations | 40, with configured KL early stopping |
| Final-checkpoint evaluation episodes | 3 paired seeds |

The final gate was rerun after D32 on `torch 2.4.1+cu124`; all three training
conditions used `cuda:0`. The network, normalization, optimizer, monitor,
reward, and observation settings come from the frozen pilot protocol. Only
training scale, vector count, logging frequency, and the non-pilot engineering
seed are sanity overrides. Final-checkpoint gold evaluation remains the common
CPU evaluation path for every condition.

OmniSafe prints an epoch-cutoff warning at the exact 1000-step boundary because
its adapter checks `epoch_end` before its `time_out` branch. The same branch then
uses `final_observation` for timeout bootstrapping. Episode length was 1000 in
every condition, and the Stage I wrapper had already finalized terminal monitor
state before auto-reset; this message does not indicate a partial-horizon
rollout in this run.

## Gate result

All required checks passed:

- all three runs wrote five finite progress rows and a final `epoch-5.pt`;
- all three training runs used the same `cuda:0` device;
- all observations had the shared 63-dimensional shape;
- task-only selected cost was zero in every epoch;
- native-condition selected cost exactly equaled native cost in every epoch;
- STL-condition selected cost exactly equaled STL event cost in every epoch;
- positive native cost and positive STL event cost were both actually observed;
- each final checkpoint used deterministic evaluation on seeds
  `13000, 13001, 13002`;
- every online trace agreed with the independent direct oracle;
- maximum RTAMT completed-window robustness difference was `0.0`.

In the final CUDA sanity, the three-episode diagnostic outputs contained
missed-obligation rates of 0.0 (task-only: 0/3), 1.0 (native: 1/1), and 1.0
(gold STL: 1/1). These values are deliberately reported only as checkpoint/
evaluator evidence. Ten thousand transitions and three evaluation episodes are
far below the frozen pilot design, so they do not measure the D31 hypothesis and
must not be interpreted as evidence for or against STL-cost effectiveness. The
earlier CPU sanity is retained only as engineering history and is not mixed with
the CUDA evidence.

## Gate boundary and next action

The engineering sanity gate is closed. No full 1M run was started. The complete
follow-up package defined by `docs/CURRENT_EXECUTION_DIRECTIVE.md` subsequently
passed: resumable runner, frozen analysis, focused tests, and excluded 100k
exact-scale preflight. The project is now at the single compute decision in
`docs/stage1_pilot_launch_readiness.md`. After launch approval, the five-seed,
three-condition pilot, paired final-checkpoint evaluation, bootstrap report and
WP1 closure proceed continuously. Before treating its result as converged or
converting the pilot protocol into a final main-study standard, inspect
learning curves and record a new decision under O8.
