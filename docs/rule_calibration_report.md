# Stage I Rule Parameter Calibration Report

## Result

The formal Ubuntu calibration run selected:

```text
environment = SafetyPointGoal1-v0
d_warn = 0.45
d_safe = 0.55
K = 79 environment steps
```

The values satisfy the fixed domain
`0.2 < d_warn < d_safe < 3`, and the 79-step deadline is below the declared
100-step Stage I upper bound.

## Reproducibility record

- formal run date: 2026-08-05;
- final collection-script commit before data generation: `fdfdf06`;
- controlled seeds: `1000--1029`;
- random diagnostic seeds: `2000--2029`;
- command:

```bash
conda activate stl-stage1
python scripts/collect_rule_calibration.py
```

The machine-readable evidence is
`results/rule_calibration/summary.json`. It contains all 60 raw-trajectory
hashes, individual recovery times, candidate statistics, controller details,
and exact software versions. Bulk CSV files remain ignored under
`results/rule_calibration/raw/`.

The run used Python 3.8.20, NumPy 1.23.5, Safety-Gymnasium 1.0.0,
Gymnasium 0.28.1, MuJoCo 2.3.3, OmniSafe 0.5.0, RTAMT 0.3.5, and
PyTorch 2.4.1+cpu.

## Controlled trajectory protocol

For each controlled reset, the script selected the initially nearest hazard.
It used privileged positions and agent velocity only to generate a controlled
trajectory:

1. turn in place and approach the selected hazard;
2. decelerate before the warning region;
3. finish the approach at low action magnitude;
4. preserve heading and drive backward until public distance exceeds 0.9.

The monitor/calibration signal was always reconstructed from the public
observation:

```text
d_t = 3 * (1 - max(hazards_lidar))
```

All 30 controlled runs reached the approach target and later exceeded public
distance 0.9. Their approach-phase minimum public distances were
`0.247579--0.278243`; the selected-target minimum distances over the complete
runs were `0.216650--0.269798`. Controlled runs used 105--224 actions
(median 150.5).

Three runs (`1000`, `1003`, and `1014`) later passed inside native hazard
distance 0.2 while continuing toward the stricter `>0.9` stopping condition.
Those later encounters occurred after the first recovery used by the declared
calibration statistic. They are disclosed here because the controller is a
data-generation instrument, not evidence of a safe policy.

The maximum public-distance versus capped privileged-center-distance error
over all formal controlled and random samples was
`1.1102230246251565e-15`.

## Candidate results

The primary grid produced:

| `d_warn` | `d_safe` | valid recoveries | recovery Q95 | derived `K` | random trigger rate | eligible |
|---:|---:|---:|---:|---:|---:|---|
| 0.35 | 0.45 | 30/30 | 47.00 | 59 | 9/30 (30.00%) | yes |
| 0.35 | 0.55 | 30/30 | 52.55 | 66 | 9/30 (30.00%) | yes |
| 0.45 | 0.55 | 30/30 | 63.00 | 79 | 17/30 (56.67%) | yes |
| 0.45 | 0.65 | 30/30 | 91.00 | 114 | 17/30 (56.67%) | no: `K > 100` |
| 0.55 | 0.65 | 30/30 | 99.55 | 125 | 17/30 (56.67%) | no: `K > 100` |
| 0.55 | 0.75 | 30/30 | 121.55 | 152 | 17/30 (56.67%) | no: `K > 100` |

Because the primary grid contained eligible candidates, the fallback grid was
not run. For the selected pair, controlled recovery times were 42--64 steps
(median 59.5, linear empirical Q95 63.0), so the fixed selection equation gave:

```text
K = max(5, ceil(1.25 * 63.0)) = 79
```

Among eligible candidates, the selected trigger rate of 56.67% lies in the
preferred 10--80% band and is closest to 50%. This criterion takes precedence
over hysteresis margin and smaller `K`, exactly as predeclared.

## Stable fixtures

`scripts/generate_monitor_fixtures.py` produces:

- an on-time recovery fixture cropped from formal seed 1026;
- an unresolved fixture from the same real trajectory with a declared
  collector-imposed truncation;
- a deadline-violation fixture generated in the real environment with seed
  3000 by approaching and holding near a hazard through the deadline.

The fixture manifest records their hashes, sources, trigger steps, and expected
outcomes under `tests/fixtures/manifest.json`.

## Interpretation boundary

This calibration establishes feasible numerical parameters for monitor
testing. It does not demonstrate learned safety, training stability, or a
formal safety guarantee. No RL training was performed.
