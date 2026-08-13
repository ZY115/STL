# Stage II Continuous Work Order

- **Issued:** 2026-08-12
- **Authority:** D37 and D38 in `DECISIONS.md`
- **Applies to:** the Ubuntu work computer with the existing Stage I checkpoints
- **Objective:** continue from spatial diagnosis through the Stage II offline
  comparison, Gold-STL learner-cost diagnosis, fair online-interface freeze and
  a bounded Stage II-B online pilot
- **Important:** this document authorizes a continuous work package, not a
  claim that the formal route will win

## 1. Research question and current boundary

The project compares two ways to convert a controlled natural-language temporal
safety requirement into a cost signal:

```text
Formal path: NL -> typed STL -> verified monitor -> common learner-cost adapter
Direct path: NL + causal public history -> learned temporal state/cost
Final truth: independently reviewed Gold STL -> frozen Gold evaluator
```

Stage I already established that the Gold evaluator is exact and that the
binary event cost reaches PPO-Lagrangian. Its behavioral hypothesis failed:
the sparse 79-step event cost did not improve policy behavior. Do not repeat an
experiment whose purpose is merely to prove that STL cost can enter PPO.

The next work has four linked goals:

1. reveal the actual two-dimensional Stage I behavior;
2. complete the O7 benchmark and run Stage II-A offline comparison;
3. diagnose and improve the Gold-STL learner cost without changing Gold truth;
4. freeze one fair cost interface and run a bounded Stage II-B online pilot.

## 2. Continuous-execution rule

Complete every unblocked item in this document without asking for another
instruction after each script, plot, test or short run. Stop only when:

- independent human review is required before held-out labels can be released;
- a required model cannot be obtained without a paid API or license change;
- the work would change the Gold STL semantics or the benchmark split;
- neither predeclared learner-cost candidate passes its diagnostic gate;
- a repeated technical failure remains after diagnosis and documented fixes.

When one branch is blocked, continue every other branch that does not use the
blocked held-out information.

## 3. Work Package A - Reproduce real spatial trajectories

### 3.1 Purpose

The synchronized diagnostic data contain actions and nearest-hazard distance
but not agent, hazard or goal coordinates. Re-run existing fixed checkpoints to
show what the policies actually do in the map. This is diagnostic replay only;
do not retrain or select a new checkpoint.

### 3.2 Required replay cases

Replay all three conditions (`task_only`, `native_cost`, `gold_stl_cost`) for:

1. training seed `4404`, evaluation seed `10066` - frozen Gold-worse case;
2. training seed `2202`, evaluation seed `10031` - frozen Gold-better case;
3. one median paired case selected before plotting by minimizing the absolute
   Gold-minus-task difference in missed obligations, with deterministic
   seed/evaluation tie breaking.

For aggregate spatial analysis, replay the same 100 evaluation seeds for all 15
final checkpoints. Existing checkpoint and evaluation hashes must match the
successful Stage I manifests.

### 3.3 Geometry to record

At reset and every action step, export:

```text
condition, training_seed, evaluation_seed, sample_index
agent_x, agent_y, agent_heading
goal_id, goal_x, goal_y, goal_met
hazard_0_x, hazard_0_y, ..., hazard_7_x, hazard_7_y
nearest_hazard_id, privileged_nearest_center_distance
public_lidar_distance
action_forward, action_turn
monitor_state, remaining_steps
warning_trigger, recovery, deadline_violation, terminal_unresolved
reward, native_cost, stl_cost, selected_algorithm_cost
```

Privileged geometry is for diagnosis and plotting only. It must never enter a
policy observation, language method input or learner cost.

### 3.4 Validation

- Recompute nearest center distance from `(agent_x, agent_y)` and all hazards.
- Require maximum absolute disagreement with public lidar distance `<=1e-9`.
- Reproduce all existing episode totals, monitor/oracle events and RTAMT values.
- Preserve goal resampling: split paths by `goal_id` rather than drawing one
  fixed goal for the full 1,000-step episode.

### 3.5 Figures

Create under `results/post_pilot_spatial_diagnosis/`:

1. `paired_top_down_trajectories.png`: rows are the three frozen cases; columns
   are task, native and Gold conditions.
2. `event_spatial_density.png`: occupancy, warning, recovery and violation
   densities aggregated by condition.
