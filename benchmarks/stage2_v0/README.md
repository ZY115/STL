# Stage II v0 Offline Benchmark Foundation

This directory is the machine-readable foundation for the controlled-language
comparison. It is deliberately **not** the final O7 dataset.

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

All five records are machine-validated but still require an independent human
reviewer. `reviews.json` provides the required nine-field checklist and
provenance slots; `review.schema.json` defines its format. O7 must also freeze
the final formula families, complete item
composition, semantic-pair grouping, exact train/validation/test assignments,
and numerical offline admission gates. Therefore:

- `draft_unassigned` is intentional;
- no structure split is claimed from the current single-family fragment;
- the generated files may support review and implementation tests but are not
  a final held-out benchmark;
- model inference, model training, paid API use, and online RL are outside this
  package.
