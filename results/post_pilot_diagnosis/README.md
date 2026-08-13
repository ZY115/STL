# Post-pilot CPU Replay Diagnosis

This directory contains a diagnostic replay of the existing 15 frozen final
checkpoints. It performs no training and no checkpoint selection.

The full matrix replays 100 deterministic evaluation episodes for every
condition/training-seed checkpoint and requires episode counts, returns, native
costs and minimum distances to match the previously frozen episode tables.
The two representative evaluation cases were selected from the pre-existing
paired results before replay; all three conditions are then exported for both
cases.

Reproduce with:

```bash
env PYTHONNOUSERSITE=1 PYTHONPATH=src MUJOCO_GL=egl \
  /home/jerry/anaconda3/envs/stl-stage1/bin/python \
  scripts/diagnose_stage1_trajectories.py
```

`runtime_contract.json` is generated separately by:

```bash
env PYTHONNOUSERSITE=1 PYTHONPATH=src \
  /home/jerry/anaconda3/envs/stl-stage1/bin/python \
  scripts/inspect_omnisafe_runtime.py
```

The tracked compact package contains aggregate/checkpoint tables,
representative per-step trajectories and provenance, two PNG figures, runtime
contract evidence, and hashes. Existing raw training/checkpoint trees remain
ignored and are referenced by path and SHA-256.
