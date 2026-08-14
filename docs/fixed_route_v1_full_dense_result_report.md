# Fixed-route v1 full C1-dense round result

## Scope and validity

This report analyzes one matched training seed (`12647`), three fixed final 1M-transition checkpoints and 100 paired stochastic evaluation episodes per condition. It is exploratory: it is not the frozen five-seed confirmatory study and does not establish a formal safety guarantee.

The original runner stopped after training because one of 100 STL CSV rows differed between selected and dense logger aggregates by `3.8147e-6` at scale `42.2763` (about `9.0e-8` relative). All three checkpoints were complete and finite. A scale-aware validation accepted the existing checkpoint; the original failed manifest remains unchanged.

## Fixed-checkpoint result

| Condition | Return mean | Goals/episode | Goal success | Gold missed / trigger | Native cost mean | Mean minimum distance |
|---|---:|---:|---:|---:|---:|---:|
| Task-only | 35.674 | 12.97 | 100.0% | 0/268 = 0.000 | 2.420 | 0.200 |
| Native-safety | 31.694 | 10.98 | 100.0% | 0/345 = 0.000 | 0.020 | 0.216 |
| STL-dense-safety | 17.477 | 6.27 | 100.0% | 31/139 = 0.223 | 8.730 | 0.190 |

Task-only and Native-safety had zero missed recovery obligations, whereas STL-dense had `31/139 = 0.223`. Because the Task-only baseline rate is zero, the frozen protocol uses absolute difference: the Task-minus-STL reduction is `-0.223` (95% paired episode-bootstrap interval `-0.313` to `-0.139`), and Task-minus-Native is `0.000`. Relative reduction is undefined. STL-dense therefore does not meet the intended safety direction in this run.

STL-dense retained 100% goal success but its mean return was `17.477` versus Task-only `35.674`. Its physical native cost mean was `8.730` versus `2.420`.
Native-safety reduced physical native cost from `2.420` to `0.020`, while mean return changed from `35.674` to `31.694`.

Paired episode-bootstrap intervals are descriptive only because policies come from one training seed:

- STL minus Task return difference 95% interval: `-18.943` to `-17.501`.
- Native minus Task return difference 95% interval: `-4.082` to `-3.885`.
- STL minus Task native-cost difference 95% interval: `1.830` to `12.700`.
- Native minus Task native-cost difference 95% interval: `-3.120` to `-1.770`.

Online monitor and independent oracle agreed in every evaluated episode for all three conditions; RTAMT completed-window maximum robustness difference was zero.

## Interpretation

The dense interface definitely supplied non-sparse training feedback, but it did not produce a safer final policy. Over the last 20 training epochs, STL selected cost averaged `16.535`, above its frozen `10.995` limit, while its Lagrange multiplier averaged `1.444` and ended at `1.490`. The STL return was still improving but remained far below Task-only. These traces do not support a convergence claim.

The outcome pattern is mechanistically important: STL-dense reduced the number of warning triggers (`139` versus Task-only `268`) but missed `31` of the obligations it did trigger, reduced goal throughput, and increased physical contact. A plausible interpretation is that the accumulated pending-obligation surrogate and tight episode-level budget encouraged avoiding triggers without learning reliable recovery after entry; this is an inference, not yet a causal conclusion. Native cost, by contrast, nearly eliminated physical hazard contact (`0.020` versus `2.420`) while preserving zero Gold misses, though at a smaller task-return penalty.

The next step should be mechanism diagnosis before another long run: inspect C1 cost/value/advantage scale around trigger and recovery windows, test whether accumulated surrogate mass overwhelms the event objective, and evaluate these fixed checkpoints on prospectively defined held-out routes/layouts. Any cost normalization or scenario/rule change must be frozen before seeing new training outcomes.

Learning-curve tail values remain in `analysis_summary.json`; visual inspection is still required before calling any condition converged.

## Figures

- `results/fixed_route_v1/full_dense_round/full_dense_learning_curves.png`
- `results/fixed_route_v1/full_dense_round/full_dense_constraint_diagnostics.png`
- `results/fixed_route_v1/full_dense_round/full_dense_final_outcomes.png`
- `results/fixed_route_v1/full_dense_round/full_dense_deterministic_trajectories.png`
