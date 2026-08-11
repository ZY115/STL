# Stage I exact-scale preflight evidence

This directory retains only compact, reviewable evidence from the excluded
engineering preflight. The preflight used `gold_stl_cost`, training seed
`20260811`, ten vector environments, 10,000 steps per epoch, 100,000 CUDA
transitions, fixed `epoch-10.pt`, and ten deterministic gold-STL evaluations.

`summary.json` records throughput, VRAM, disk projections, routing/oracle/RTAMT
checks, and the two pre-rollout failures that were corrected. The raw OmniSafe
run, checkpoint, attempt manifests, and evaluation CSV remain local and ignored.
`dry_run_15_job_manifest.json` is the no-training plan for the frozen 15-job
matrix.

This seed and all ten evaluation episodes are excluded from Stage I inference.
These files do not support a behavioral or convergence claim.
