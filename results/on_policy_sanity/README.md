# PPOLag on-policy positive-cost sanity

`summary.json` is the tracked machine-readable record for the 2026-08-11
pre-main engineering gate. It records the explicit cost limit, rollout/horizon
alignment, package versions, progress hash, independent cost metrics, and gate
checks.

The raw OmniSafe run directory and checkpoints are reproducible bulk outputs
and remain ignored. Re-run with:

```bash
./scripts/run_on_policy_sanity.sh
```

This is a one-epoch plumbing sanity, not a trained-policy comparison or safety
result.
