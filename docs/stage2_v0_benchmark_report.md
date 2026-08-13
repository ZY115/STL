# Stage II v0 Offline Benchmark Foundation Report

- **Prepared:** 2026-08-12
- **Scope:** D36 non-GPU offline foundation
- **Status:** machine-validatable draft; final O7 and human-review gates remain closed

## What was implemented

The repository now contains a versioned benchmark contract, JSON Schemas,
five controlled-language/typed-grounding/Gold-STL draft examples, synthetic
boundary-trace generation, existing-checkpoint real-trace import, three-way
Gold label verification, split-leakage validation, coverage reporting and an
offline prediction evaluator. A separate nine-field independent-review
checklist records object, signal, operator, comparator, threshold, deadline,
equality, terminal-semantics and paraphrase-equivalence review.

The executable fragment is intentionally limited to the already verified
hysteretic bounded-recovery family. This permits rigorous tool and data testing
without silently approving the broader O7 proposal. Four of the five parameter
sets are explicitly offline-only and uncalibrated for RL.

## Gold-label contract

For every generated or imported trace:

1. `BoundedRecoveryMonitor` produces causal per-sample states, events and cost;
2. the independent `evaluate_trace` enumerator recomputes events and cost;
3. RTAMT evaluates every completed inclusive recovery window;
4. generation fails on any online/oracle event or cost mismatch, or RTAMT
   robustness difference greater than `1e-9`.

Synthetic and real traces use the same `trajectory.schema.json`. Reward and
native cost are nullable for synthetic fixtures and retained for real policy
traces. The real importer accepts only the two representative cases selected
before diagnostic replay, across task-only, native-cost and Gold-STL final
checkpoints, and records checkpoint hashes and selection provenance.

## Coverage

The generator creates 11 cases for each of five draft specifications, covering
the required temporal and equality boundaries plus a same-observation,
different-history pair. Every pair among the five parameterized specifications
must also have at least one trace-level semantic witness. Six real traces are
imported from the completed Stage I replay diagnosis. The generated package
contains 55 synthetic trajectories/3,202 samples and 6 real trajectories/6,006
samples, for 61 trajectories total. All 10 specification pairs have a
distinguishing witness. Exact counts, sample
counts, case tags, pair witnesses, agreement values, review status and artifact hashes are written under
`benchmarks/stage2_v0/generated/`.

All 61 trajectories reproduce exact online/oracle event-cost agreement and an
RTAMT maximum robustness difference of `0.0`. Five same-current-distance
history pairs were checked to have different causal monitor states at their
declared anchor. Machine foundation status is `true`; final dataset status is
`false` for the review reasons below.

## What this package does not claim

- The five examples have not yet been independently reviewed by a human.
- The final 30–50 specifications and broader formula families are not frozen.
- Every record remains `draft_unassigned`; no held-out split exists yet.
- A structure split is impossible in the current single-family fragment.
- No translator or direct predictor has been selected, called or trained.
- No numerical offline-to-online admission gate has been chosen.

Consequently, the **machine-foundation gate** can pass after generation and
tests, while the **final Stage II dataset gate** must remain closed. The exact
review choices are consolidated in `docs/stage2_v0_baseline_review_package.md`.

The complete repository suite contains 68 passing tests. A second benchmark
build reproduced the same generated manifest hash
`7b6735d830d6207b95bd73ba2e4280a0cc24ad083bf762c0543d56384e49ae0c`;
all embedded artifact hashes, JSON/YAML parsing and isolated-environment
`pip check` passed.
