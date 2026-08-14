# Fixed-route v1 launch-readiness report

- Date: 2026-08-13
- Protocol: D43 `fixed_route_v1_quick_turn`
- Readiness: D43 package completed under the scoped D45 administrator override

## Passed

- Scenario geometry and fixed task installer validation.
- Two-reset real-environment layout/lidar/native-cost lifecycle check.
- Four ordered goals completed and cycled in one real route attempt.
- EGL render and planned/real route figures.
- Separate `0.25/0.28/K=25` executable rule supported by 30/30 recoveries.
- Online/direct-oracle/RTAMT exact agreement on all 30 calibration windows.
- Scalar and two-slot synchronous construction for task, native and C1 dense environments.
- D43 runner dry-run for all three environment IDs with rule/scenario paths,
  ten vector slots, one 10k epoch and project-owned PPOLag runtime.
- Runner phases, separate-unit task-control budget derivation, fixed-checkpoint
  stochastic/deterministic evaluator, replay command and plot/report builder.
- Fail-closed test: an attempted preflight stopped before Agent construction
  because no structured D41 pass evidence exists. No training process remained.
- Pre-launch repository regression: 108 tests passed.
- Administrator authorization was recorded in D45 without falsely marking the
  D41 CPU/RAM/discarded-epoch evidence as passed.
- Corrected equal-workload preflights selected 70k matched transitions; all
  three training cells, evaluations and figures completed within the cap.
- Final repository regression: 109 tests passed; both Conda environments passed
  `pip check`; full Python compilation and `git diff --check` passed.

## Execution outcome

The first implementation used one optimizer update in each throughput
preflight versus 40 in a reported epoch. That 150k estimate was rejected during
execution; its task-only attempt was stopped at 40k and retained. With the
preflight corrected to the same 40-update workload, task/native/STL preflights
took 66.01/65.45/65.53 seconds and selected 70k transitions per condition.

All three reported cells completed with exact cost routing, finite metrics,
hashed final checkpoints and no new kernel stop event. Aggregate accounting,
including the interrupted attempt, was 1,395.16 seconds versus the 1,800-second
cap. The 20-episode Gold results and three inspected figures are reported in
`docs/fixed_route_v1_quick_turn_report.md`.

## Residual gate

D41 remains uncleared for every scope outside this completed D43 exception.
There is still no claim that administrator CPU/RAM stability tests or the
discarded formal epoch passed. D38, Stage II-A, full 1M and confirmatory
training remain unauthorized/blocked until their respective gates are met.
