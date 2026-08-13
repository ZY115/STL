# Current Execution Directive

- **Directive ID:** `POST-PILOT-OFFLINE-BENCHMARK-2026-08-12`
- **Current work:** Gold-STL baseline diagnosis plus Stage II offline benchmark
- **Status:** non-GPU work authorized; no additional long RL run authorized
- **Long-term map:** `docs/END_TO_END_RESEARCH_PIPELINE.md`
- **Current evidence:** `docs/stage1_pilot_result_report.md`

## 1. Current research position

The project no longer asks whether an STL monitor can technically send a cost
to PPO-Lagrangian. Prior work already establishes that general route, and this
repository has independently verified the complete local implementation:

- the online monitor, direct oracle and RTAMT agree;
- raw STL events are routed to the selected learner cost;
- PPO-Lagrangian can update from a positive STL cost;
- the completed 15-run pilot produced reproducible policy-level evidence.

The pilot did not produce the expected behavioral improvement. Task-only and
Gold-STL policies missed 25.85% and 26.03% of triggered obligations,
respectively. This is a valid negative pilot, not an integration failure.

The long-term scientific question is now:

```text
Formal path: NL -> STL -> verified monitor -> cost -> Safe RL
Direct path: NL + causal trajectory history -> learned cost -> Safe RL
```

Under matched data, environment and Safe RL backends, does the explicit formal
path preserve temporal safety semantics more faithfully, expose more
diagnosable errors, and ultimately produce better policy behavior?

## 2. Why the next work is offline first

The existing Gold-STL pilot separates two facts:

1. **Evaluator validity:** the Gold-STL monitor correctly labels completed
   trajectories. This has passed.
2. **Training-signal efficacy:** the current delayed binary event cost did not
   measurably change policy behavior. This has not passed.

Starting another large run with the same settings would only repeat the same
question. Starting the language comparison immediately would also be premature,
because translation error, label error and cost-optimization failure would be
mixed together.

Therefore the work computer must now proceed through the following route. It
must complete all unblocked non-GPU items before requesting another instruction.

## 3. Step 1 - Close the current pilot as evidence

### Work

1. Preserve the frozen configs, checkpoints, evaluation files and statistical
   report without changing or relabeling them.
2. Treat the result as a diagnostic pilot, not as a final comparison and not as
   evidence that STL is generally ineffective.
3. Confirm that every claim in the status and presentation uses the distinction
   between a correct evaluator and an ineffective current training signal.

### Output

- existing reproducible Stage I result package;
- one concise statement of what passed, what failed and what remains unknown.

### Gate

This step is complete when no document describes the pilot as a test of whether
STL can be connected to PPO. It tested one specific sparse binary cost design.

## 4. Step 2 - Diagnose the Gold-STL training baseline without retraining

### Work

Use the existing task-only, native-cost and Gold-STL checkpoints and matched
evaluation seeds. Do not launch new training.

1. Replay representative successful and failed trajectories.
2. Export per-step distance, warning trigger, monitor state, remaining deadline,
   recovery event, violation event, terminal-unresolved event, reward, native
   cost and STL cost.
3. Produce trajectory plots or videos showing what the agent actually does
   before and after a warning trigger.
4. Quantify trigger count, recovery latency, deadline violations,
   terminal-unresolved cases, positive-cost frequency and the delay from trigger
   to cost.
5. Check whether policies primarily change hazard-entry frequency, recovery
   behavior after entry, or neither.
6. Add project-owned regression tests for the known runtime risks, especially
   cost-value bootstrap after a terminal-unresolved obligation, effective
   advantage scaling, rolling-window length and actual cost discount.
7. Record the effective runtime contract and diagnostic quantities needed by
   any future RL run.

### Output

- a Gold-STL trajectory diagnosis report;
- representative plots or videos linked to exact checkpoints and seeds;
- machine-readable per-step trajectory exports;
- runtime-contract and regression-test evidence;
- a short list of supported and rejected explanations for the negative pilot.

### Gate

Step 2 passes when the project can explain where and when the current cost is
generated and whether the observed failure is consistent with signal sparsity,
delay, budget mismatch or optimizer behavior. It does not need to prove that a
particular repair will work.

## 5. Step 3 - Build the Stage II offline benchmark foundation

This step may proceed in parallel with Step 2 and does not require a GPU.

### Work

1. Convert the O7 proposal into a versioned v0 benchmark contract.
2. Define the supported controlled-language fragment, grounding schema and STL
   formula families. Begin with bounded temporal requirements over public
   SafetyPointGoal1-v0 signals.
3. Create five independently reviewed end-to-end examples containing natural
   language, typed grounding, Gold STL and distinguishing traces.
4. Create synthetic boundary traces for on-time recovery, exact-deadline
   recovery, one-step-late recovery, terminal unresolved, equality boundaries,
   repeated triggers and identical current observations with different history.
5. Add real trajectories exported from task-only, native-cost and Gold-STL
   policies. Synthetic and real traces must share one schema.
6. Label every trace using the frozen Gold-STL oracle and preserve monitor,
   oracle and RTAMT agreement evidence.
7. Implement schema validation, split-leakage checks and a coverage report.

