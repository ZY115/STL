# Fixed-route v1 quick-turn report

- Status: exploratory D43 diagnostic completed
- Matched transitions per condition: 70,000
- Aggregate reported training seconds: 1395.16 (23.25 minutes)
- Evaluation: one matched training seed; 20 paired stochastic episodes and one deterministic visualization episode per condition
- Hardware authority: D45 administrator risk override for D43 only; the D41 CPU/RAM stability gate was not declared passed

This bounded result is not evidence of convergence, statistical significance, method superiority or generalization. Native and C1 costs have different units. All safety comparisons below use the unchanged Gold binary evaluator, not a learner surrogate.

## Stochastic final-checkpoint summary

| Condition | Return mean | Goals/episode | Goal success | Missed/trigger | Missed / triggers | Native cost mean |
|---|---:|---:|---:|---:|---:|---:|
| Task-only | 5.781 | 2.05 | 100.0% | 0.931 | 27 / 29 | 48.900 |
| Native-safety | 7.882 | 2.70 | 100.0% | 0.675 | 27 / 40 | 38.550 |
| STL-dense-safety | 8.595 | 3.00 | 100.0% | 0.564 | 31 / 55 | 46.200 |

## Descriptive matched comparisons

- STL-dense versus task-only: missed/trigger absolute reduction `0.367`; relative reduction `39.5%`.
- Native versus task-only: missed/trigger absolute reduction `0.256`; relative reduction `27.5%`.
- All three conditions reached at least one goal in all 20 episodes; this satisfies the quick-turn visibility check but is not a powered non-inferiority test.
- Online monitor and independent oracle agreed on every evaluated episode; RTAMT completed-window maximum robustness difference was zero.

The STL-dense point estimate crosses the historical 30% reduction target, while Native does not. Because D43 has only one training seed and 20 evaluation episodes, this observation is a screening signal only and must not be promoted to a confirmatory claim.

## Frozen quick-turn pressure budgets

- Native: task-control mean `48.900` native events/episode; limit `34.230`.
- C1: task-control mean `96.717` surrogate-mass units/episode; limit `67.702`.

These limits were frozen separately at 70% of the corresponding task-only mean. Their numerical values are not directly comparable.

## Figures

- `results/fixed_route_v1/quick_turn/fixed_route_quick_turn_outcomes.png`
- `results/fixed_route_v1/quick_turn/fixed_route_quick_turn_learning_curves.png`
- `results/fixed_route_v1/quick_turn/fixed_route_quick_turn_trajectories.png`

The deterministic trajectory panels are qualitative single episodes. In that seed, all three policies triggered once and recovered within K=25; they are not the source of the stochastic safety rates above.

## Execution note

The first preflight implementation used one optimizer iteration while reported epochs used 40, which inflated its throughput estimate. The resulting 150k task-only attempt was stopped after 40k transitions and retained as a failed diagnostic attempt. The preflight was corrected to use the full 40-iteration workload; three corrected 10k preflights selected 70k matched transitions. The interrupted attempt's 232.46 seconds remain included in the 1,395.16-second aggregate cap accounting.

No D38, Stage II-A, full 1M-per-condition pilot or confirmatory run was started.
