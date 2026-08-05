# Stage I Visualization Runner

## Purpose and scope

The repository now has a repeatable launch path for viewing the validated
environment-signal-monitor chain. It is an evaluation and debugging surface,
not an RL training result.

The default run uses:

- `SafetyPointGoal1-v0`;
- the public `hazards_lidar` distance signal;
- the fixed `d_warn=0.45`, `d_safe=0.55`, `K=79` monitor;
- a deterministic approach/escape controller that deliberately creates one
  visible warning and recovery episode;
- separate native reward, native cost, and STL cost logging.

The scripted controller uses privileged simulator geometry to select and steer
toward a hazard. This is permitted only for a diagnosable visualization. It is
not a learned policy, does not feed geometry to the monitor, and must not be
reported as a Safe RL result.

## One-command live launch

From the repository root:

```bash
./scripts/visualize_stage1.sh
```

The launcher finds the `stl-stage1` Conda environment, clears contaminating
global Python paths, selects the GLFW backend, and opens the native MuJoCo
window. The right-side overlay shows:

- current policy/controller phase;
- environment step;
- public distance `d_t`;
- monitor state (`INACTIVE`, `PENDING`, or `OVERDUE`);
- remaining deadline steps;
- warning, recovery, or violation events;
- cumulative reward, native cost, and STL cost as separate values.

The default scripted run uses seed 44. It stops after the warning episode has
recovered and the public distance exceeds 0.9. On the verified machine it
completed after 146 actions.

## Annotated MP4 and headless modes

Create an annotated MP4 without opening a desktop window:

```bash
./scripts/visualize_stage1.sh --render video
```

Run the same chain without rendering:

```bash
./scripts/visualize_stage1.sh --render none
```

Run a seeded random policy instead of the scripted demonstration:

```bash
./scripts/visualize_stage1.sh --policy random --seed 11 --max-steps 500
```

Use `--help` for all options. The Python entry point is also directly usable
inside the activated environment:

```bash
python scripts/run_stage1_demo.py --render human
```

The Python entry point selects `MUJOCO_GL=glfw` for live rendering and
`MUJOCO_GL=egl` for video/headless execution before MuJoCo is imported.

## Output contract

Unless `--output-dir` is supplied, each run writes to a timestamped directory
under:

```text
results/visualization/
```

Each run produces:

- `trajectory.csv`: reset sample plus every action/sample, with action,
  reward, native cost, STL cost, monitor events, and cumulative values;
- `summary.json`: rule parameters, exit reason, event counts, minimum distance,
  software versions, renderer backend, and artifact names;
- `stage1_demo.mp4`: only in `--render video` mode.

Generated run directories and CSV tables are ignored by Git. The small verified
reference video, its summary, and the visualization directory README are kept as
durable smoke-test evidence.

If a run stops because of the runner's `--max-steps` limit while the environment
itself has not terminated, the summary uses `exit_reason=max_steps`. A pending
obligation at that external cutoff is recorded as `collector_cutoff_pending`;
it is not silently converted into an environment terminal event or STL cost.

## Verified behavior

Verified on 2026-08-05 with the locked `stl-stage1` environment:

| Check | Result |
|---|---|
| Headless environment/monitor/log path | Passed |
| Annotated EGL MP4 | H.264, `yuv420p`, 147 frames |
| Native GLFW live window | Opened, updated, and exited automatically |
| Scripted warning trigger | sample 75, `d_t=0.446` |
| Scripted recovery | sample 130, `d_t=0.550` |
| Deadline result | recovered with 24 steps remaining; no STL cost |
| Automated tests | 27 passed |

The native X11 viewer is slower than EGL encoding on this machine. Disabling
viewer vertical synchronization removed the original long blocking behavior;
the final complete live scripted regression took about 7 seconds in the tested
desktop session.

## Remaining boundary

This runner proves that the environment, public signal, monitor, visualization,
and artifact logging can run together. It does not implement the OmniSafe
STL-cost wrapper, train PPO-Lagrangian, load a learned checkpoint, or establish a
safety improvement. Those remain in the next integration milestone.
