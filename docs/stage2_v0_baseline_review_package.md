# Stage II v0 Representation-Baseline Review Package

- **Prepared:** 2026-08-12
- **Status:** implementation specification prepared; final freeze requires O7 review
- **Machine-readable contract:** `configs/stage2_v0/baselines.yaml`
- **No execution performed:** no language model was called or trained

## 1. Comparison being prepared

The experiment must compare two representations while keeping the trace corpus,
public signals, causal access, data split and Gold evaluator explicit:

```text
Formal: controlled NL -> candidate STL -> verified causal monitor -> label/cost
Direct: controlled NL + causal public trajectory prefix -> learned label/cost
Truth:  independently reviewed Gold STL -> frozen oracle
```

The current-observation direct method is retained because it is closest to a
published-style language-conditioned cost baseline. It is a structural
ablation, not the sole primary opponent, because bounded recovery cannot in
general be inferred from the current distance alone.

## 2. Implementation specifications

### Formal path

- Input: one controlled-language requirement and the public typed signal
  registry.
- Output: candidate STL plus typed predicate and temporal parameters.
- Runtime: the existing verified causal monitor executes the candidate.
- Training supervision: Gold formula and grounding on the training split only.
- Classification: **adaptation**; the exact translator remains unresolved.
- Candidate choices for review: a local RESTL/ReasonSTL-style adaptation or a
  constrained structured predictor that does not require an LLM.

### Published-style direct path

- Input: the same controlled language and current public observation only.
- Output: binary temporal-cost/violation prediction.
- Training supervision: training-split Gold trace labels only.
- Classification: **idea-level adaptation pending a paper reproduction audit**.
- Role: published-style ablation; not sufficient as the only direct baseline.

### History-aware direct path

- Input: the same controlled language and the same causal public trajectory
  prefix that is available to the formal monitor.
- Output: binary temporal-cost/violation prediction; a learned active-obligation
  output may be reported for causal-history diagnostics.
- Training supervision: training-split Gold trace labels only.
- Classification: **new project adaptation** rather than a claimed strict
  reproduction.
- Candidate architectures for review: GRU or causal Transformer.

## 3. Information-access fairness table

| Item | Formal path | Current-observation direct | History-aware direct |
|---|---:|---:|---:|
| Controlled NL | yes | yes | yes |
| Public signal definition | yes | yes | yes |
| Current public observation | monitor runtime | yes | yes |
| Causal public prefix | monitor state derives from it | no | yes |
| Future trajectory | no | no | no |
| Training Gold STL | yes, translator supervision | no | no |
| Training Gold trace labels | generated after translation for diagnostics | yes | yes |
| Test Gold STL/labels | no | no | no |
| Gold monitor state as model input | no | no | no |
| Hand-coded timer as direct input | n/a | no | no |
| Final evaluator | same frozen Gold oracle | same | same |

Formula and trace supervision are inherently different resources. Fairness
therefore means transparent accounting, matched held-out cases and prohibited
test leakage—not pretending that the annotation types are identical.

## 4. Prepared evaluator

`scripts/evaluate_stage2_predictions.py` validates one method's JSONL and
reports:

- precision, recall, F1, false-negative and false-positive rates;
- exact trace-label agreement;
- matched event-time mean absolute error and unmatched-event counts;
- deadline/equality boundary and terminal-unresolved accuracy;
- paraphrase consistency when multiple language variants are supplied;
- causal-history minimal-pair accuracy when the optional learned
  active-obligation output is supplied;
- formula exact match when a formal method supplies `predicted_stl`.
- formula syntax validity plus per-field and exact typed-structure accuracy when
  a formal method supplies `predicted_structure`.

Formula exact match is only a diagnostic. Semantic or trace equivalence must be
evaluated separately; syntactically different formulas can be equivalent.

## 5. Consolidated decision request

The following choices must be made together before test-set model evaluation:

1. Approve the final O7 formula families and exact 30–50-item composition.
2. Approve semantic-pair grouping and exact paraphrase,
   parameter-composition and structure split assignments.
3. Complete independent human review of formula, grounding, comparator,
   threshold, deadline, equality and terminal semantics.
4. Select the formal translator and record pretrained resources/API access.
5. Select GRU versus causal Transformer for the primary direct baseline.
6. Audit the published direct method and decide whether the implementation can
   be called a reproduction or must remain an adaptation.
7. Freeze parameter-count allowances, training/inference compute, annotation
   counts and any API budget.
8. Freeze numerical offline admission thresholds using only corpus balance and
   annotation-quality evidence, before viewing held-out predictions.

Until these decisions are recorded, `configs/stage2_v0/baselines.yaml` is a
teacher-reviewable proposal, not a claim that the methods or gates are frozen.
