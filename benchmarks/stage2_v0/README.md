# Stage II v0 Offline Benchmark Foundation

This directory is the historical five-item machine-readable foundation for the
controlled-language comparison. It is deliberately **not** the final D37 O7
dataset. Expand it according to `docs/STAGE2_CONTINUOUS_WORK_ORDER.md`.

## Current executable scope

The only executable formula family is the already verified Stage I hysteretic
bounded-recovery requirement over the public nearest-hazard distance:

```text
G(e(d < d_warn) -> F_[0,K](d >= d_safe))
```

Five draft specification records exercise different threshold/deadline values.
Only `br-v0-001` uses calibrated Stage I parameters and is allowed for online
use. The other four are offline-only candidates and have not been calibrated
as RL requirements.

Each specification currently has 11 generated distinguishing cases: vacuous,
on-time recovery, exact-deadline recovery, one-step-late recovery, terminal
unresolved, both equality boundaries, repeated unsafe samples under one active
obligation, retrigger after recovery, and a two-trajectory causal-history
contrast. Existing Stage I task/native/Gold checkpoints supply six preselected
real trajectories through the same schema.

## Build and validate

From the repository root:

```bash
env PYTHONNOUSERSITE=1 PYTHONPATH=src MUJOCO_GL=egl \
  /home/jerry/anaconda3/envs/stl-stage1/bin/python \
  scripts/build_stage2_v0_benchmark.py
```

The command validates the specification contract, regenerates Gold labels with
the independent oracle, checks the online monitor event-by-event, checks every
completed obligation window with RTAMT, imports the frozen representative real
traces, and writes `generated/coverage.json` plus artifact hashes.

To evaluate a future method prediction file:

```bash
env PYTHONNOUSERSITE=1 PYTHONPATH=src \
  /home/jerry/anaconda3/envs/stl-stage1/bin/python \
  scripts/evaluate_stage2_predictions.py PREDICTIONS.jsonl
```

`prediction.schema.json` defines the common input format. Direct methods must
not receive Gold STL or Gold monitor state; `predicted_active_obligation` is a
method prediction used to score causal-history contrasts, not an input label.

## Review boundary

All five current records are machine-validated and were independently approved
by Yuhang on 2026-08-12. `reviews.json` records the completed nine-field
checklists; `review.schema.json` defines their format. D37 has now frozen
the final formula families, item composition, semantic-pair grouping, exact
train/validation/test assignments and numerical offline admission gates.
Therefore:

- `draft_unassigned` is intentional;
- no structure split is claimed from the current single-family fragment;
- the generated files may support review and implementation tests but are not
  a final held-out benchmark;
- this five-item package alone does not authorize held-out evaluation because
  the remaining 35 D37 records do not yet exist or have reviews;
- train/validation model work and later gated online RL follow the continuous
  work order, while paid API use remains prohibited.
