# Environment Inspection Artifact Record

This directory contains the local outputs from the completed
`SafetyPointGoal1-v0` environment-inspection milestone on 2026-07-29.

Git tracks this file and `summary.json`. Raw CSV trajectories and MP4 renderings
are handled separately: CSV trajectories remain ignored, while the two compact
MP4 renderings are tracked as visual smoke-test evidence.

## Local artifacts

| File | Purpose | Size |
|---|---|---:|
| `random_seed_11.csv` | 1000-step seeded random trajectory | 183455 bytes |
| `random_seed_22.csv` | 1000-step seeded random trajectory | 184158 bytes |
| `random_seed_33.csv` | 1000-step seeded random trajectory | 184012 bytes |
| `scripted_hazard_approach_seed_44.csv` | 500-step trajectory that enters native hazard cost | 78397 bytes |
| `random_seed_11_first_120_steps.mp4` | EGL render of the first random rollout | 35429 bytes |
| `scripted_hazard_approach_seed_44.mp4` | EGL render of the scripted rollout | 168210 bytes |

`summary.json` stores the associated statistics and SHA-256 hashes. A copied CSV
artifact can be checked against that record even though the raw trajectory
tables are not stored in Git. The tracked MP4 files can be checked directly.

## Artifact retention policy

The two videos are small and provide direct evidence that EGL off-screen
rendering worked, so they are retained in Git. The larger machine-generated CSV
tables are not yet stable test fixtures and remain ignored until the rule
parameters and fixture format are frozen.

If a later monitor test requires a trajectory fixture, select and document a
minimal fixture deliberately rather than treating all smoke-test output as a
permanent test dataset.
