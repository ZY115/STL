# Current Execution Directive

- **Directive ID:** `STAGE2-CONTINUOUS-2026-08-14`
- **Authority:** D37--D53
- **Full work order:** `docs/STAGE2_CONTINUOUS_WORK_ORDER.md`
- **Machine-readable owner decisions:**
  `configs/stage2_v0/owner_decisions_2026-08-14.yaml`
- **Status:** D42--D48 fixed-route diagnostics are complete; D49 authorizes
  guarded Stage II compute continuation. Current prerequisites are the D51 alias
  amendment, delta review of changed records and D48 mechanism report.

## Owner decisions effective 2026-08-14

The owner reports that hardware inspection found no actionable repair and
authorizes guarded continuation under D49. A recurring system or training
failure must be preserved and diagnosed locally first; one controlled clean
retry is allowed after a reproducible fix. Escalate only if administrator or
hardware action is required, a frozen research contract must change, or the
controlled retry remains unsuccessful.

All 35 previously pending current-revision specifications are independently
approved by `jiahui`; the five historical Yuhang approvals remain unchanged.
The owner selected parameter amendment rather than accepting the six logical
aliases. Changed records must return to pending review, and held-out labels
remain closed until the amended benchmark has zero missing witnesses and the
delta review is complete.

D48 is followed by mechanism analysis and then the unchanged registered C0/C1
matrix. No additional cost candidate or free hyperparameter search is allowed.
If no Gold learner-cost cell passes, the online branch ends.

Online work is split into B1 (`br-v0-001`) and conditional B2
(`rp-v0-001` plus non-alias `or-v0-001`). A workload-matched estimate above 20
aggregate hours blocks automatic launch unless the strict D53 upstream-perfect
exception passes; otherwise it requires an owner decision package.

## Current objective

```text
reviewed O7 benchmark
  -> alias-free parameter amendment and delta review
  -> Stage II-A offline formal-versus-direct comparison
  -> D48 mechanism analysis and bounded Gold C0/C1 diagnostic
  -> fair online-interface freeze
  -> bounded Stage II-B1 propagation pilot
  -> conditional Stage II-B2 complex-specification pilot
```

Do not repeat an experiment whose purpose is only to prove that monitor cost can
reach PPO-Lagrangian. Do not tune a learner cost until STL wins. A correctly
executed negative or offline-only branch is a completed Stage II outcome.

## Immediate continuous package

The Ubuntu work computer must now:

1. produce the smallest coherent D51 parameter amendment and distinguishing
   traces without exposing model predictions or held-out labels, then write
   `docs/stage2_v0_alias_amendment_report.md`;
2. regenerate affected language/AST/STL/trace artifacts, hashes and the delta
   review packet; changed records become pending automatically;
3. run all train/validation-only Stage II-A cells under D49 guarded compute while
   the delta review is pending;
4. complete `docs/d48_c1_mechanism_analysis_report.md` from existing artifacts
   before new Gold learner-cost training;
5. after that report, run the unchanged D38/D40 C0/C1 diagnostic matrix;
6. after the delta review closes, run the frozen held-out Stage II-A evaluation;
7. stop the online branch if either primary offline admission or every Gold
   learner-cost cell fails;
8. otherwise freeze the common online interface and run the B1 routing sanity;
9. use workload-matched preflight timing to enforce the 20-hour automatic-launch
   limit before B1 reported training;
10. run B1 only when all gates and compute policy pass;
11. calibrate `rp-v0-001` and `or-v0-001`, then apply the same gate and time
    policy to conditional B2;
12. finish with the predeclared interpretation branch and repository updates,
    even when the result is negative.

Every parameter, split, model, metric and stopping rule not amended by D49--D53
remains normative in `docs/STAGE2_CONTINUOUS_WORK_ORDER.md`.

## Compute behavior

Before every training package, validate configs and hashes, run the smallest
workload-matched real update or epoch, confirm finite metrics and checkpoint
output, compare kernel/system events and record a measured ETA.

If an already authorized job has more than 20 minutes remaining, leave the
resumable job running, record PID/command/log/ETA/resume information and stop
continuous monitoring. Do not terminate a healthy job merely because the Codex
session stops polling.

Separately, do not automatically launch any B1 or B2 package whose aggregate
workload-matched estimate exceeds 20 hours unless every D53 upstream-perfect
criterion passes. Otherwise create the decision package at
`docs/stage2_online_compute_decision_package.md`.

## Failure handling

On a new MCE, native crash, CUDA Xid, OOM or non-finite result:

1. preserve the failed attempt and all logs;
2. collect host, kernel, CUDA, process and training evidence;
3. distinguish repository/environment failure from host hardware failure;
4. apply only reproducible local fixes that do not change the frozen research
   contract;
5. run one clean from-scratch validation retry;
6. request human help only if administrator/hardware action is required, a
   contract change is necessary, or the controlled retry still fails.

## Stop conditions

Stop and consolidate one decision request only when:

- delta human review is the only blocker to held-out evaluation;
- a paid/proprietary model would be required;
- Gold semantics or the frozen split would need to change;
- neither learner-cost candidate passes;
- repeated technical failure remains unresolved after local diagnosis and one
  controlled retry;
- a B1/B2 package exceeds the 20-hour automatic-launch limit.

Otherwise continue all unblocked work without returning for one-step
instructions.

## Current checkpoint

Spatial replay, the 40-spec benchmark foundation, train/validation corpora,
three Stage II-A model implementations, isolated environment, CUDA minimal
updates, terminal-cost repair, C0/C1 adapters, diagnostics, task-control budget
contract and resumable launchers are implemented.

D43 and D47/D48 fixed-route runs are complete. The long C1 result is negative
and does not justify additional cost search. D49 permits guarded Stage II
training after owner hardware inspection. D50 records `jiahui` approval of the
35 previously pending current-revision records. Held-out evaluation remains
closed because D51 requires an alias-free amendment and fresh review of every
changed record.