3. `layout_feasibility.png`: per-layout fraction of the sampled map outside the
   physical hazard radius `0.20`, warning radius `0.45` and safe radius `0.55`.
4. Optional MP4 for the median case if rendering is stable.

Each top-down panel must show:

- map boundary `[-1.5,1.5]^2`;
- hazard physical disks of radius `0.20`;
- warning circles of radius `0.45` and safe circles of radius `0.55`;
- trajectory colored by time and segmented by goal;
- start, goal, trigger, recovery, deadline-violation and terminal markers.

Track compact figures, summaries, scripts and provenance. Keep the full
1.5-million-step geometry table local/ignored, with schema, command, row count
and SHA-256 recorded. Store representative-case CSVs in Git when reasonably
sized.

### 3.6 Report and gate

Implement the replay/export entry point as
`scripts/replay_stage1_spatial_trajectories.py` and the deterministic figure
builder as `scripts/plot_stage1_spatial_diagnosis.py`. Both commands must expose
`--help`, accept explicit output roots, and refuse a checkpoint/hash mismatch.

Create `docs/stage1_spatial_trajectory_report.md`. It must answer separately:

- whether the Gold policy takes a visibly different route;
- whether it oscillates or remains inside overlapping warning/safe regions;
- whether violations cluster near goal changes or episode truncation;
- how much navigable map remains outside every `d_safe=0.55` circle;
- whether the simple environment is easy in perception but poorly aligned with
  the selected rule geometry.

Do not infer a causal explanation from one extreme trajectory. Use aggregate
maps and the median case for the main conclusion.

## 4. O7 frozen benchmark design

O7 design choices are resolved by D37. Independent human review remains an
artifact-release gate and cannot be completed by Codex on behalf of a person.

### 4.1 Environment and signals

- Environment: `SafetyPointGoal1-v0`.
- Public signal: nearest hazard-center distance reconstructed from
  `hazards_lidar`.
- Temporal unit: environment step.
- No vague language, visual perception, moving obstacles or missing numbers.
- Every sentence explicitly provides object, comparator, threshold and time.

### 4.2 Exact 40-specification composition

Create eight canonical specifications in each family:

| Prefix | Count | Family | Canonical structure |
|---|---:|---|---|
| `br-v0` | 8 | hysteretic bounded recovery | `G(e_w -> F_[0,K] p_s)` |
| `rp-v0` | 8 | recovery plus persistence | `G(e_w -> F_[0,K] G_[0,H] p_s)` |
| `ba-v0` | 8 | bounded avoidance | `G_[0,H] p_a` |
| `and-v0` | 8 | conjunction | `phi_br AND phi_ba` |
| `or-v0` | 8 | disjunction | `phi_br OR phi_ba` |

Here `e_w` is the project-defined hysteretic warning-entry event, `p_s` is a
safe-distance predicate and `p_a` is an avoidance predicate. The benchmark
record must store the complete typed AST; formula strings alone are not
sufficient.

Preserve the five existing `br-v0` records and add three. For family index
`1..8`, use the following base recovery tuples:

| Index | `d_warn` | `d_safe` | `K` | `H` for persistence |
|---:|---:|---:|---:|---:|
| 1 | 0.45 | 0.55 | 79 | 20 |
| 2 | 0.35 | 0.50 | 40 | 10 |
| 3 | 0.40 | 0.60 | 60 | 15 |
| 4 | 0.50 | 0.65 | 90 | 20 |
| 5 | 0.55 | 0.75 | 100 | 25 |
| 6 | 0.30 | 0.45 | 30 | 10 |
| 7 | 0.40 | 0.55 | 80 | 15 |
| 8 | 0.50 | 0.70 | 60 | 20 |

Bounded-avoidance durations use `H={20,30,40,50,60,80,100,120}` and distance
thresholds `{0.20,0.25,0.30,0.35,0.40,0.45,0.50,0.55}` in index order. The
conjunction and disjunction records combine the same-index recovery and
avoidance clauses. Clearly parenthesize Boolean scope.

Only `br-v0-001` is already calibrated for online use. All other records remain
`offline_only_pending_feasibility` until the spatial/controlled feasibility
gate explicitly approves them.

### 4.3 Language variants

Each canonical specification has exactly two independently written,
meaning-preserving paraphrases, producing 120 language records in total. Do not
use paraphrases that omit numbers, change comparator direction or alter scope.

