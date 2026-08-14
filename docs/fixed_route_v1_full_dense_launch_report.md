# Fixed-route v1 full C1-dense round: launch record

## Frozen scope

- Authority: D47 owner/administrator authorization on 2026-08-13.
- Training: one new matched seed (`12647`), three conditions, 1,000,000
  transitions per condition, all trained from scratch.
- Conditions: Task-only, Native-safety and STL-dense-safety.
- Evaluation: 100 paired stochastic episodes per final checkpoint and one
  deterministic trajectory per condition.
- Scenario/rule: fixed-route v1, `d_warn=0.25`, `d_safe=0.28`, `K=25`.
- Research status: long exploratory round, not a five-seed confirmatory study.

## Cost contract

The STL training condition is bound to
`Stage2SafetyPointGoal1STLDenseCost-v0`. It selects C1 causal dense learner
cost, not the old C0 binary-only learner cost:

```text
inactive obligation: 0
active non-missed obligation:
  clip(0.5 * normalized distance deficit
     + 0.5 * normalized deadline urgency, 0, 1)
actual missed obligation: 1
```

C1 is only the learner surrogate. The unchanged Gold evaluator separately
counts binary deadline violations and terminal unresolved obligations. Final
safety comparison therefore remains missed recovery obligations divided by
triggered recovery obligations. Native and C1 limits are derived separately
from the new Task-only final checkpoint because they have different units.

## Required startup evidence

Before the 1M cells continue, three excluded 10k/40-update CUDA preflights must
show exact selected-cost routing, finite metrics, positive Native/C1 source
cost, checkpoints, and no new kernel stop event. The STL preflight additionally
must show C1 accumulated cost strictly greater than raw binary missed-event
cost. This last check would fail a violation-only `+1` routing.

The long runner is resumable at successful cell boundaries. Once startup is
confirmed, monitoring is intentionally handed back to the owner and the
healthy background process is not terminated.

## Hardware qualification boundary

D41 has not been declared passed. The owner accepts the known prior
MCE/segfault risk only for this protocol through
`configs/fixed_route_v1/d41_full_dense_admin_override.yaml`. A new MCE,
segfault, CUDA Xid, OOM or non-finite metric remains a stop condition.

## Reproduction and monitoring

```bash
cd /home/jerry/Desktop/STL
scripts/launch_fixed_route_full_dense_round.sh
```

The live process ID, launch log, run manifest, per-cell manifests and OmniSafe
`progress.csv` files are written below
`results/fixed_route_v1/full_dense_round/`. Exact observed startup values are
appended to this document after the launch gate passes.

## Observed startup evidence

Status at handoff on 2026-08-13: **startup gate passed; background training is
active; continuous agent monitoring has stopped by owner request.**

- systemd user service: `stl-fixed-route-full-dense.service`
- training PID: `432905`
- launch log:
  `results/fixed_route_v1/full_dense_round/launcher.log`
- frozen training seed: `12647`
- Task / Native / STL-dense preflight elapsed seconds:
  `66.46 / 65.46 / 65.44`
- exact selected-cost routing: passed for all three preflights
- finite metric gate: passed for all three preflights
- STL-dense preflight raw binary event cost: `1.1000000`
- STL-dense preflight C1 dense cost: `103.7207489`
- STL-dense selected algorithm cost: `103.7207489`
- STL-dense positive-cost step fraction: `0.1128000`
- therefore `selected == C1 dense` and `C1 dense > binary event`: passed
- first reported Task-only cell progress at handoff: `20,000 / 1,000,000`
  transitions, two finite rows (`Train/Epoch` 0 and 1)
- first reported-cell checkpoint: `epoch-0.pt`
- CUDA device: NVIDIA GeForce RTX 4090; driver `560.35.03`
- observed service GPU allocation: about `602 MiB`; observed utilization at
  the handoff sample: `24%`
- new kernel MCE/segfault/CUDA Xid/OOM since service start: none observed

The first `nohup` launch was reclaimed with the invoking terminal before it
entered an optimizer update. It produced no checkpoint or research data; its
empty task preflight attempt is retained as launch diagnostic evidence. The
runner was then relaunched as a user systemd transient service, creating a new
attempt under the same frozen identity. The systemd-owned process remained
active across subsequent command sessions and produced all evidence above.

At roughly the demonstrated `~180 transitions/s` full-update rate, training
alone is expected to require on the order of 4.5--5 hours for all three 1M
cells, with task-control and final evaluations adding time. This is an ETA, not
a completion promise; early KL stopping can change the realized throughput.
