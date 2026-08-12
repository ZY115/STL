# Current Execution Directive

- **Directive ID:** `WP1-PILOT-EXECUTION-PREP-2026-08-11`
- **Current WP:** WP1 Gold-STL downstream control
- **Status:** authorized full pilot, frozen analysis, WP1 report and follow-on proposals completed
- **Long-term map:** `docs/END_TO_END_RESEARCH_PIPELINE.md`
- **Scientific protocol:** D31 and `configs/stage1_pilot/`

## 1. Why this file exists

The end-to-end pipeline defines the complete research program. This directive
defines the current bounded execution package. An agent must complete every
unblocked item in the package before stopping; it must not treat each file or
small test as a separate user decision.

The previous handoff stopped after the 10k sanity because two explicit rules
required it to stop: D31 did not authorize the full 1M runs, and the repository
did not yet contain a resumable full-pilot runner or the declared hierarchical
analysis. That pause was appropriate. The correction is to make the next
continuous work package explicit, not to remove scientific and compute gates.

## 2. Current verified state

The following gates are closed:

- environment, signal, monitor/oracle and RTAMT agreement;
- OmniSafe wrapper and exact three-condition cost routing;
- real on-policy positive STL event cost;
- common final-checkpoint gold-STL evaluator;
- D31 frozen Stage I pilot protocol;
- RTX 4090 `cuda:0` and deterministic cuBLAS validation;
- three-condition 10k-per-condition CUDA sanity;
- 43 repository tests, dependency check and packaged-file checks.

The 10k sanity is engineering evidence only. Its three evaluation episodes per
condition are not evidence for or against the Stage I hypothesis.

This paragraph described the pre-launch state. The owner subsequently approved
the full package, and all 15 jobs completed on 2026-08-12; see Section 8 and
`docs/stage1_pilot_result_report.md`.

The complete Sections 4.1--4.5 package passed on 2026-08-11. The runner,
analysis module and 11 focused tests are present; the complete suite has 54
passing tests; the excluded 100k exact-scale preflight and ten-episode gold
evaluation passed; and `docs/stage1_pilot_launch_readiness.md` records the
resource projection and recovery procedure. The full compute gate remains
closed.

## 3. Historical pre-launch rationale

The frozen matrix contains 15 training jobs:

```text
3 conditions x 5 training seeds x 1,000,000 transitions = 15,000,000 transitions
```

The current 10k sanity processed 30,000 transitions in approximately 121
seconds across the three sequential conditions, about 248 transitions/second.
A direct extrapolation is roughly 16.8 training hours before 1,500 final
evaluation episodes and analysis. The exact-scale configuration uses 10 vector
environments rather than the sanity's 2, so this estimate must be replaced by
the preflight measurement.

The repository currently has a sanity runner but no full matrix runner,
resume/skip contract, run manifest, or paired hierarchical analysis module.
Launching fifteen jobs manually would make partial failure, duplicate runs,
checkpoint identity and statistical aggregation unnecessarily fragile.

## 4. Authorized continuous implementation package

The work computer is authorized to complete all items in Sections 4.1--4.5
without requesting another step-by-step instruction.

### 4.1 Full-pilot matrix runner

Implement:

```text
scripts/run_stage1_pilot.py
scripts/run_stage1_pilot.sh
```

The runner must:

- load and validate `configs/stage1_pilot/protocol.yaml` and all three overlays;
- enumerate the exact 15 condition/seed jobs in deterministic order;
- run one training job at a time on the single RTX 4090;
- set `CUBLAS_WORKSPACE_CONFIG=:4096:8` before Python/Torch initialization;
- support `--dry-run`, condition/seed selection, `--resume`, `--train-only` and
  `--evaluate-only`;
- write one immutable manifest entry per job containing Git commit, config
  hashes, condition, seed, start/end time, status, run directory, final
  checkpoint and progress hashes;
- never overwrite an existing successful run;
- skip a completed run only when commit/config/checkpoint hashes match;
- mark interrupted/failed jobs explicitly and resume only the missing job;
- use the fixed final checkpoint, not a post-hoc best checkpoint;
- evaluate each successful job immediately on the 100 paired seeds so a later
  failure cannot leave all evaluation until the end;
- avoid full trajectory JSONL by default; retain episode CSV and aggregate JSON.

The runner must not silently change D31, D32, rule semantics, seeds, budgets,
network settings or evaluation mode.

### 4.2 Pilot analysis module

Implement:

```text
src/safety_stl/pilot_analysis.py
scripts/analyze_stage1_pilot.py
```

The analysis must:

- require all 15 final-checkpoint evaluations for a complete primary report;
- preserve per-training-seed and per-episode records;
- calculate pooled missed obligations per trigger and its absolute/relative
  gold-STL-vs-task-only reduction;
- apply the task-only-zero fallback exactly as D31 defines;
- separately report deadline violations, terminal unresolved, trigger rate,
  missed obligations per episode, native cost, STL cost, return and goal events;
- calculate the 10-percentage-point goal-success non-inferiority result;
- perform 10,000 paired hierarchical bootstrap replicates by resampling
  training seeds first and matched evaluation episodes within seed second;
- use a fixed analysis RNG seed recorded in the output;
- report point estimates and 95% intervals without replacing N/A values by 0;
- output machine-readable JSON/CSV and a concise Markdown result table;
- inspect learning-curve stability without claiming formal convergence.

