# Stage I pilot launch-readiness report

- **Date:** 2026-08-11
- **Directive:** `WP1-PILOT-EXECUTION-PREP-2026-08-11`
- **Readiness result:** passed
- **Full 15M-transition pilot started:** no
- **Required next decision:** one explicit owner compute authorization

## Implemented execution surface

The repository now contains a deterministic 15-job matrix runner and the
frozen D31 analysis. The runner validates the protocol and all overlays,
enumerates condition-major jobs, trains one job at a time on `cuda:0`, evaluates
each fixed final checkpoint immediately, and stores independent attempt and job
manifests. It supports `--dry-run`, condition/seed selection, `--resume`,
`--train-only`, and `--evaluate-only`.

A successful job is skipped only when its Git commit, execution-source hash,
protocol/overlay/resolved-config hashes, progress hash, fixed-checkpoint hash,
and evaluation hashes still match. Failed or interrupted attempts remain in
separate directories; resume creates a new attempt and never overwrites a
successful run. Resume is at job granularity, not mid-job optimizer-state
continuation.

The analysis requires all 15 evaluations and preserves every training seed and
episode. It implements pooled missed obligations per trigger, task-zero
fallback, absolute/relative gold-vs-task reduction, deadline and terminal
components, goal-success non-inferiority, 10,000 paired hierarchical bootstrap
replicates, and descriptive learning-curve review without a convergence claim.

## Exact commands after authorization

Start the full frozen matrix from the repository root:

```bash
./scripts/run_stage1_pilot.sh --authorized-full-pilot
```

Resume after interruption or failure:

```bash
./scripts/run_stage1_pilot.sh --authorized-full-pilot --resume
```

After all 15 jobs succeed, run the frozen analysis:

```bash
env PYTHONNOUSERSITE=1 PYTHONPATH=src MUJOCO_GL=egl \
  /home/jerry/anaconda3/envs/stl-stage1/bin/python \
  scripts/analyze_stage1_pilot.py
```

The runner refuses non-preflight training unless
`--authorized-full-pilot` is supplied. This flag must only be used after the
owner gives the explicit approval requested at the end of this report.

## Dry-run matrix

Command used:

```bash
./scripts/run_stage1_pilot.sh --dry-run \
  --dry-run-output results/pilot_preflight/dry_run_15_job_manifest.json
```

The final dry-run contains exactly 15 planned jobs:

```text
task_only:     1101, 2202, 3303, 4404, 5505
native_cost:   1101, 2202, 3303, 4404, 5505
gold_stl_cost: 1101, 2202, 3303, 4404, 5505
```

Its SHA-256 is
`3c0e34003414ffc2d30bb10b2182167bf7c72c3ddc1452d1ad531ef299ebda78`.
The status is `dry_run_only_no_training_started`.

## Automated verification

The final repository test suite contains 54 passing tests. The 11 new focused
tests cover:

- exact 15-job enumeration and fixed-final-checkpoint selection;
- completed-job skip, non-overwrite, config/artifact hash rejection, and
  interrupted-attempt resume;
- zero-trigger and zero-task-baseline handling;
- preservation of training-seed hierarchy and paired episode resampling;
- deterministic bootstrap output and goal non-inferiority sign/margin;
- rejection of an incomplete 15-job analysis matrix.

Additional checks passed:

- `pip check`: no broken requirements;
- all YAML files parse;
- new Python modules compile and the shell launcher passes `bash -n`;
- final preflight evidence declares `full_15m_pilot_started=false`;
- no `results/stage1_pilot/jobs/` directory exists.

## Exact-scale excluded preflight

Command used:

```bash
./scripts/run_stage1_pilot.sh \
  --preflight configs/stage1_pilot_preflight.yaml \
  --output-dir results/pilot_preflight --resume
```

The successful attempt used:

