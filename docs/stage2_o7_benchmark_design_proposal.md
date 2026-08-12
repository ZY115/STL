# O7 Proposal: Stage II Controlled-Language Benchmark

- **Prepared:** 2026-08-12
- **Status:** non-compute design proposal; not yet frozen
- **Scope:** WP2 controlled NL/gold-STL and trajectory benchmark
- **Excluded:** model training, free-form language, online Stage II RL

## 1. Purpose

The Stage I pilot established a verified gold label path but did not show a
policy-level safety gain under the frozen sparse-cost PPOLag configuration.
WP2 can nevertheless proceed because its first objective is offline semantic
comparison:

```text
controlled NL -> predicted STL -> verified monitor labels
controlled NL + causal history -> direct predicted labels
                         versus
human-verified gold STL -> gold labels
```

O7 must freeze the supported language, formula fragment, data split and human
confirmation procedure before data generation or baseline training.

## 2. Candidate v0 scope

Build a 30–50-specification pilot. A concrete candidate is 40 canonical gold
specifications with two meaning-preserving paraphrases each. This is a proposal,
not a final dataset-size commitment.

The first version should use only signals already defined and mechanically
checkable in `SafetyPointGoal1-v0`, beginning with the public nearest-hazard
distance. New signals may be added only after their public observation mapping,
units and validation are documented.

Candidate formula families are:

1. bounded recovery from a hysteretic warning event;
2. recovery followed by sustained safety for a bounded interval;
3. bounded avoidance/always constraints over declared intervals;
4. conjunction and disjunction of supported bounded clauses;
5. polarity and temporal-scope contrasts used primarily for offline semantic
   testing.

Dangerous or task-incompatible polarity cases remain offline test items and do
not automatically become RL training requirements.

## 3. Controlled-language and grounding contract

Every sentence must explicitly state:

- the relevant object (`nearest hazard` in the first slice);
- comparison direction (`closer than`, `at least`);
- numerical threshold and simulator-distance unit;
- deadline or duration in environment steps;
- temporal relation (`within`, `after`, `for`, `always`);
- conjunction/disjunction scope where present.

No open-world inference of phrases such as “reasonably far” is allowed in v0.
Each record must contain a typed grounding schema rather than only a formula
string.

## 4. Required specification schema

```text
spec_id
canonical_natural_language
paraphrases
gold_stl
formula_family
grounding_schema
parameter_values
semantic_pair_id
semantic_contrast_type
allowed_online_use
split
annotation_author
independent_reviewer
review_status
source_or_generation_record
```

The schema and a small hand-checked example set belong in Git. Bulk generated
trajectories may remain external/ignored, but their generator command, hashes,
schema and aggregate coverage must be tracked.

## 5. Semantic minimal-pair taxonomy

The candidate taxonomy must include trajectories that distinguish each pair:

- threshold increase/decrease;
- deadline increase/decrease;
- `within K` versus `after K`;
- eventual recovery versus recovery-and-persistence;
- conjunction versus disjunction;
- positive versus negated predicate;
- meaning-preserving paraphrase;
- same current observation with different causal histories.

A text-only pair is insufficient. Every contrast requires at least one gold
trajectory or synthetic trace on which the two meanings produce different
labels or event times.

## 6. Trajectory corpus

Each supported family must cover:

- no trigger/vacuous case;
- on-time recovery;
- exact inclusive deadline recovery;
- first recovery one step late;
- terminal unresolved;
- predicate equality boundaries;
- repeated entry while one obligation is active;
- matched current observation with different monitor history;
- trajectories from scripted fixtures and from task/native/gold policies.

Each trajectory record must include signals, gold event steps, binary costs,
completed-window robustness where defined, termination metadata, source policy,
environment seed and generator hash.

## 7. Candidate split policy

Use three disjoint axes rather than a random sentence split:

1. **Paraphrase split:** unseen wording for seen semantics;
2. **Parameter-composition split:** unseen threshold/deadline combinations;
3. **Structure split:** at least one formula composition held out from training.

All paraphrases and parameter variants belonging to one semantic pair must be
grouped to prevent leakage. Exact split proportions remain an O7 decision after
the 40-item composition is enumerated.

## 8. Human confirmation

Every gold item requires:

1. one author to write the sentence, grounding and STL;
2. one independent reviewer to check operator, predicate, threshold, deadline,
   equality and terminal semantics;
3. RTAMT/direct-oracle agreement on all distinguishing traces;
4. resolution notes for every disagreement;
5. a frozen review status before test labels are released.

Translator or direct-cost developers must not edit test gold labels after
seeing model outputs without creating a versioned adjudication record.

## 9. Baseline fairness requirements

- Formal and direct paths receive the same controlled-language split and public
  environment signals.
- The direct main baseline receives a causal history or recurrent state; a
  current-observation-only method is a published-style ablation, not the sole
  opponent.
- The direct baseline never receives gold STL or gold monitor state.
- The formal path never receives held-out gold formulas.
- Formula supervision, trace labels, pretrained resources, parameter count,
  annotation count, API use and compute are reported separately.
- Final trace and policy truth is always the human-verified gold oracle.

Candidate method families remain RESTL/ReasonSTL-style explicit translation,
Lou et al.-style direct cost, and a history-aware GRU/Transformer direct
baseline. O7 must later label each implementation as strict reproduction,
adaptation or idea-level reimplementation.

## 10. Candidate offline gate

Before any Stage II online RL comparison, prospectively freeze thresholds for:

- formula syntax and operator/predicate/parameter accuracy;
- semantic equivalence or trace equivalence;
- violation precision, recall, F1, false-negative and false-positive rates;
- event-time error and deadline-boundary accuracy;
- terminal-unresolved accuracy;
- minimal-pair flip and paraphrase consistency.

No numerical gate is confirmed in this proposal. Selecting thresholds requires
class-balance and annotation-quality evidence from the first hand-checked
corpus; it must occur before baseline test-set evaluation.

## 11. Immediate non-compute implementation after approval

1. freeze the formula families and exact 40-item composition;
2. add JSON Schema/YAML schema files and five manually reviewed examples;
3. implement validators for IDs, grouping, units and split leakage;
4. implement synthetic distinguishing-trace generators per family;
5. extend gold oracle/RTAMT agreement tests only for the approved fragment;
6. generate a coverage report before selecting model baselines.

This proposal does not authorize an LLM, baseline training or an online RL run.
