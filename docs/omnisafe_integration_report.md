# Stage I OmniSafe Wrapper and Integration Smoke Report

## Status

- **Milestone:** OmniSafe wrapper and bounded integration smoke
- **Completed:** 2026-08-10
- **Result:** completion gate passed
- **Scope:** cost routing, temporal observation augmentation, vectorized monitor
  lifecycle, logging, and one minimal PPO-Lagrangian update
- **Not in scope:** main training, comparison between conditions, safety
  improvement, statistical evaluation, or language translation

## Implemented interface

The project now registers three OmniSafe environment IDs:

| Condition | Environment ID | Cost returned to learner |
|---|---|---|
| Task only | `Stage1SafetyPointGoal1TaskOnly-v0` | zero |
| Native safety | `Stage1SafetyPointGoal1NativeCost-v0` | native hazard cost |
| Temporal STL safety | `Stage1SafetyPointGoal1STLCost-v0` | binary STL event cost |

All three conditions use the same `SafetyPointGoal1-v0` task, native reward,
fixed distance signal, fixed monitor, and 63-dimensional policy observation.
The original 60-dimensional public observation is followed by:

```text
active_obligation
overdue_indicator
normalized_remaining_deadline
```

The selected algorithm cost changes between conditions, but `native_cost`,
`stl_cost`, and `selected_algorithm_cost` remain independent diagnostics in
every step and completed-episode log.

## Terminal and vectorized lifecycle

Safety-Gymnasium auto-resets vector environments. On a terminal or truncated
transition, the returned observation is already the next episode's reset
observation, while the actual last sample is in `info["final_observation"]`.
The wrapper therefore performs the following order independently for each
vector slot:

1. process the actual final observation with the current monitor;
2. apply termination or truncation semantics, including
   `terminal_unresolved`;
3. preserve the augmented final observation for OmniSafe value bootstrapping;
4. emit the terminal transition's STL cost and diagnostics;
5. reset only that slot's monitor from the new returned observation;
6. return the new observation with the new episode's temporal state.

This prevents a reset observation from being mistaken for the final sample and
prevents monitor state from crossing episode or vector boundaries.

OmniSafe 0.5.0 resets its on-policy adapter at the start of each rollout epoch.
The smoke runner therefore requires
`steps_per_epoch / vector_env_nums` to be an integer multiple of the configured
episode horizon. Main configurations must preserve this alignment so an epoch
boundary cannot externally reset and erase a pending obligation.

## Automated checks

`tests/test_omnisafe_wrapper.py` adds 11 wrapper-specific checks:

1. all three environment IDs are registered;
2. task/native/STL cost routing preserves both diagnostic costs;
3. reset inside the warning zone returns an already-active temporal state;
4. recovery clears the active policy state;
5. a deadline violation produces exactly one STL cost;
6. terminal-unresolved is evaluated from the final observation before reset;
7. all conditions have identical observation shape and dtype;
8. vector monitor states and resets are independent;
9. completed-episode logs retain native, STL, and selected costs separately;
10. the real environment preserves reward and native-cost transitions across
    the three conditions;
11. OmniSafe vector reset/step tensor shape and device contracts hold.

Together with the prior 27 tests, the complete suite contains 38 passing tests.

## Positive STL-cost routing probe

Before constructing the learner, the smoke runner uses the existing
privileged scripted controller only as a validation instrument. It runs the
real STL-cost environment with seed 44 and a deliberately short 100-step
horizon.

Observed result:

| Field | Result |
|---|---:|
| Actions | 100 |
| Warning triggers | 1 |
| Recoveries | 0 |
| Deadline violations | 0 |
| Terminal unresolved | 1 |
| Native cost total | 0 |
| STL cost total | 1 |
| Selected algorithm cost total | 1 |

The final pending observation retained its active temporal state for
bootstrapping, while the observation returned after auto-reset contained a
cleared state. This probe verifies a real positive STL cost and its selected
cost routing. It is not a learned policy or experimental result.

## PPO-Lagrangian smoke update

The runner then constructed OmniSafe 0.5.0 `PPOLag` with the STL-cost
environment and the following intentionally small CPU configuration:

| Setting | Value |
|---|---:|
| Vector environments | 2 |
| Total transitions | 64 |
| Steps per epoch | 64 |
| Environment steps per vector slot | 32 |
| Smoke-only episode horizon | 16 |
| Epochs | 1 |
| Update iterations | 1 |
| Batch size | 32 |
| Policy observation | `(63,)`, `float32` |

The rollout completed, one update iteration ran, all recorded values were
finite, separate cost metrics were written, and two checkpoints were created.
The policy rollout did not enter a warning episode, so its three cost totals
were all zero. This is acceptable for the interface gate: the preceding real
probe verifies the positive cost path, while the learner run verifies that
OmniSafe consumes the same selected-cost tensor surface and completes an
update. It does not show learning from violations or any safety improvement.

## Reproduction

From the repository root:

```bash
./scripts/run_omnisafe_smoke.sh
```

Equivalent explicit command:

```bash
env PYTHONNOUSERSITE=1 PYTHONPATH=src MUJOCO_GL=egl \
  /home/jerry/anaconda3/envs/stl-stage1/bin/python \
  scripts/run_omnisafe_integration_smoke.py
```

Configuration:

```text
configs/omnisafe_integration_smoke.yaml
```

Tracked machine-readable evidence:

```text
results/integration_smoke/summary.json
```

Raw OmniSafe `progress.csv`, configuration copies, and checkpoints are stored
below `results/integration_smoke/omnisafe_runs/` and intentionally ignored by
Git. The tracked summary records the progress hash, exact package versions,
configuration hash, registered IDs, checks, and key metrics.

## Environment and limitations

The smoke used the locked CPU environment:

| Component | Version |
|---|---:|
| Python | 3.8.20 |
| PyTorch | 2.4.1+cpu |
| OmniSafe | 0.5.0 |
| Safety-Gymnasium | 1.0.0 |
| Gymnasium | 0.28.1 |
| MuJoCo | 2.3.3 |
| RTAMT | 0.3.5 |

`torch.cuda.is_available()` remained false. GPU repair is not required for this
small integration gate, but it must be handled before GPU training is claimed.

This milestone establishes only that:

- the fixed temporal monitor is connected to an OmniSafe-compatible cost
  surface;
- all conditions receive the same temporal state;
- independent costs and monitor metrics survive reset, vectorization, and
  logging;
- PPO-Lagrangian can complete a minimal rollout and update.

It does not establish that the STL condition reduces violations, maintains goal
performance, outperforms native cost, or provides a formal safety guarantee.

## Next gate

Before any main training, the project must resolve open decision O6 and
predeclare:

- required violation-rate reduction;
- acceptable goal-success or return degradation;
- matched training seeds;
- evaluation episode count;
- uncertainty reporting method.

Only after those choices are recorded in `DECISIONS.md` should the three matched
training configurations and small-budget sanity runs be frozen.