### 4.4 Frozen split

All language variants and trace labels for one specification remain in the same
primary split.

| Split | Specification assignment | Count |
|---|---|---:|
| Train | indices 1-5 of `br`, `rp`, `ba`, `and` | 20 |
| Validation | indices 6-7 of `br`, `rp`, `ba`, `and` | 8 |
| Parameter test | index 8 of `br`, `rp`, `ba`, `and` | 4 |
| Structure test | all eight `or-v0` specifications | 8 |

The primary test contains 12 specifications. The structure test is a genuine
held-out Boolean composition: no `or-v0` item or generated OR formula may enter
model training or hyperparameter selection.

Report paraphrase consistency across the three wordings of each held-out
specification. A separate lexical diagnostic may train on the canonical wording
of train items and evaluate their paraphrases, but it must not be mixed with
primary held-out performance.

### 4.5 Trace corpus

For every specification family, implement direct oracle and RTAMT-compatible
evaluation and generate boundary traces covering:

- vacuous/no-trigger;
- on-time, exact-deadline and one-step-late recovery;
- terminal unresolved;
- comparator equality;
- repeated trigger while active and retrigger after recovery;
- same current distance with different causal histories;
- persistence broken at the first, middle and final required step;
- conjunction/disjunction distinguishing witnesses.

Use at least 12 deterministic boundary traces per specification. Add a fixed,
stratified real corpus of 20 episodes per Stage I condition, selected without
language-model results. Preserve full provenance and evaluate every compatible
specification against those public distance traces.

Synthetic model-training data are separate from the fixed evaluation corpus.
Generate with seed `20260812` using train structures and train parameter tuples
only:

- 10,000 controlled NL-to-structure pairs for the formal translator;
- 2,000 causal distance traces with balanced event/no-event cases for direct
  model training;
- 400 validation traces using validation tuples;
- no test tuple or OR composition in generated training data.

### 4.6 Independent review

Every one of the 40 records requires an author and a different human reviewer.
The reviewer checks object, signal, operator, Boolean scope, comparator,
threshold, deadline/duration, equality, terminal semantics and paraphrase
equivalence. Disagreements require a versioned adjudication note.

The existing `br-v0-001` through `br-v0-005` records were independently
approved by Yuhang on 2026-08-12. Preserve those review records when expanding
the dataset. Each of the 35 new records still requires its own author and
independent review; the five existing approvals do not transfer by template.

The work computer may build models on the frozen train/validation draft while
review is pending, but it must not release test Gold labels to model code or run
the held-out evaluation until every test record is approved.

## 5. O7 frozen Stage II-A methods

Create a separate `stage2-offline` environment. Do not modify the pinned Stage I
environment. Record package versions, model revisions, licenses and hashes.

### 5.1 Formal path - primary

- Model: `google-t5/t5-base` (220M), local supervised adaptation.
- Input: controlled NL plus typed public signal registry.
- Output: typed JSON/AST containing operator, predicate, comparator, thresholds
  and temporal bounds.
- Compile the validated AST deterministically to STL.
- Reject invalid schema output; do not silently repair test predictions.
- Classification: project adaptation motivated by NL2TL, not RESTL/ReasonSTL
  reproduction.
- No paid API and no proprietary model.

Add a deterministic grammar parser as a non-neural sanity baseline. It is not
the claimed formal method.

### 5.2 Published-style current-observation direct baseline

- Text encoder: `sentence-transformers/all-MiniLM-L12-v2`.
- Input: controlled NL and a text rendering of the current public distance.
- Classifier: documented cosine/MLP binary cost adaptation.
- No history, future trajectory, Gold STL or Gold monitor state.
- Classification: idea-level Lou et al. adaptation because the original
  GPT-3.5 condensation endpoint and original domain are not reproduced.
- Role: structural ablation only, not the sole direct opponent.

### 5.3 History-aware direct baseline - primary direct opponent

- Use the same MiniLM language encoder and a GRU with hidden size 128 over the
  causal public distance sequence.
- Maximum causal context: 128 steps with mask; no future samples.
- Fuse language and GRU state using a two-layer MLP.
- Output per step: violation-event probability and active-obligation
  probability. Remaining-fraction prediction is an auxiliary diagnostic.
- Train with class-weighted binary cross-entropy where weights are calculated
  from training data only.
