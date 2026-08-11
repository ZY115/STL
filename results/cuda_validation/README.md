# Stage I CUDA validation evidence

This directory records the CUDA enablement gate for the verified `stl-stage1`
environment. The compact `summary.json` contains driver/device metadata, a
CPU/GPU matrix check, Stage I wrapper tensor-device checks, a full-horizon
positive-STL-cost PPOLag update, dependency status, config hashes, and the
checkpoint/progress evidence.

Reproduce with:

```bash
./scripts/validate_cuda_stage1.sh
```

Bulk CUDA validation checkpoints and logs remain ignored under
`on_policy_runs/`. This gate does not start the full Stage I pilot and does not
constitute a safety or learning result.
