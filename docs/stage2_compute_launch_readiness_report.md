# Stage II Compute Launch Readiness and Stop Report

- **Date:** 2026-08-12
- **Outcome:** software path ready through minimal CUDA updates; research launch blocked by repeated host MCE

## Passed software gates

- separate `stl-stage2-offline` environment and pinned model revisions;
- CUDA visible on RTX 4090 and finite matrix multiplication;
- T5 formal, MiniLM current and MiniLM+GRU history each completed forward,
  backward, optimizer update, validation and checkpoint preflight;
- T5 JSON output is lossless after regular structure-token registration;
- immutable config/data/source/model hashes and resumable checkpoints;
- D38 task/C0/C1 routing, settled cost bootstrap, diagnostic logs and
  attempt-preserving runner implemented;
- repository test suite passes; held-out labels remain closed.

## Failed host-stability gate

Kernel evidence during full T5 training:

| Time | Evidence |
|---|---|
| 22:52:01 | machine-check event logged |
| 22:57:29 | machine-check event logged |
| 23:03:27 | `pt_autograd_0` segfault in `libstdc++.so.6.0.34` |
| 23:15:31 | new machine-check event during clean retry |

The clean retry completed 626 optimizer updates over two epochs with finite
metrics and about 12.46 GB peak allocated CUDA memory before the repeated MCE
stop. No CUDA Xid, OOM or non-finite metric was logged. The available
unprivileged evidence is insufficient to assign the fault to GPU, CPU, RAM or
motherboard.

No additional matching kernel event was logged between `23:15:32` and the
final CPU-only artifact/test audit at `23:49`. This does not clear the hardware
gate because it did not reproduce the failed training load.

There is currently no active Stage II training process and no accepted full
baseline result. Partial checkpoints are diagnosis-only and are archived under
`results/stage2a_hardware_failure*/`; the normal matrix path is empty so a
post-D41 run starts from scratch.

## Required recovery evidence

An administrator must collect decoded MCA/firmware evidence, check BIOS and CPU
microcode, remove any overclock/XMP/undervolt during diagnosis, and run
independent CPU and RAM stability tests. Then run one discarded formal epoch.
The compute gate passes only if that interval has no new MCE, segfault, CUDA
Xid, OOM or non-finite value and produces a finite checkpoint/progress record.

Only after this gate may the frozen Stage II-A matrix resume, followed by the
Gold task-control dry run and matched-budget sequence. This report authorizes
neither held-out evaluation nor the five-seed 1M confirmatory study.
