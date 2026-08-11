# Stage I CUDA enablement report

- **Date:** 2026-08-11
- **Decision:** D32
- **Result:** CUDA training path passed
- **Full Stage I pilot started:** no
- **Evidence:** `results/cuda_validation/summary.json`

## Root cause of the earlier unavailable state

The machine GPU and driver are healthy. The `stl-stage1` environment contained
`torch 2.4.1+cpu`, so `torch.cuda.is_available()` correctly returned false even
though `nvidia-smi` could see the RTX 4090. No driver repair was required.

## Installed and verified stack

| Component | Verified value |
|---|---|
| GPU | NVIDIA GeForce RTX 4090 |
| VRAM | 24,564 MiB |
| Compute capability | 8.9 |
| NVIDIA driver | 560.35.03 |
| Driver CUDA compatibility | 12.6 |
| PyTorch | 2.4.1+cu124 |
| PyTorch CUDA runtime | 12.4 |
| cuDNN | 9.1.0 |

The official PyTorch CUDA 12.4 wheel bundles the required CUDA runtime
libraries, so a standalone system `nvcc` toolkit is not needed for this project.
The driver is new enough to execute the CUDA 12.4 wheel.

## Validation layers

`./scripts/validate_cuda_stage1.sh` checks:

1. driver, GPU identity, VRAM and compute capability;
2. PyTorch CUDA runtime and a 1024×1024 CPU/GPU matrix comparison;
3. observation, reward, native cost, STL cost, and selected cost tensors on
   `cuda:0` through the real Stage I wrapper;
4. one 2000-transition, full-horizon PPOLag update;
5. a real deadline violation with mean `STLCost=0.5` and selected cost `0.5`;
6. Lagrange multiplier update and checkpoint output;
7. `pip check` with no broken requirements.

OmniSafe enables deterministic algorithms. CUDA process launchers therefore
set `CUBLAS_WORKSPACE_CONFIG=:4096:8`; without it, cuBLAS correctly refuses a
deterministic linear layer operation.

After this gate, the full task/native/STL 10k sanity was rerun on `cuda:0` and
passed exact routing, final-checkpoint, direct-oracle, and RTAMT checks. The
frozen Stage I pilot backend is now `cuda:0` for all conditions.

## Interpretation

CUDA is fully usable for Stage I training. This validation does not establish a
training-speed improvement: the tiny sanity uses a small 64×64 network and is
dominated by simulator and kernel-launch overhead. A representative throughput
measurement should be recorded before estimating the duration of all fifteen
1M-transition runs.
