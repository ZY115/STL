# Stage I Environment Setup

## Status

The Stage I environment was installed and verified on 2026-07-29.

The environment is named `stl-stage1`. It is isolated from existing ROS and Isaac
Python paths and uses CPU-only PyTorch because a GPU is not required for the
environment-inspection milestone.

## Host

- Operating system: Ubuntu 22.04.5 LTS, Linux 6.8.0-124-generic, x86-64
- CPU: Intel Core i9-14900KF, 32 logical CPUs
- Memory: 62 GiB
- Git: 2.34.1
- GCC: 12.3.0
- CMake: 3.22.1
- FFmpeg: 4.4.2
- NVIDIA status: the installed driver was not usable by `nvidia-smi` during setup

The CPU setup is sufficient for the smoke test, trajectory collection, RTAMT
reference evaluation, and initial diagnosable tests. GPU setup is deferred until
training performance makes it necessary.

## Pre-existing and newly installed components

The following host components already existed and were not changed:

- Ubuntu, Git, GCC, CMake, FFmpeg, EGL/OpenGL, GLFW, GLEW, and Boost;
- the Conda installation at `/home/jerry/anaconda3`;
- unrelated Conda environments named `omnisafe`, `osrl`, and others.

No `apt` package was installed or upgraded. The only new environment is:

```text
/home/jerry/anaconda3/envs/stl-stage1
```

All Python packages listed below were installed into this dedicated environment.
Existing environments were inspected only to avoid accidental reuse and were
not modified.

## Core versions

| Component | Installed version | Source |
|---|---:|---|
| Python | 3.8.20 | Conda defaults |
| PyTorch | 2.4.1+cpu | Official PyTorch CPU wheel index |
| NumPy | 1.23.5 | PyPI |
| Gymnasium | 0.28.1 | Required by Safety-Gymnasium 1.0.0 |
| Gymnasium-Robotics | 1.2.2 | Required by Safety-Gymnasium 1.0.0 |
| MuJoCo | 2.3.3 | Required by Safety-Gymnasium 1.0.0 |
| Safety-Gymnasium | 1.0.0 | Official PyPI release / repository tag `v1.0.0` |
| OmniSafe | 0.5.0 | Official PyPI release / repository tag `v0.5.0` |
| RTAMT | 0.3.5 | Official PyPI release |

No editable source checkout is used by this environment. Package versions, rather
than mutable repository working trees, identify the installed code. The complete
resolved environment is stored in `environment.stage1.yml`.

## Commands used on the successful installation

The successful installation sequence was:

```bash
/home/jerry/anaconda3/bin/conda create \
  -n stl-stage1 \
  python=3.8.20 \
  pip=24.2 \
  setuptools=75.1.0 \
  wheel=0.44.0 \
  -y

/home/jerry/anaconda3/envs/stl-stage1/bin/python -m pip install \
  --index-url https://download.pytorch.org/whl/cpu \
  torch==2.4.1+cpu

PYTHONNOUSERSITE=1 \
/home/jerry/anaconda3/envs/stl-stage1/bin/python -m pip install \
  numpy==1.23.5 \
  safety-gymnasium==1.0.0 \
  omnisafe==0.5.0 \
  rtamt==0.3.5

/home/jerry/anaconda3/bin/conda env config vars set \
  -n stl-stage1 \
  PYTHONNOUSERSITE=1 \
  PYTHONPATH= \
  MUJOCO_GL=egl
```

The lock file contains 91 exact pip distributions plus the exact Conda package
versions resolved on the successful host.

## Create or activate

To recreate the environment:

```bash
cd /home/jerry/Desktop/STL
conda env create -f environment.stage1.yml
conda activate stl-stage1
```

For the already installed environment:

```bash
conda activate stl-stage1
```

Activation sets:

```text
PYTHONNOUSERSITE=1
PYTHONPATH=
MUJOCO_GL=egl
```

The empty `PYTHONPATH` is intentional. The host shell globally injects ROS 2 and
Isaac Gym/Sim Python paths, including Python 3.10 packages, into new processes.
Those paths must not enter this Python 3.8 experiment.

`MUJOCO_GL=egl` enables verified off-screen rendering without an accessible X11
display. No additional Ubuntu packages were required.

## Verified checks

