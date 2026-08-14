# Stage II v0 Representation-Baseline Review Package

- **Prepared:** 2026-08-12
- **Status:** D37 implementation and CUDA preflight complete; full training paused by D41 hardware gate
- **Normative successor:** `docs/STAGE2_CONTINUOUS_WORK_ORDER.md`
- **Machine-readable contract:** `configs/stage2_v0/baselines.yaml`
- **Execution boundary:** local train/validation only; held-out Gold remains blocked

> **2026-08-14 update:** D49 authorizes guarded compute continuation. D50 closes
> the current-revision 35-record review, but D51 keeps held-out Gold closed until
> alias amendment and delta review pass. Follow `CURRENT_EXECUTION_DIRECTIVE.md`.

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
- Historical classification: **adaptation**. D37 later selected local
  `google-t5/t5-base` with typed-AST output and deterministic STL compilation.

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
- Historical candidates were GRU or causal Transformer. D37 later selected a
  GRU-128 primary model and deferred the Transformer to a resource-dependent
  ablation.

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

## 5. Historical consolidated decision request

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

D37 records the owner decisions, and `configs/stage2_v0/baselines.yaml` has
been regenerated as the machine-readable D37 contract. Independent human
review remains required before held-out evaluation.

## 6. D37 implementation update

The historical choices above have now been implemented without changing the
frozen information-access table:

- formal: pinned `google-t5/t5-base` produces typed JSON AST, followed by
  schema validation and deterministic STL compilation;
- grammar sanity: an exact registry parser accepts only the 120 frozen
  controlled wordings and refuses arbitrary text;
- current direct: pinned `all-MiniLM-L12-v2` language embedding plus current
  numeric public distance and a two-layer MLP;
- history direct: the same MiniLM encoder plus a causal GRU-128 and two-layer
  head for event, active-obligation and remaining-fraction outputs.

The separate `stl-stage2-offline` environment, exact versions, model revisions,
licenses, CUDA test and minimal updates are recorded in
`stage2a_environment_and_preflight_report.md`. Formal training attaches the
same typed public signal registry to each input. Direct training contains no
Gold formula/AST input, handcrafted timer, future sample, test tuple or OR
composition.

The deterministic grammar is explicitly an engineering ceiling/sanity check,
not the claimed learned formal result. The current-observation direct method is
reported as a structural ablation even if it fails. Selection uses validation
only; held-out prediction/evaluation scripts must not run until all required
human reviews are approved.

The first full formal cell demonstrated an otherwise executable typed-JSON
path (`compilable_rate=1.0` after epoch 0), but repeated kernel machine-check
events and one native-thread segmentation fault triggered D41. Partial
checkpoints are excluded. No further baseline or Gold-diagnostic training may
start until the host stability gate in
`stage2a_environment_and_preflight_report.md` passes.
