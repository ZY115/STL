# Current Execution Directive

- **Directive ID:** `STAGE2-CONTINUOUS-2026-08-12`
- **Authority:** D37 and D38
- **Full work order:** `docs/STAGE2_CONTINUOUS_WORK_ORDER.md`
- **Status:** spatial replay and non-held-out implementation complete to the
  hardware gate; all new training paused by D41; held-out evaluation also
  requires independent human review

## Current objective

Continue from the completed negative Stage I pilot through:

```text
real spatial replay and figures
  -> O7 benchmark implementation and independent review
  -> Stage II-A offline formal-versus-direct comparison
  -> parallel Gold-STL learner-cost diagnostic
  -> fair online-interface freeze
  -> bounded Stage II-B Safe RL pilot
```

Do not repeat an experiment whose purpose is only to prove that monitor cost
can reach PPO-Lagrangian. That engineering fact is already verified.

## Immediate continuous package

The Ubuntu work computer must now:

1. replay existing checkpoints with privileged geometry used only for
   diagnostics;
2. generate paired top-down trajectories, spatial event-density and layout
   feasibility figures under `results/post_pilot_spatial_diagnosis/`;
3. write `docs/stage1_spatial_trajectory_report.md`;
4. expand the Stage II benchmark to the D37 frozen 40-specification design;
5. implement all formula-family oracles, schemas, generators and leakage tests;
6. prepare the independent-human-review packet;
7. build the separate Stage II-A environment and implement the frozen formal,
   current-observation direct and history-aware direct baselines;
8. continue train/validation-only work while review is pending;
9. after review, run the frozen held-out Stage II-A evaluation;
10. in parallel, implement the project-owned terminal-cost bootstrap repair and
    run the bounded Gold learner-cost diagnostic;
11. if both primary offline methods and one Gold learner-cost cell pass their
    gates, freeze the common online interface and run the bounded Stage II-B
    pilot.

Every parameter, split, model, gate, output and stopping rule is defined in
`docs/STAGE2_CONTINUOUS_WORK_ORDER.md`. That document is normative if this
summary omits a detail.

## Compute behavior

Training may begin only after its preceding gate passes. Verify startup through
one real update/epoch, a checkpoint, finite metrics, GPU activity and a measured
ETA. If the remaining time exceeds 20 minutes, leave the resumable job running,
record PID/command/log/ETA/resume information, and stop continuous monitoring.
Do not terminate a healthy job merely because the Codex session stops polling.

## Stop conditions

Stop and consolidate one decision request only when:

- independent human review is the only blocker to held-out evaluation;
- a paid/proprietary model would be required;
- Gold semantics or the frozen split would need to change;
- neither learner-cost candidate passes;
- repeated technical failure cannot be resolved locally.

Otherwise continue all unblocked work without returning for one-step
instructions.

## 2026-08-12 execution checkpoint

Work Package A is complete: all 15 fixed checkpoints were replayed over 100
paired seeds (1,500 episodes, 1,501,500 geometry rows), all frozen totals
matched, three spatial figures were inspected, and the fixed 60-episode real
corpus was built without releasing held-out labels.

The 40-spec D37 implementation, train/validation corpora, review packet,
three-model code, isolated environment, CUDA minimal updates, terminal-cost
bootstrap repair, C0/C1 adapters, diagnostics, exact 3×50 task-control budget
contract and resumable Gold matrix launcher are implemented. The full test
suite passes.

The remaining compute path is blocked by D41: a clean T5 retry produced a new
kernel MCE after two finite epochs, following earlier MCEs and a native-thread
segfault. There is no active training process. Do not restart Stage II-A or
Gold diagnostic training until the administrator-level hardware recovery gate
is documented as passed. Held-out evaluation independently remains blocked by
35 human reviews and the six-alias owner disposition.