### 4.3 Automated tests

Add focused tests for:

- exact 15-job matrix enumeration;
- frozen-config and hash mismatch rejection;
- completed-job skip and interrupted-job resume behavior;
- no accidental overwrite;
- zero-trigger and zero-task-baseline metric handling;
- paired hierarchical resampling preserving the seed hierarchy;
- deterministic bootstrap output;
- goal-success non-inferiority sign and margin;
- incomplete-matrix analysis rejection;
- final-checkpoint-only selection.

Tests must use synthetic fixtures or mocks; they must not require 15 real GPU
runs.

### 4.4 Exact-scale throughput preflight

After code/tests pass, run one excluded engineering job using:

- condition: `gold_stl_cost`;
- seed: `20260811`, excluded from pilot inference;
- exact 10-vector, 10,000-steps-per-epoch CUDA configuration;
- 100,000 transitions;
- final-checkpoint evaluation on 10 excluded paired seeds;
- separate output under `results/pilot_preflight/`.

Record:

- transitions/second and wall-clock time;
- peak GPU memory if available;
- disk use per training run and evaluation output;
- projected wall-clock and disk for all 15 jobs;
- all routing/oracle/RTAMT checks;
- resume behavior from a deliberately interrupted synthetic or bounded test.

The preflight is not part of Stage I inference and must never be pooled with the
five frozen training seeds.

### 4.5 Launch-readiness report

Create `docs/stage1_pilot_launch_readiness.md` containing:

- exact command for the full matrix and resume command;
- dry-run 15-job manifest;
- test/checksum results;
- measured time, VRAM and disk projection;
- remaining risks and recovery procedure;
- confirmation that no full pilot job has started;
- one explicit launch decision request.

Do not stop after writing the runner, analysis module or tests individually.
Continue through the preflight and readiness report unless a real technical
failure prevents progress.

## 5. Full-pilot compute gate — authorized and completed

The expensive 15-job full pilot was a deliberate owner gate. The owner gave the
required explicit launch authorization, and the package completed on
2026-08-12. The text below remains the historical post-approval work order.

After explicit launch approval, the work computer must execute the following as
one continuous package without further step-by-step questions:

1. run/resume all 15 frozen training jobs sequentially;
2. evaluate each final checkpoint on the same 100 paired seeds;
3. run the frozen hierarchical analysis;
4. inspect learning curves and label instability or non-convergence;
5. create the Stage I pilot result report with failures and limitations;
6. update the WP1 status, decision log, changelog, manifest and checksums;
7. prepare the O8 final-main-study decision package;
8. begin the non-compute WP2/O7 benchmark-design proposal described in the
   long-term pipeline while O8 is reviewed.

## 6. Continuation and stopping policy

### Continue automatically when

- the next item is already specified by this directive;
- the work is code, tests, documentation, dry-run or the bounded 100k preflight;
- a previous item passes its declared gate;
- a failure has a local fix that does not alter scientific semantics.

### Stop and request one decision only when

- authorization for the 15M-transition full pilot is required;
- a proposed fix changes D31/D32, STL semantics, the benchmark, primary metric,
  seeds, budget, baseline or evaluation protocol;
- the measured resource projection is materially larger than documented;
- repeated technical failure remains after diagnosis and documented attempts.

When blocked, prepare the decision package and continue every other unblocked
item. Do not end with only “please tell me what to do next.”

## 7. What comes after WP1

The project does not end after the Stage I pilot. The next scientific work is
already defined:

- O8 decides whether a larger Stage I final study is necessary;
- WP2 defines controlled NL/gold-STL specifications and semantic minimal pairs;
- WP3 reproduces an NL-to-STL method, Lou et al.-style direct cost and a
  history-aware direct-cost baseline on the same saved trajectories;
- WP4 performs the matched online representation comparison;
- WP5 follows predefined Branch A--E to determine whether the contribution is
  an empirical formal-representation advantage, a negative result, a hybrid
  method, a cost-learning fix or a benchmark expansion.

The authoritative details remain in `docs/END_TO_END_RESEARCH_PIPELINE.md`.

## 8. Completion record

This directive's authorized preparation package completed on 2026-08-11.
Measured exact-scale throughput was 335.68 transitions/second. PyTorch peak
reserved CUDA memory was 90 MiB. Linear projection for fifteen 1M jobs and
1,500 evaluations is approximately 13.13 hours and 14.24 MB. All cost routing,
fixed-checkpoint, direct-oracle and RTAMT checks passed. The successful
preflight resume returned `skipped_verified_success` without retraining.

The owner subsequently authorized Section 5. All 15 one-million-transition jobs
and 1,500 paired deterministic evaluations completed without failure. Frozen
analysis found task-only/gold-STL missed-obligation rates of 25.85%/26.03%, a
relative reduction of -0.71% with 95% interval [-24.92%, +21.88%]; the 30%
target was not met. Both primary conditions had 100% goal success and passed
the 10-point non-inferiority criterion. Rising multipliers and costs above both
condition-specific budgets preclude a convergence claim.

The WP1 report, reproducible figures, O8 decision proposal and non-compute O7
benchmark proposal are complete. The active boundary is now owner resolution
of O8 before more GPU work and O7 before Stage II dataset implementation.
