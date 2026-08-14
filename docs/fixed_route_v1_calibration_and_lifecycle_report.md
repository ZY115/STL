# Fixed-route v1 calibration and lifecycle report

- Date: 2026-08-13
- Scope: D42/D43 pre-training gates
- Result: geometry, lifecycle, rendering and deadline gates passed; GPU training remains blocked by D41

## Outcome

The real Safety-Gymnasium 1.0.0 MuJoCo environment reproduced the same start,
heading, eight hazards, vase and first goal across two reset seeds. Public lidar
distance agreed with privileged geometry, initial native cost was zero, and an
EGL frame rendered successfully. A deterministic validation controller reached
G1--G4 at samples 71, 171, 291 and 408, then cycled to G1. It is a lifecycle
instrument, not a trained policy; its minimum distance is not a safety result.

## Deadline calibration

Thirty real-dynamics approach/retreat trials (seeds 12000--12029) used the fixed
`d_warn=0.25`, `d_safe=0.28` thresholds. All 30 triggered and recovered, all in
20 steps, with no post-recovery retrigger. The declared rule
`K=max(5,ceil(1.25*linear empirical Q95))` therefore gives **K=25**. Maximum
entry depth was 0.04013; trigger inward velocity was 0.51520--0.51525.

Online monitor and independent oracle event/cost outputs agreed on all trials.
RTAMT checked all 30 completed windows; maximum robustness difference was 0.
The executable rule is `configs/fixed_route_v1/rule.yaml`; historical K=79
artifacts are unchanged.

## Reproduction

```bash
PYTHONNOUSERSITE=1 PYTHONPATH=src MUJOCO_GL=egl \
  /home/jerry/anaconda3/envs/stl-stage1/bin/python scripts/calibrate_fixed_route_deadline.py
PYTHONNOUSERSITE=1 PYTHONPATH=src MUJOCO_GL=egl \
  /home/jerry/anaconda3/envs/stl-stage1/bin/python scripts/validate_fixed_route_lifecycle.py
```

Compact evidence is under `results/fixed_route_v1/`. Raw calibration and route
CSVs remain local/ignored; calibration summary retains their hashes.

## Remaining gate

D41 is not cleared: the repository contains neither administrator CPU/RAM
stability results nor a clean discarded formal epoch. No kernel event newer
than the recorded 2026-08-12 23:15:31 MCE appeared during these short CPU
checks, but that absence is not the required stability proof. No GPU preflight
or quick-turn training was started.
