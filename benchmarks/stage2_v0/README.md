# Stage II v0 Offline Benchmark

This directory implements the frozen D37 40-specification contract. It contains
eight items in each of five typed formula families: hysteretic bounded recovery,
recovery plus persistence, bounded avoidance, conjunction and held-out
disjunction. The split is 20 train, eight validation, four parameter test and
eight structure test; semantic pairs never cross splits.

## Current release boundary

All 40 records, typed ASTs, deterministic STL renderings and machine-generated
boundary traces validate. The five historical `br-v0-001..005` records have
independent approval; 35 new records remain pending human review. Six frozen
same-index Boolean contrasts are classified logical aliases and await owner
disposition. Therefore the final dataset gate and all held-out Gold labels stay
closed.

Model-visible generated artifacts contain train/validation labels only. The
builder may evaluate held-out records transiently for machine coverage, but it
does not serialize their labels. The fixed real-policy package contains 60
pre-model-selection trajectories (20 per Stage I condition); all 2,400
spec/trace combinations pass internal direct/online/RTAMT checks, while only
1,680 train/validation label records are written.

## Rebuild

From the repository root:

```bash
env PYTHONNOUSERSITE=1 PYTHONPATH=src MUJOCO_GL=egl \
  /home/jerry/anaconda3/envs/stl-stage1/bin/python \
  scripts/build_stage2_v0_benchmark.py

env PYTHONNOUSERSITE=1 PYTHONPATH=src MUJOCO_GL=egl \
  /home/jerry/anaconda3/envs/stl-stage1/bin/python \
  scripts/build_stage2_training_data.py

env PYTHONNOUSERSITE=1 PYTHONPATH=src MUJOCO_GL=egl \
  /home/jerry/anaconda3/envs/stl-stage1/bin/python \
  scripts/build_stage2_real_corpus.py
```

The real-corpus command requires the completed local spatial replay, whose full
geometry table is intentionally ignored but hash-locked. Do not pass
`--include-held-out-labels` before every held-out specification has independent
approval.

Future predictions are validated with:

```bash
env PYTHONNOUSERSITE=1 PYTHONPATH=src \
  /home/jerry/anaconda3/envs/stl-stage1/bin/python \
  scripts/evaluate_stage2_predictions.py PREDICTIONS.jsonl
```

Direct methods must not receive Gold STL, Gold labels, handcrafted timers or
Gold monitor state as inputs. Full design and gates are in
`docs/STAGE2_CONTINUOUS_WORK_ORDER.md` and
`docs/stage2_v0_benchmark_report.md`.