| Setting | Value |
|---|---:|
| Condition | `gold_stl_cost` |
| Training seed | `20260811`, excluded |
| Device | RTX 4090 `cuda:0` |
| Vector environments | 10 |
| Steps per epoch | 10,000 |
| Transitions | 100,000 |
| Fixed checkpoint | `epoch-10.pt` |
| Deterministic evaluation episodes | 10 excluded seeds |

Measured resources:

| Measurement | Value |
|---|---:|
| Training wall time | 297.90 s |
| Throughput | 335.68 transitions/s |
| Ten-episode evaluation time | 17.21 s |
| PyTorch peak allocated VRAM | 92,382,208 bytes (88.10 MiB) |
| PyTorch peak reserved VRAM | 94,371,840 bytes (90.00 MiB) |
| Successful training bytes | 90,279 |
| Evaluation bytes | 4,662 |
| Successful attempt total | 103,193 bytes |

All ten progress rows were finite; the observation remained 63-dimensional;
selected learner cost equaled STL cost in every epoch; total steps were exactly
100,000; and the final checkpoint was `epoch-10.pt`. All ten evaluation traces
agreed with the independent direct oracle, and maximum RTAMT robustness
difference was `0.0`.

The ten-episode diagnostic had 39 triggers, 20 deadline violations, two
terminal-unresolved obligations, and eight goal-success episodes. These values
are excluded engineering observations, not evidence for or against the Stage I
hypothesis and not a convergence result.

## Resource projection

Linear projection from the exact vector/epoch-scale preflight gives:

| Full package component | Projection |
|---|---:|
| Fifteen 1M-transition training jobs | 12.41 h |
| 1,500 final-checkpoint evaluations | 0.72 h |
| Training plus evaluation | 13.13 h |
| Approximate generated data | 14.24 MB |

The estimate is a planning value, not a runtime guarantee. It assumes similar
throughput across all conditions and across ten times the training duration.
Reserve operational margin for simulator variance, checkpoint I/O, failure
retries, reporting, and bootstrap analysis. Disk is not a practical constraint;
100 MB free space is a conservative minimum for this package.

## Failures encountered and corrected

Two attempts failed before Agent construction or rollout, so they executed zero
transitions:

1. PyTorch 2.4.1 rejected a `torch.device` argument in
   `reset_peak_memory_stats`; the runner now explicitly selects CUDA index 0
   and uses the integer index for memory statistics.
2. custom OmniSafe environment registration depended on incidental import
   order; the runner now imports `safety_stl.omnisafe_env` explicitly before
   constructing the Agent.

Attempt 3 completed. A subsequent `--resume` invocation verified all hashes
and returned `skipped_verified_success` without retraining. A deliberately
interrupted synthetic job also passed the new-attempt resume test.

## Remaining risks and recovery

- The preflight is only 100k transitions. Learning-curve behavior and runtime
  can change during the full 1M jobs; every curve must still be reviewed.
- The workload is simulator/update dominated and uses little VRAM. The RTX 4090
  is functioning, but available VRAM does not imply a proportional speedup.
- The preflight worktree contained the implementation changes but had not yet
  been committed. Commit this complete package before the behavioral launch so
  each new job records a reproducible Git commit. Do not alter frozen configs.
- If the process stops, run the resume command. Verified successful jobs are
  skipped; only a failed or missing job is started in a new attempt directory.
  A partially trained job restarts from its seed because mid-job optimizer
  continuation is intentionally not claimed.
- If commit/config/checkpoint/progress/evaluation hashes disagree, the runner
  stops instead of overwriting or silently accepting the job. Diagnose and
  preserve the old evidence before any rerun.

## Launch decision request

The implementation, tests, exact-scale preflight, resource projection, and
recovery path are ready. No frozen pilot job has started.

> **Owner decision required:** authorize the full 15-job, 15M-transition Stage I
> pilot now? Approval authorizes the exact frozen D31/D32 matrix only; it does
> not authorize changing the protocol or treating it as the final main-study
> standard.
