# Stage I Rule Calibration Artifacts

This directory records the formal parameter-calibration run for the Stage I
bounded-recovery rule.

- `summary.json` is tracked and contains software versions, controller details,
  per-run hashes, all candidate statistics, and the selected parameters.
- `raw/` contains 30 controlled and 30 random-policy CSV trajectories. These
  bulk outputs remain ignored by Git; their hashes are retained in the summary.
- Stable, minimal monitor fixtures derived from the controlled trajectories are
  tracked under `tests/fixtures/`.

The final collection script was committed as `fdfdf06` before the formal run. The
scripted controller uses privileged geometry only to generate controlled
approach-and-escape evidence. Public `hazards_lidar` remains the monitor input.
