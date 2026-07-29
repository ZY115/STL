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

## Removal

If this dedicated environment is no longer needed:

```bash
conda env remove -n stl-stage1
```

Do not remove either the existing `omnisafe` or `osrl` environment; they predated
this project setup and may belong to other work.
