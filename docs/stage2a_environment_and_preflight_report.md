# Stage II-A Environment and CUDA Preflight Report

> **2026-08-14 owner update:** this report preserves the historical D41 failures.
> D49 now authorizes guarded continuation with preserved attempts, local diagnosis
> and one clean retry before escalation. Held-out evaluation separately waits for
> the D51 alias amendment and delta review.

- **Prepared:** 2026-08-12
- **Environment:** `/home/jerry/anaconda3/envs/stl-stage2-offline`
- **Scope:** train/validation only; no held-out Gold evaluation

## Construction and isolation

The first attempt to create a clean Python environment and install the official
PyTorch `2.4.1+cu124` wheel failed because the currently reachable NVIDIA wheel
index did not provide the wheel's exact historical dependency
`nvidia-cudnn-cu12==9.1.0.70`. This was a package-index availability issue, not
a CUDA-device failure.

The successful route cloned the already verified `stl-stage1` environment to a
separate `stl-stage2-offline` environment, then installed only the frozen Stage
II dependencies. The Stage I environment and its completed pilot were not
modified. `pip check` reports no broken requirements.

## Exact tested versions

| Component | Version |
|---|---|
| Python | 3.8.20 |
| PyTorch | 2.4.1+cu124 |
| CUDA build / device | 12.4 / NVIDIA GeForce RTX 4090 |
| OmniSafe | 0.5.0 |
| Safety-Gymnasium | 1.0.0 |
| RTAMT | 0.3.5 |
| Transformers | 4.46.3 |
| Sentence-Transformers | 3.2.1 |
| SentencePiece | 0.2.0 |
| NumPy / SciPy | 1.23.5 / 1.10.1 |
| scikit-learn | 1.3.2 |
| typeguard / pytest | 4.4.0 / 8.3.5 |

An actual `1024 x 1024` CUDA matrix multiplication completed with finite
outputs. Training enforces `CUBLAS_WORKSPACE_CONFIG=:4096:8`, disables fused
non-deterministic attention paths and calls
`torch.use_deterministic_algorithms(..., warn_only=False)`.

## Frozen pretrained resources

| Model | Revision | License from pinned model card | Card SHA-256 | Config SHA-256 |
|---|---|---|---|---|
| `google-t5/t5-base` | `a9723ea7f1b39c1eae772870f3b547bf6ef7e6c1` | Apache-2.0 | `c43c23f205b6839a6adb10f0757265f76c1c6f96b7793a4e53582d3a61cbfb23` | `46dd7cb62d29c81fb551e0ef1ea274c24a46ba441eeb948897706252933df033` |
| `sentence-transformers/all-MiniLM-L12-v2` | `a50ef00143b4d5391434df20ae11632588ac25be` | Apache-2.0 | `a9c5a266121350036e45a733802ac6a8567604be365de01e40aa4b43e5ee594d` | `bc451f333af67312ba0de5018ef1c9ba663cb18549443e568f0bd35262dc1c48` |

The model revisions are recorded from the local Hugging Face cache and again
inside each run summary. No paid API or proprietary model is used.

## Executed preflight

All three trainable methods completed a CUDA forward pass, backward pass, one
optimizer update, finite validation metrics and both `latest.pt` and `best.pt`
checkpoint writes:

| Method | Parameters | Peak allocated CUDA memory in minimal update |
|---|---:|---:|
| T5 formal translator | about 222.9M | 6.7--7.1 GB |
| MiniLM current-observation direct | 33,409,537 | 0.74 GB |
| MiniLM + GRU history direct | 33,574,659 | 0.74 GB |

The tiny-update accuracies are not research results. Their purpose is limited
to exercising data loading, causal inputs, model output, loss, checkpoint and
metric paths.

## T5 JSON tokenizer failure and repair

The first real formal run found that the stock T5 tokenizer did not losslessly
decode JSON braces and commas. After two epochs the training loss was near
zero, but validation output could never be parsed (`compilable_rate=0`). That
run was stopped and preserved under
`results/stage2a_failed_json_tokenizer/`; it is excluded from comparison.

The project now adds the five regular structure tokens `{`, `}`, `,`, `[` and
`]`, verifies a JSON encode/decode probe before training, and does not shrink
T5's original padded embedding table. No validation/test-specific output is
repaired. In the replacement real-scale run, the first epoch completed 313
optimizer updates with `compilable_rate=1.0` and typed-AST exact validation
accuracy `0.375`, confirming that the structural-output path is executable.

The first replacement process later ended outside Python exception handling.
The kernel recorded machine-check events at `22:52:01` and `22:57:29`, followed
by a `pt_autograd_0` segmentation fault in `libstdc++` at `23:03:27`; it
recorded no CUDA Xid, OOM or memory exhaustion. The two completed epochs and
predictions are preserved under `results/stage2a_hardware_failure/`, but their
duplicate checkpoint weights were pruned and the attempt is excluded.

A clean retry started from scratch. It completed two epochs and reproduced the
first attempt's finite train/validation behavior: typed-AST exact accuracy
`0.375`, compiled-STL exact accuracy `0.375`, and compilable rates `1.0` then
`0.9167`. At `23:15:31`, the kernel logged a third machine-check event. This
satisfied the prospective repeated-hardware-failure stop condition. The retry
was interrupted with SIGINT at a checkpoint-safe boundary rather than allowed
to generate research results on an unstable host. Its manifest, progress,
best/latest checkpoints and hashes remain in
`results/stage2a_hardware_failure_retry/formal/seed-6101/` for diagnosis only;
they are explicitly not accepted baseline results. The normal
`results/stage2a/formal/seed-6101/` path is clean for a from-scratch restart only
after D41 passes.

The runner now checkpoints the DataLoader RNG state and optimizer-update count,
retains the earliest best checkpoint on metric ties, and records a clean
`interrupted` manifest for future SIGINT/SystemExit events. The Stage II-A
matrix and all new GPU RL cells remain stopped until the host-level MCE source
is investigated. CPU-only spatial replay, artifact generation and tests may
continue.

## Hardware stop evidence and recovery gate

The affected host uses an Intel Core i9-14900KF and Linux
`6.8.0-124-generic`. The available unprivileged kernel log does not expose a
decoded MCA bank/status, and `rasdaemon`, `ras-mc-ctl`, `mcelog` and
`coredumpctl` are not installed. Therefore the repository does not assign the
fault to the GPU, CPU core, RAM or motherboard. Before resuming research
training, an administrator should collect decoded hardware-error evidence,
verify current motherboard BIOS and CPU microcode, restore vendor-default
CPU/RAM settings if any overclock/XMP/undervolt is active, and run independent
CPU and memory stability checks. A subsequent clean stress check and one
discarded formal epoch must finish with no new MCE, segfault, CUDA Xid, OOM or
non-finite value before the frozen matrix can resume.

## Commands

The following commands are recorded for reproducibility. **Do not run them on
this host until D41's hardware recovery gate passes.**

Run or resume one cell:

```bash
/home/jerry/anaconda3/envs/stl-stage2-offline/bin/python \
  scripts/train_stage2a.py --method formal --seed 6101 --output-root results/stage2a
```

Run/resume the frozen nine-cell train/validation matrix:

```bash
/home/jerry/anaconda3/envs/stl-stage2-offline/bin/python \
  scripts/run_stage2a_train_validation.py --output-root results/stage2a
```

These commands do not run held-out evaluation. That remains blocked by the
independent-human-review gate.
