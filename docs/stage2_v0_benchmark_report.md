# Stage II v0 Offline Benchmark Implementation Report

- **Updated:** 2026-08-12
- **Authority:** D37 and D38
- **Status:** 40-item machine foundation complete; independent review and held-out gate open

## Implemented frozen design

The repository now implements all 40 D37 canonical specifications: eight each
of hysteretic bounded recovery (`br`), recovery plus persistence (`rp`),
bounded avoidance (`ba`), conjunction (`and`) and held-out disjunction (`or`).
Every record contains a complete typed AST, deterministic STL rendering, one
canonical controlled-language requirement, exactly two meaning-preserving
paraphrases, typed public grounding, explicit parameters and its frozen split.

The split is 20 train, eight validation, four parameter test and eight
structure-test specifications. No `or` specification or generated OR formula
enters model training or validation selection. Only `br-v0-001` is calibrated
for online use; all other records remain `offline_only_pending_feasibility`.

## Formula and trace verification

`stage2_formula.py` implements direct event evaluators for all five families.
The bounded-recovery path is additionally checked against the existing online
monitor, and every completed metric-temporal window is checked with RTAMT.
Conjunction and disjunction retain complete child states and define event time
from the child failure events; no future signal is exposed to online methods.

The full machine-review construction contains 791 deterministic synthetic
traces and six historical real traces, 797 trajectories and 63,499 samples in
total. The released model-visible package contains only train/validation
synthetic traces plus the six compatible historical train traces: 562
trajectories. Across the complete in-memory machine review:

- online/direct-oracle agreement is exact;
- maximum RTAMT robustness difference is `0.0`;
- 40 same-current-observation/different-history pairs are checked;
- deadline equality, one-step-late, terminal-unresolved, repeated trigger,
  persistence boundary and Boolean distinguishing cases are covered.

Held-out trace labels are deliberately not serialized for model code.
`gold_labels.jsonl` and `synthetic_trajectories.jsonl` contain train/validation
records only. The complete all-40 evaluation exists transiently during machine
validation, while `coverage.json` stores aggregate coverage facts without
releasing held-out labels.

## Parameter-contrast audit and frozen-design issue

Of 115 required adjacent-parameter and same-index structure contrasts, 109 have
an explicit distinguishing trace. The remaining six are not generator misses;
they are logical aliases induced by the frozen D37 parameter matrix:

- `br-v0-006/007/008` are event-equivalent to same-index `or-v0` because the
  recovery failure implies the corresponding avoidance failure;
- `ba-v0-006/007/008` are event-equivalent to same-index `and-v0` because
  satisfying avoidance precludes the warning entry needed for recovery failure.

The validator classifies these six cases and reports zero *unclassified*
missing witnesses. It does not silently edit the frozen specifications. The
final dataset gate remains closed until the owner either accepts these as
documented hard aliases or records a prospective D37 amendment with new
parameters and impact analysis.

## Train/validation corpora

The deterministic generator uses seed `20260812` and creates only frozen
train/validation content:

| Artifact | Count | Leakage guard |
|---|---:|---|
| controlled NL-to-AST training pairs | 10,000 | 20 train specs only |
| causal direct training traces | 2,000 | train families/tuples only |
| causal direct validation traces | 400 | eight validation specs only |
| formal occurrences of test/OR records | 0 | required |
| direct occurrences of test/OR records | 0 | required |

Direct traces contain 128 causal samples and event, active-obligation and
remaining-fraction targets. Formal data attach the same typed public signal
registry at runtime. Bulk training JSONL files remain local/ignored; their
schema, exact counts, seed and SHA-256 hashes are tracked in
`generated/training_data_manifest.json`.

The fixed real-policy corpus was constructed after the complete spatial
replay. Its predeclared selector chose 20 episodes per Stage I condition,
stratified by training seed and four outcome classes without using any
language-model result: 60 trajectories and 60,060 samples. All 40
specifications × 60 traces (2,400 combinations) passed internal direct/online/
RTAMT machine review with maximum difference `0.0`; only the 1,680 train/
validation label records were serialized for model code. Test labels remain
unavailable until review.

## Independent review gate

The five historical `br-v0-001` through `br-v0-005` approvals by Yuhang are
preserved. The 35 new records are machine validated but still require a named
human reviewer different from the annotation author. The generated
`independent_review_packet.md` contains all pending language, AST, STL and the
nine-field checklist; it does not claim that Codex performed human review and
does not include held-out trace labels.

Current gates are therefore:

- D37 implementation: **pass**;
- machine foundation: **pass**;
- final reviewed dataset: **closed** (35 reviews plus six-alias disposition);
- held-out Stage II-A evaluation: **prohibited until the review gate closes**.

Train/validation-only model work remains authorized by D38, but execution is
currently paused under D41 because the host produced repeated kernel MCEs. This
hardware stop is independent of the human-review/held-out gate.
