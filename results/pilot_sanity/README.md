# Stage I three-condition pilot sanity evidence

This directory contains the compact evidence for the engineering-only sanity
gate run on 2026-08-11.

The final run used one non-pilot seed (`20260811`), `cuda:0`, 10,000 transitions
per condition, two vector environments, and five rollouts of one complete
1000-step episode per vector slot. It trained task-only, native-cost, and
gold-STL-cost PPOLag
conditions and evaluated each fixed final checkpoint deterministically on the
same seeds `13000--13002` with the common gold-STL evaluator.

`summary.json` records frozen config hashes, package versions, all epoch-level
cost-routing metrics, final checkpoint hashes, evaluation aggregates, and gate
checks. `evaluation/*/episodes.csv` and `evaluation/*/summary.json` are compact
paired-evaluation records. Bulk OmniSafe logs and checkpoints remain ignored by
Git but are retained locally under `omnisafe_runs/`.

Reproduce with:

```bash
./scripts/run_stage1_pilot_sanity.sh
```

This is not a pilot behavioral comparison, convergence evidence, or a safety
claim. Its three episodes per condition must not be tested against the D31
scientific target. The full 1M-transition runs were not started.
