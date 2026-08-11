# OmniSafe Integration Smoke Evidence

`summary.json` is the tracked machine-readable completion record for the
2026-08-10 wrapper/integration milestone.

The smoke has two parts:

1. a real `SafetyPointGoal1-v0` scripted validation trajectory that produces
   one positive terminal-unresolved STL cost and confirms selected-cost routing;
2. a 64-transition, one-epoch, one-update OmniSafe PPO-Lagrangian CPU run using
   two vector environments.

Bulk OmniSafe logs and checkpoints are generated below `omnisafe_runs/` and are
ignored by Git. The tracked summary stores their relevant metrics and the
`progress.csv` SHA-256 hash.

This evidence is an interface smoke test, not an RL performance or safety
result. See `docs/omnisafe_integration_report.md` for interpretation and the
exact reproduction command.
