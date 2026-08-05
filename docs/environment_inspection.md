# SafetyPointGoal1-v0 Environment Inspection

## Status

The environment-only inspection milestone was completed on 2026-07-29. This
report contains no STL monitor integration and no RL training.

## Public API

`SafetyPointGoal1-v0` resets with:

```text
observation, info
```

and each step returns:

```text
observation, reward, native_cost, terminated, truncated, info
```

The tested default spaces are:

- flattened observation: shape `(60,)`, dtype `float64`;
- action: `Box(-1, 1, (2,), float64)`;
- maximum episode length: 1000 environment steps.
- reset info keys in the tested default configuration: none;
- terminal step info keys in the random smoke test: `cost_hazards` and
  `cost_sum`.

The unflattened observation schema contains:

| Signal | Shape |
|---|---:|
| accelerometer | `(3,)` |
| velocimeter | `(3,)` |
| gyro | `(3,)` |
| magnetometer | `(3,)` |
| goal lidar | `(16,)` |
| hazard lidar | `(16,)` |
| vase lidar | `(16,)` |

At a native hazard-cost step, the scalar native cost and
`info["cost_hazards"]` agreed exactly in the collected sample.

## Distance signal

Stage I defines \(d_t\) as the nearest agent-origin-to-hazard-center distance,
capped at the public hazard pseudo-lidar range of 3 simulator length units.

The default hazard pseudo-lidar has 16 bins and encodes center distance as
closeness. Therefore:

```text
d_t = 3 * (1 - max(hazards_lidar))
```

This signal is:

- available from the policy's public observation;
- deterministic for the current pseudo-lidar configuration;
- independent of privileged simulator state;
- exactly aligned with the center-distance quantity used to determine hazard
  proximity in the benchmark.

It is not physical boundary-to-boundary clearance. The hazard radius is `0.2`,
the Point XML contains a rendered sphere of radius `0.1`, and placement
`keepout` values are not physical radii. A boundary-clearance interpretation
would therefore require an additional convention and would not match the
benchmark's native center-distance rule as directly.

Because the public signal is capped at 3, the later choices of
\(d_{\mathrm{warn}}\) and \(d_{\mathrm{safe}}\) must both be below 3. The cap
then has no effect on warning or recovery judgments.

## Simulator-state cross-check

For validation only, the unwrapped task exposes:

```text
task.agent.pos
task.hazards.pos
task.hazards.size
```

The simulator cross-check was:

```text
min_i ||agent_xy - hazard_i_xy||_2
```

Across 3500 collected steps, public-lidar reconstruction agreed with the
simulator center distance capped at 3. The maximum absolute error was
approximately `7.8e-16`.

Simulator positions should remain a validation diagnostic, not the primary
Stage I monitor input.

## Saved sample trajectories

Generated outputs are stored locally under:

```text
results/environment_inspection/
```

The directory contains:

- three 1000-step seeded random-policy CSV trajectories;
- one 500-step scripted hazard-approach CSV trajectory;
- two short MP4 renderings;
- a JSON summary.

Each CSV records actions, native reward, native cost, termination status,
agent position, public distance, privileged validation distance, and their
reconstruction error. The scripted trajectory contains six positive native-cost
steps, confirming that reward and native cost can be recorded separately.

The collected trajectory statistics are:

| Policy and seed | Steps | Return | Native cost | Positive-cost steps | Minimum public distance |
|---|---:|---:|---:|---:|---:|
| Random, 11 | 1000 | -0.420867 | 0 | 0 | 0.648511 |
| Random, 22 | 1000 | 1.339734 | 0 | 0 | 0.436761 |
| Random, 33 | 1000 | -0.906095 | 0 | 0 | 0.388368 |
| Scripted hazard approach, 44 | 500 | -0.203226 | 6 | 6 | 0.195073 |

The random episodes reached the 1000-step time limit and returned
`truncated=True`. The scripted rollout was intentionally stopped after 500
steps, so it was neither terminated nor truncated.

Raw CSV outputs are excluded from Git by `results/.gitignore`. Git tracks the two
compact MP4 renderings, `results/environment_inspection/summary.json`, and
`results/environment_inspection/README.md`. The summary preserves statistics,
video metadata, and SHA-256 hashes for both tracked videos and ignored CSV
artifacts.

## Verification scope

The completed checks establish only that:

- the selected software stack installs and imports;
- the benchmark and its public API execute;
- reward and native cost can be logged separately;
- the public distance reconstruction agrees with simulator state;
- OmniSafe can construct PPO-Lagrangian for the benchmark;
- RTAMT can evaluate a bounded-future test specification;
- off-screen rendering and trajectory storage work.

They do not establish monitor correctness for the Stage I rule, STL-cost
correctness, training stability, safety improvement, or formal safety.

## Remaining questions

Environment inspection by itself did not choose:

- \(d_{\mathrm{warn}}\);
- \(d_{\mathrm{safe}}\);
- \(K\);

Those numerical parameters were subsequently selected as 0.45, 0.55, and 79
steps. Equality, floating-point, truncation, repeated-trigger, and cost semantics
were fixed in `docs/stage1_rule_monitor_spec.md`; the corresponding monitor and
agreement tests passed on 2026-08-05. The OmniSafe wrapper and RL training were
not part of environment inspection.
