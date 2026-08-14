# Stage II v0 Offline Benchmark Implementation Report

- **Updated:** 2026-08-14
- **Authority:** D37, D38, D50 and D51
- **Status:** current 40-item revision reviewed; alias amendment and delta-review gate open

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
missing witnesses. It does not silently edit the frozen specifications. On
2026-08-14 the owner selected a prospective parameter amendment. The work
computer must change the smallest coherent portion of the parameter matrix,
regenerate all dependent artifacts and demonstrate zero missing witnesses. Any
changed record loses its previous approval and enters a delta review packet.

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
unavailable until the alias amendment and delta review both pass.

## Independent review gate

The five historical `br-v0-001` through `br-v0-005` approvals by Yuhang are
preserved. Engineer `jiahui` independently approved the other 35 current-revision
records on 2026-08-14, with all nine checklist fields true and no disagreement
notes. This approval does not transfer to content changed by the alias amendment.
The next generated packet must contain only changed records and no held-out
trace labels.

Current gates are therefore:

- D37 implementation: **pass**;
- machine foundation: **pass**;
- current-revision independent review: **pass** (40/40);
- alias-free distinguishing coverage: **closed** (`missing_witness_count=6`);
- amended-record delta review: **not yet applicable**;
- held-out Stage II-A evaluation: **prohibited until both amendment gates close**.

Train/validation-only model work remains authorized. D49 allows guarded compute
continuation after owner hardware inspection, with failure preservation, local
diagnosis and one clean retry before escalation. This compute policy is
independent of the alias/delta-review held-out gate.
