# Stage I full-pilot results

The local `jobs/` tree contains the 15 immutable training/evaluation attempts,
progress logs and checkpoints. Those bulk artifacts remain ignored by Git.

The compact, reproducible statistical package under `analysis/` is tracked:

- `analysis.json`: frozen D31 point estimates, intervals and learning-curve review;
- `per_training_seed.csv`: all 15 condition/seed aggregates;
- `episode_records.csv`: 1,500 final-checkpoint evaluation records;
- `bootstrap_primary.csv`: 10,000 paired hierarchical bootstrap replicates;
- `learning_curve_summary.csv`: predeclared descriptive tail-drift flags;
- `learning_curve_tail_windows.csv`: first/last 20-epoch descriptive means;
- `paired_episode_examples.csv`: deterministic paired examples in both directions;
- `result_table.md`: compact primary result table;
- `figures/`: PNG/SVG figures and a hash manifest.

The formal interpretation, limitations and next-decision proposal are in
`docs/stage1_pilot_result_report.md` and
`docs/stage1_o8_main_study_decision_proposal.md`.

Reproduce the analysis and figures from the repository root with:

```bash
env PYTHONNOUSERSITE=1 PYTHONPATH=src MUJOCO_GL=egl \
  /home/jerry/anaconda3/envs/stl-stage1/bin/python \
  scripts/analyze_stage1_pilot.py

env PYTHONNOUSERSITE=1 PYTHONPATH=src MUJOCO_GL=egl \
  /home/jerry/anaconda3/envs/stl-stage1/bin/python \
  scripts/plot_stage1_pilot.py
```

The figures do not alter the frozen statistical protocol. Learning-curve
seed ranges are descriptive, not confidence intervals, and native/STL learner
costs retain different units.
