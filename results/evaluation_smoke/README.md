# Common checkpoint evaluator smoke

This directory tracks a three-episode interface validation of the common Stage
I checkpoint evaluator. `episodes.csv` contains one compact record per episode;
`summary.json` contains aggregate metrics and the checkpoint/rule identity.

Every trajectory was re-evaluated by the independent direct oracle. Completed
windows were also checked with RTAMT. The smoke checkpoint came from the
one-epoch on-policy sanity and is not a trained policy or performance result.

Large future trajectory JSONL files remain ignored. The evaluator is run with:

```bash
./scripts/evaluate_stage1_checkpoint.sh \
  --run-dir PATH_TO_OMNISAFE_RUN \
  --checkpoint epoch-N.pt \
  --episodes 100 \
  --seed-start 10000 \
  --max-episode-steps 1000 \
  --output-dir PATH_TO_OUTPUT
```