### Output

- benchmark schema and versioned metadata;
- five reviewed examples;
- synthetic trace generators and real-trajectory import path;
- Gold labels and agreement checks;
- candidate paraphrase, parameter-composition and formula-structure splits;
- coverage and data-quality report.

### Gate

Step 3 passes when another researcher can add a specification and trajectory,
validate them, reproduce their Gold labels and understand which test split they
belong to without reading the original conversation.

## 6. Step 4 - Freeze the two representation baselines

Do not train or call language models before the benchmark contract and examples
from Step 3 exist.

### Work

Define three implementations:

1. **Formal path:** controlled NL to a candidate STL formula, followed by the
   verified monitor.
2. **Published-style direct baseline:** natural language plus current public
   observation to a predicted cost or violation label.
3. **History-aware direct baseline:** natural language plus the same causal
   trajectory prefix available to the formal monitor.

For each implementation, record whether it is a strict reproduction, an
adaptation or an idea-level reimplementation. Freeze training supervision,
pretrained resources, input history, model access, compute and test-set access.
The direct baselines must not receive Gold STL or Gold monitor state.

### Output

- baseline implementation specifications;
- a fairness table showing exactly what each method receives;
- frozen offline metrics and evaluation scripts;
- one combined decision request for any unresolved model or dataset choices.

### Gate

The methods are ready only when differences in information access and
supervision are explicit. A current-observation-only direct model cannot be the
sole opponent for a history-dependent STL requirement.

## 7. Step 5 - Run the offline semantic comparison

### Work

Evaluate both routes on the same held-out language and trajectory cases.
Separate three levels of correctness:

1. formula or structured-meaning accuracy;
2. trajectory violation-label and event-time accuracy;
3. robustness to paraphrase, parameter changes, negation and temporal-scope
   minimal pairs.

Report precision, recall, false-negative rate, false-positive rate, event-time
error, boundary accuracy, minimal-pair consistency and error categories. Gold
STL remains the evaluation oracle, not a competing learned method.

### Output

- reproducible offline comparison report;
- per-example predictions and error taxonomy;
- evidence showing whether either representation has a measurable semantic
  advantage and under which requirement types.

### Gate

Proceed to online Safe RL only if both routes achieve a predeclared minimum
offline quality and the remaining errors are understood. If one route fails
offline, diagnose or revise it before spending RL compute.

## 8. Step 6 - Freeze a fair online training interface

The offline experiment compares semantic correctness. The online experiment
must not accidentally compare different cost density, scale or information.

### Work

1. Keep the frozen Gold-STL evaluator unchanged for final policy evaluation.
2. Define a common causal training-cost interface for formal and direct routes.
3. Declare cost units, timing, scale, budget, terminal treatment and history
   access for both routes.
4. Decide whether the primary control uses binary violation events or one
   semantics-preserving causal shaping rule applied consistently.
5. Use the Step 2 diagnosis to choose, but freeze the choice before observing
   new online results.
6. Define matched seeds, transition budget, evaluation episodes, task-performance
   tolerance and statistical analysis.

### Output

- frozen online comparison protocol;
- Gold evaluation protocol separated from learner cost;
- bounded sanity matrix and compute estimate;
- one explicit authorization request for GPU execution.

### Gate

No online comparison begins until a cost difference can be attributed to the
representation rather than an avoidable difference in scale, delay or access to
history.

## 9. Step 7 - Run matched online Safe RL experiments

After explicit compute authorization:

1. run a bounded routing and learning sanity for every condition;
2. inspect trajectories and cost dynamics before the main run;
3. run matched formal, direct and required control conditions from
   initialization;
4. evaluate every final policy with the same Gold-STL oracle;
5. compare temporal safety, task success, return and error propagation from
   language to labels to policy behavior.

The current 2026-08-12 pilot cannot be reused as independent confirmatory
evidence for a newly selected training interface.

## 10. Step 8 - Decide the actual research contribution

The result determines the contribution; the project must not assume that the
formal route wins.

- If the formal path is more accurate offline and safer online, report the
  conditions and mechanism of that advantage.
- If it is more accurate offline but not safer online, study the training-cost
  interface and error propagation.
- If the direct path performs better, report where explicit formalization loses
  information or creates supervision and grounding costs.
- If both are similar, the benchmark, controlled protocol and negative result
  may be the contribution.
- If neither is adequate, use the error taxonomy to motivate a hybrid or repair
  method rather than inventing one in advance.

## 11. Current stopping and compute policy

The work computer should now complete Steps 1--3 as one continuous non-GPU
package. It should prepare Step 4 and consolidate all unresolved choices into
one decision request rather than stopping after each file.

It must stop before:

- selecting final formula families or dataset splits without review;
- committing to a particular proprietary model or paid API;
- changing the Gold STL semantics;
- launching any new long RL training;
- selecting a shaping rule after observing its final evaluation performance.

The immediate deliverable is therefore not another policy checkpoint. It is a
teacher-reviewable package containing the negative-pilot interpretation,
trajectory diagnosis, benchmark contract, reviewed examples, Gold trace labels
and the exact decisions needed to begin the formal-versus-direct comparison.