- No handcrafted timer, Gold STL or Gold monitor state as input.
- A causal Transformer is deferred to a secondary ablation only if the GRU
  implementation passes and resources remain within the recorded cap.

Run three model seeds for each trainable Stage II-A baseline. Hyperparameters
are selected on validation only and frozen before primary test evaluation.

## 6. Stage II-A offline semantic comparison

### 6.1 Evaluation levels

1. **Structure:** schema validity, operator/comparator/parameter accuracy and
   exact typed-structure match.
2. **Trace:** precision, recall, F1, false-negative/positive rates and exact
   event timing against Gold labels.
3. **Semantic stress:** deadline/equality, terminal unresolved, history pairs,
   paraphrase consistency, parameter test and held-out OR structure test.

Formula-string exact match is diagnostic only. Typed structure and trace
equivalence are the principal formal-path measures.

### 6.2 Frozen admission gate

Report point estimates, counts and 95% Wilson/bootstrap intervals. At least 100
positive held-out events are required before applying the gate.

The formal path and history-aware direct path each must satisfy:

| Metric | Required value |
|---|---:|
| Output/schema validity | `100%` |
| Violation-event recall | `>=0.95` |
| Violation-event precision | `>=0.90` |
| F1 | `>=0.92` |
| False-negative rate | `<=0.05` |
| Event-time MAE on matched events | `<=2` steps |
| Deadline/equality boundary accuracy | `>=0.95` |
| Terminal-unresolved accuracy | `>=0.90` |
| Minimal-pair accuracy | `>=0.90` |
| Paraphrase consistency | `>=0.95` |

The current-observation direct ablation is reported even if it fails. It is not
required to pass before the two primary methods proceed.

If only one primary method passes, do not run a claimed formal-versus-direct
online comparison. Produce error analysis, repair using train/validation only,
and rerun all model seeds without changing the test set or gate.

### 6.3 Output

Create:

- fixed prediction JSONL for every model seed;
- `docs/stage2a_offline_comparison_report.md`;
- structure, trace, boundary and semantic-pair tables;
- confusion/event-time figures;
- per-example error taxonomy without exposing held-out labels to training code.

## 7. Parallel Gold-STL learner-cost diagnosis

This branch may run while Stage II-A models train. It must never change the
Gold evaluator.

### 7.1 Mandatory runtime repair before training

Implement a project-owned OmniSafe adapter that sets `last_value_c=0` when a
pending obligation has already been settled as terminal unresolved. Do not edit
Conda `site-packages`. Add executable regression tests for reward/cost bootstrap
separation, effective rolling cost, cost-advantage scale and actual discount.

Add per-epoch logs for positive-cost frequency, cost-value calibration,
reward/cost advantage standard deviation, actor reward/cost gradient norms,
lambda, actor learning rate, triggers, misses and goal events.

### 7.2 Predeclared learner-cost candidates

Keep the binary Gold event evaluator unchanged. Compare only:

1. **C0 binary event:** the existing one-cost-per-missed-obligation signal.
2. **C1 causal dense surrogate:** while an obligation is active,

```text
q_distance = clip((d_safe - d_t) / (d_safe - d_warn), 0, 1)
q_urgency  = clip(1 - remaining_steps / K, 0, 1)
c_dense    = clip(0.5*q_distance + 0.5*q_urgency, 0, 1)
```

   Emit `1` on the actual missed event. Call C1 a training surrogate, not an
   STL truth value or formal guarantee.

For each cost definition, set its diagnostic budget to 70% of the matched
task-only mean cost measured before diagnostic training. For C0 this is based
on missed events per episode, not missed/trigger percentage. Never copy a
numeric budget between C0 and C1.

Use an actor learning-rate schedule with a nonzero floor `3e-5`. Compare the
existing Lagrange initialization with one predeclared early-pressure cell
(`lambda_init=0.1`); do not search additional values after results are seen.

### 7.3 Bounded diagnostic matrix

- three new, non-pilot training seeds;
- one calibrated Gold specification: `br-v0-001`;
- `300k` transitions per cell;
- C0/C1 x existing/early-pressure optimizer cells;
- one matched task-only control;
- 50 paired evaluation episodes per seed for screening;
- unchanged Gold evaluator for all policy conclusions.

This is non-confirmatory configuration diagnosis. Select the simplest cell that
shows all of:

