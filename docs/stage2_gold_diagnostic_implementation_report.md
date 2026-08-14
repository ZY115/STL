# D38 Gold Learner-Cost Diagnostic Implementation Report

- **Prepared:** 2026-08-12
- **Authority:** D38, implementation details D40
- **Execution status:** implementation/static tests complete; no 300k cell started; D41 hardware-blocked
- **Gold specification/evaluator:** unchanged `br-v0-001` binary oracle

> **2026-08-14 update:** D52 requires a mechanism analysis of existing D47/D48
> artifacts before this unchanged matrix runs. No C2 or extra free search is
> authorized. D49 replaces the absolute compute pause with guarded continuation.

## Implemented scope

The project-owned runtime leaves OmniSafe 0.5.0 installed files unchanged. It
adds a rollout adapter that preserves reward timeout bootstrap but sets only
the cost bootstrap to zero when `stl_terminal_unresolved` has already settled
the pending Gold obligation. An executable probe verifies reward bootstrap `3`
and cost bootstrap `0` on the same truncated transition.

Two and only two learner-cost candidates are implemented:

- **C0:** the unchanged binary missed-obligation event;
- **C1:** the frozen causal mean of distance deficit and deadline urgency,
  with cost 1 on an actual miss and 0 while inactive.

C1 is a training surrogate, not an STL truth value. Native cost, C0 Gold cost,
C1 dense cost and selected learner cost are logged independently. The same
augmented policy observation is used for task, C0 and C1 conditions.

The diagnostic PPO-Lagrangian subclass adds the frozen `3e-5` actor-LR floor
and per-epoch positive-cost fraction, cost-value RMSE/means, raw reward-
advantage scale, actor-scale cost advantage, separate reward/cost actor gradient
norms, multiplier, LR, triggers, misses and goal events.

## Frozen matrix and budget order

The matrix uses new seeds `7307`, `8419`, `9521`; 300,000 transitions per cell;
one task control; and C0/C1 crossed with `lambda_init=0.001/0.1`. Screening uses
50 paired evaluation seeds `23001..23050` per training seed.

`configs/stage2_gold_diagnostic/budgets.json` intentionally does not exist yet.
Before any C0/C1 training, all three new task controls must train and be
evaluated. Budget derivation then requires exactly 150 episodes, the identical
50 evaluation seeds for each training seed, and exactly 1,000 actions in every
episode. C0 and C1 limits are separately frozen at 70% of their respective
task-control means. A numeric value is never copied between their different
units.

## Resumption and failure preservation

Each condition/seed writes immutable `attempt-NNNN` evidence plus a latest cell
manifest. A successful cell is skipped on rerun; a failed, interrupted or
native-crashed attempt is preserved and the next launch receives a new attempt
directory. The matrix launcher runs task controls first, freezes the budgets,
reloads their hash, and only then permits the 12 cost cells.

After D41 is cleared, the required order is:

```bash
env PYTHONNOUSERSITE=1 PYTHONPATH=src MUJOCO_GL=egl \
  /home/jerry/anaconda3/envs/stl-stage2-offline/bin/python \
  scripts/run_gold_cost_diagnostic.py \
  --condition task_only_control --seed 7307 --dry-run

env PYTHONNOUSERSITE=1 PYTHONPATH=src MUJOCO_GL=egl \
  /home/jerry/anaconda3/envs/stl-stage2-offline/bin/python \
  scripts/run_gold_cost_diagnostic_matrix.py --phase task-controls

# Inspect frozen budgets, then preflight one C0 and one C1 cell before full cost cells.
env PYTHONNOUSERSITE=1 PYTHONPATH=src MUJOCO_GL=egl \
  /home/jerry/anaconda3/envs/stl-stage2-offline/bin/python \
  scripts/run_gold_cost_diagnostic_matrix.py --phase cost-cells
```

The all-in-one `--phase all` route exists for resumption after all preflight
gates are documented, but it is not a substitute for those gates.

## Current gate

Static config construction confirms the dry-run contract is 10,000 transitions,
one epoch and one update iteration; the real contract is 300,000 transitions,
30 epochs and 40 update iterations. Routing, cost, bootstrap, LR and attempt
tests pass as part of the repository suite.

No GPU dry run or 300k diagnostic result is claimed. Repeated host MCEs triggered
D41 before this branch could execute. The next legitimate action is hardware
recovery, not budget invention or CPU substitution. If no C0/C1 cell later
passes the predeclared screening gate, Stage II-B must stop.