| Check | Observed result |
|---|---|
| Dependency consistency | `pip check`: `No broken requirements found.` |
| Core imports | Safety-Gymnasium, MuJoCo, OmniSafe, RTAMT, and PyTorch imported |
| RTAMT reference calculation | `eventually[0:2](d >= 1.0)` produced robustness `0.2` on the test trace |
| Benchmark horizon | A seeded random episode ran 1000 steps and ended with `truncated=True` |
| Safe-RL API | Reward and native cost were returned as separate scalar values |
| OmniSafe integration | `PPOLag` constructed successfully on `SafetyPointGoal1-v0` using CPU |
| Off-screen rendering | EGL produced `uint8` RGB frames with shape `(256, 256, 3)` |
| Video output | ImageIO/FFmpeg produced H.264 MP4 files |
| Environment isolation | No ROS or Isaac path remained in `sys.path` after activation |

OmniSafe was only constructed, not trained.

## Problems encountered and resolutions

### Global Python path contamination

The host shell supplied ROS 2 and Isaac Gym/Sim paths through `PYTHONPATH`,
including Python 3.10 packages. They caused an unrelated ROS package to appear
in an initial pip dependency check.

Resolution: activation clears `PYTHONPATH` and sets `PYTHONNOUSERSITE=1`. The
isolated dependency check then passed.

### Default X11 rendering

The first RGB render attempt used GLFW and failed to open display `:1`.

Resolution: `MUJOCO_GL=egl` was tested successfully and saved in the Conda
environment variables.

### RTAMT test-data schema

The first test invocation used an incorrect offline dataset shape and then
omitted RTAMT's required `time` key.

Resolution: the documented discrete-time dictionary form was used:

```text
{"time": [0, 1, 2], "d": [0.2, 0.5, 1.2]}
```

The corrected reference calculation passed. This was a test-script input error,
not an RTAMT installation failure.

### NVIDIA driver

`nvidia-smi` could not communicate with the installed NVIDIA driver. No attempt
was made to alter the host driver because the current environment inspection
and diagnosable CPU tests do not require a GPU.

## Known non-blocking warning

Importing Safety-Gymnasium emits a Gymnasium-Robotics warning about reward changes
in three Adroit Hand environments. Stage I uses `SafetyPointGoal1-v0`, so the
warning does not affect the selected benchmark.

## 2026-08-05 reproducibility recheck

The existing environment was converged to `environment.stage1.yml` with:

```bash
conda env update -n stl-stage1 -f environment.stage1.yml --prune
```

All locked dependencies were already satisfied. With the documented
`PYTHONPATH` isolation applied, `pip check` again reported
`No broken requirements found`. The local Stage I project was then installed as
an editable package without adding dependencies:

```bash
python -m pip install --no-deps --no-build-isolation -e .
```

The benchmark/public-distance smoke test and the original 23 signal, monitor,
oracle, fixture, and RTAMT agreement tests passed. The locked PyTorch build
remains CPU-only; GPU training was not part of this milestone.

## 2026-08-05 visualization-runner verification

No package installation was required. Pillow 10.4.0, ImageIO 2.35.1, and
ImageIO-FFmpeg 0.5.1 were already present in `environment.stage1.yml`; they are
now also declared in `pyproject.toml` because the runnable video path imports
them directly.

The following public entry points were tested:

```bash
./scripts/visualize_stage1.sh --render none --policy random --max-steps 5
./scripts/visualize_stage1.sh --render video --policy scripted --seed 44
./scripts/visualize_stage1.sh --render human --policy scripted --seed 44
```

The launcher chooses EGL for headless/video execution and overrides the Conda
default with GLFW for the native X11 viewer. The full scripted run triggered at
sample 75 and recovered at sample 130. The annotated video contained 147 H.264
`yuv420p` frames. The native window opened, updated its STL overlay, and exited
automatically after 146 actions. The expanded suite of 27 tests passed.

The first native-viewer run inherited GLFW vertical synchronization and took
several minutes in the available desktop session. The runner now disables
viewer VSync and applies its own target-frame delay; the verified full run took
about 7 seconds. This affects display speed only, not simulator steps or
monitor semantics.

## 2026-08-10 OmniSafe-wrapper verification

No package installation or host change was required for the wrapper milestone.
The existing locked CPU environment executed:

```bash
./scripts/run_omnisafe_smoke.sh
```

The run registered all three Stage I conditions, verified one real positive STL
cost, and completed a 64-transition, one-epoch PPO-Lagrangian rollout and
update with two vector environments. Eleven new wrapper tests passed, bringing
the complete suite to 38 tests. Exact evidence and limitations are recorded in
`docs/omnisafe_integration_report.md` and
`results/integration_smoke/summary.json`.

The environment remains CPU-only (`torch 2.4.1+cpu`, no CUDA build). This was
sufficient for the bounded interface smoke and does not establish GPU training
readiness.

## Removal

If this dedicated environment is no longer needed:

```bash
conda env remove -n stl-stage1
```

Do not remove either the existing `omnisafe` or `osrl` environment; they predated
this project setup and may belong to other work.