- exact routing and finite diagnostics;
- at least 10% relative reduction in Gold missed/trigger versus matched
  task-only screening;
- no more than 10 percentage-point goal-success loss;
- decreasing or stabilizing Gold cost with non-runaway multiplier behavior.

If no cell passes, stop before Stage II-B. Preserve the negative result and
prepare a method/optimizer decision instead of expanding the search.

## 8. Freeze the fair online cost interface

After Stage II-A and the Gold diagnostic pass, freeze one common interface:

- all cost generators consume only controlled NL, the typed public signal
  registry and the allowed causal distance history;
- all policies receive the same base observation plus the same 128-step raw
  public-distance history and mask; no policy receives Gold monitor state;
- each method produces the common fields `active_probability`,
  `violation_event_probability` and optional `remaining_fraction`;
- use the selected C0 or C1 adapter unchanged across Gold, formal and direct
  representation conditions;
- task/native controls receive the same policy observation/history;
- Gold evaluation remains the fixed binary oracle and is never replaced by a
  method's predicted cost;
- cost units, timing, budget derivation, terminal handling and normalization
  are recorded separately from task reward.

Create `docs/stage2_online_interface_protocol.md`, frozen configs, tests and a
dry-run matrix. Any deviation requires a new decision entry before online
results are viewed.

## 9. Stage II-B bounded online Safe RL pilot

### 9.1 Conditions

For the first calibrated specification `br-v0-001`, compare:

1. task only;
2. native hazard cost;
3. Gold STL using the frozen learner-cost adapter;
4. formal NL-to-STL prediction using the same adapter;
5. published-style current-observation direct prediction;
6. history-aware direct prediction.

Use the same PPO-Lagrangian backend, network, history observation, training
seeds, transition budget and Gold final evaluator. Models and translator are
fixed before RL training; do not fine-tune them on policy outcomes.

### 9.2 Execution scale

1. Run a 10k-transition one-seed routing sanity for all six conditions.
2. If every condition passes, run three matched seeds and `300k` transitions
   per condition.
3. Evaluate each final checkpoint on 100 paired seeds with the Gold oracle.
4. Report Gold violations, trigger/recovery behavior, native cost, task return,
   goal success, multiplier dynamics and prediction error under policy-induced
   distribution shift.

This bounded pilot is authorized after all prior gates pass. A five-seed,
one-million-transition confirmatory study is not automatically authorized by
this document.

## 10. Training launch and 20-minute monitoring policy

This policy applies to Stage II-A model training, Gold-cost diagnostics and the
Stage II-B pilot.

Before launch:

1. validate configs and hashes;
2. run unit tests and a dry run;
3. run the smallest real batch/rollout that exercises forward, backward,
   checkpoint and metric output;
4. use a resumable launcher with immutable attempt manifests and log paths.

After launch, monitor only until all of the following are true:

- the process remains alive;
- GPU utilization/memory is nonzero when GPU work is expected;
- at least one real optimizer update or RL epoch completes;
- loss/metrics are finite;
- one checkpoint or progress artifact is written;
- throughput gives a defensible ETA and disk estimate.

If the estimated remaining time exceeds 20 minutes, do not continuously poll or
keep the Codex session waiting. Leave the verified resumable job running and
record:

```text
PID/session identifier
command and Git commit
config and model hashes
log/run directory
completed step/epoch
throughput and ETA
GPU memory and projected disk
resume/status command
```

Stopping active monitoring does not mean terminating the job. On the next
invocation, inspect the manifest, resume failed/missing cells only, then run the
predeclared analysis automatically when the matrix completes.

## 11. Final interpretation branches

- Formal better offline and online: report where explicit structure helps.
- Formal better offline but not online: locate the learner-cost/optimization
  bottleneck rather than claiming representation superiority.
- Direct better: report the supervision, grounding and flexibility advantage.
- Similar results: treat the controlled benchmark and negative comparison as
  the result.
- Neither passes: do not hide errors with RL training; use the frozen taxonomy
  to motivate a later hybrid or repair method.

## 12. Required repository updates

After each work package, update `README.md`, `DECISIONS.md`,
`EXPERIMENT_PROGRESS_CHANGELOG.md`, `MANIFEST.md`, the relevant report and
`CHECKSUMS.sha256`. Keep confirmed evidence separate from proposals. Do not
commit bulk checkpoints or the full spatial table.
