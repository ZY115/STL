# Project Context and Research Evolution

## 1. Why this document exists

This document reconstructs the reasoning developed across the full project conversation. It is not a verbatim chat transcript. It records the research conclusions, changes of scope, rejected assumptions, and reasons behind the current Stage I plan.

The central purpose is continuity: a new researcher or a new Codex session should understand not only the current experiment, but how and why the project arrived at it.

## 2. Original research idea

The original idea was:

> A user describes a task and its safety requirements in natural language. The system translates the description into STL and uses the STL specification during RL training.

An example is:

> Reach the goal. If you get too close to an obstacle, return to a safe distance within 10 steps.

This command contains two components:

- task objective: reach the goal;
- temporal safety requirement: after unsafe proximity, recover before a deadline.

The initial intuition was broadly correct, but two technical corrections were necessary.

### Correction 1: not every part of the task must become STL

For the first Safe RL formulation, the task objective can remain the benchmark's native reward. STL is used to represent the safety requirement.

This separation avoids replacing a stable task definition with a more complicated temporal objective before the safety mechanism is understood.

### Correction 2: an STL string is not directly consumed by RL

The actual chain is:

```text
STL formula
    ->
trajectory monitor
    ->
satisfaction, violation, or robustness
    ->
safety cost
    ->
Safe RL optimizer
```

The monitor is therefore a necessary interface between formal logic and learning.

## 3. Technical foundations established from the literature

### 3.1 Temporal Logic, LTL, and STL

Temporal Logic is the broad family.

Linear Temporal Logic describes properties over ordered sequences of states using propositions and temporal operators such as always, eventually, next, and until.

Signal Temporal Logic extends temporal reasoning to real-valued signals and explicit time intervals. This makes it suitable for statements such as:

> Whenever distance becomes smaller than a warning threshold, distance must become larger than a safe threshold within five seconds.

STL is therefore more directly aligned with continuous control and quantitative robot signals than propositional LTL.

### 3.2 The NL2TL paper

The EMNLP 2023 NL2TL paper studies translation from natural language to temporal logic.

The key idea is to separate:

- logical structure;
- domain-specific atomic propositions.

The paper trains T5 on lifted examples, where specific entities and propositions are replaced with placeholders. This allows the model to learn recurring logical structures rather than memorizing one application domain.

GPT-3 is used in the broader data-generation and proposition-recognition pipeline, while T5 is the specialized sequence-to-sequence model trained for repeatable NL-to-TL translation.

The project-level lesson was:

> Complex unseen instructions may be translated by composing learned logical patterns, provided that the atomic propositions and their grounding are available.

However, translation accuracy is not sufficient for Safe RL. A syntactically valid formula may still use the wrong signal, threshold, object, or time unit.

### 3.3 DeepLTL

DeepLTL studies how an RL agent can efficiently satisfy complex LTL specifications, including formulas not observed during training.

Its main problem differs from NL2TL:

- NL2TL asks how to produce a formal formula from language;
- DeepLTL assumes a formal LTL specification is already provided and asks how an agent can execute it.

DeepLTL uses automata structure and formula-conditioned policies. It is evidence that temporal specifications can support compositional and zero-shot task execution.

It does not solve the language-grounding problem and is not directly a solution to the current STL-cost Safe RL experiment.

### 3.4 Safe RL via shielding

Safe RL via Shielding represents an alternative enforcement philosophy.

A shield checks or modifies actions so that unsafe actions are blocked during execution. This can provide stronger runtime intervention than a learned cost.

Our current Stage I plan is closer to traditional constrained Safe RL:

- a safety signal becomes a cost;
- PPO-Lagrangian trades task reward against a cost constraint;
- violations may still occur.

A shield may be compared later, but adding it now would change the research question from learning with a temporal cost to runtime action intervention.

## 4. The initially proposed complete system

The broad system discussed earlier contained four major parts:

1. natural-language specification generation;
2. formal safety checking;
3. Safe RL execution;
4. counterexample feedback and specification repair.

The intended loop was:

```text
Natural-language task
    ->
candidate STL
    ->
syntax and feasibility checking
    ->
STL-guided Safe RL
    ->
unsafe or unsuccessful trajectory
    ->
counterexample explanation
    ->
revised grounding or specification
```

This is a meaningful long-term architecture, but it combines multiple research problems:

- language translation;
- numerical grounding;
- formal verification;
- control feasibility;
- monitor implementation;
- cost shaping;
- constrained RL;
- diagnosis and repair.

The workload and attribution problem would be too large for a first experiment.

## 5. The role of grounding

Grounding means connecting linguistic concepts to the concrete variables, objects, thresholds, and units of an environment.

For example:

```text
"too close"
    ->
distance to the nearest hazard
    ->
d_t < d_warn
```

Grounding must determine:

- which object is relevant;
- which simulator or sensor signal represents the concept;
- the comparison direction;
- the numerical threshold;
- the unit of time;
- the coordinate or reference frame.

The project therefore cannot assume that natural language automatically supplies a complete and correct executable safety condition.

Stage II will initially avoid this open-ended problem by using controlled language with explicit objects, distances, and deadlines.

## 6. Why a numerical STL condition does not guarantee RL safety

Even if the safety condition contains exact numbers, several difficulties remain.

### 6.1 The signal may be defined incorrectly

Distance may mean center distance, boundary clearance, lidar estimate, or privileged simulator state.

### 6.2 The formula may be correct while the monitor is wrong

Temporal boundaries, repeated triggers, truncation, equality, and floating-point tolerance can change judgments.

### 6.3 The cost may be delayed or sparse

A bounded-future formula may only be known to have failed after its deadline expires. A late cost may be difficult for RL credit assignment.

### 6.4 Safe RL optimizes expected behavior

PPO-Lagrangian does not prove that every trajectory satisfies the formula. Constraint budgets, optimization error, exploration, function approximation, and stochasticity can all produce violations.

### 6.5 Safety and task performance may conflict

An agent could reduce violations by refusing to approach the goal or by stopping. Safety improvement must therefore be interpreted together with goal success and return.

## 7. Comparison with the 2026 UAV NL-to-STL and MILP repair paper

The UAV paper demonstrates a more complete application pipeline:

- natural-language navigation instructions;
- translation into STL;
- numerical or structural repair;
- trajectory generation for a low-altitude UAV setting.

This work is close to our long-term language-to-formal-specification direction.

The current project differs in its central downstream question:

- the UAV work focuses on specification translation, repair, and trajectory planning/control;
- our Stage I focuses on using a temporal STL safety requirement as a cost inside Safe RL training.

MILP repair can correct certain infeasible or inconsistent numerical specifications, but it does not establish that an STL-derived cost is correctly integrated into a model-free Safe RL learner.

The UAV paper therefore motivates later stages rather than eliminating the need for the current Stage I control experiment.

## 8. Why the problem was narrowed

The original end-to-end chain has at least four independent uncertainty groups.

### 8.1 Language interpretation

Did the system identify the correct task objective and safety requirement?

### 8.2 Grounding

Were phrases mapped to the correct objects, signals, thresholds, and time units?

### 8.3 Monitoring and cost design

Did the monitor evaluate the formula correctly, and did its output produce a useful cost?

### 8.4 Safe RL learning

Could the agent reduce temporal failures while preserving task completion?

Each component can fail even if the others are correct. An end-to-end failure would not reveal the cause.

This motivated the staged decomposition.

## 9. Three-stage research plan

### Stage I: Gold-STL experiment

Manually write one correct STL rule.

Test:

- environment signal extraction;
- trajectory monitoring;
- STL-to-cost conversion;
- Safe RL integration;
- behavioral effect.

No language model is used.

### Stage II: Controlled language

Add commands whose objects, distances, and deadlines are explicit.

Evaluate separately:

- translation correctness;
- formula equivalence;
- downstream behavior.

The Stage I monitor, wrapper, and benchmark remain fixed so that new errors can be attributed to the language layer.

### Stage III: Broader language and environments

Expand to:

- vague or missing parameters;
- more STL structures;
- uncertain sensing;
- dynamic hazards;
- additional applications;
- repair and counterexample feedback.

## 10. Teacher feedback and experimental grounding

The project was asked to:

- identify a concrete application and benchmark;
- make the problem definition grounded;
- examine limitations;
- compare alternative methods;
- clarify scenarios the approach can address;
- specify a clear next step.

This feedback shifted the project from a broad architecture discussion to one minimal experiment.

## 11. Application and benchmark selection

### Selected application

Simulated mobile robot navigation around static hazards.

### Selected benchmark

`SafetyPointGoal1-v0` from Safety-Gymnasium.

### Reasons for selection

- it is a recognized Safe RL benchmark;
- it already provides a goal-reaching task;
- it includes hazards and a native instantaneous hazard cost;
- it is supported by OmniSafe;
- it avoids building a simulator;
- it avoids perception uncertainty in the first test;
- its native cost creates a useful baseline.

### Deliberate limitation

This benchmark is much simpler than UAV, autonomous driving, multi-agent navigation, or a real robot.

That simplicity is useful for attribution in Stage I but limits external validity.

## 12. Current Stage I specification

### Plain-language rule

> If the agent enters a warning zone, it must return to a safe distance within `K` environment steps.

### STL form

```text
G(e_t -> F_[0,K](d_t >= d_safe))
```

### Intended meaning

- `e_t`: start of a new hysteretic warning episode;
- `d_t`: nearest agent-origin-to-hazard-center distance, capped at the public
  pseudo-lidar range of 3;
- `d_warn`: warning threshold;
- `d_safe`: recovery threshold;
- `K`: recovery deadline;
- `d_warn < d_safe`: hysteresis between entering warning and completing recovery.

The distance definition was fixed after environment inspection. The formal
2026-08-05 calibration selected `d_warn=0.45`, `d_safe=0.55`, and `K=79`
environment steps. Equality, inclusive deadline, repeated-trigger, terminal,
binary-cost, and policy-state semantics are fixed in
`docs/stage1_rule_monitor_spec.md`.

Older project materials use `d_t < d_warn` directly as the formula antecedent.
That is an intuitive shorthand, not the normative experiment: literal
pointwise semantics would create a new obligation at every unsafe sample.

## 13. Planned Stage I comparison

### Condition A: task reward only

Purpose: measure unconstrained task learning.

### Condition B: native hazard cost

Purpose: measure the behavior produced by the benchmark's existing instantaneous safety signal.

### Condition C: temporal STL cost

Purpose: determine whether an explicit recovery deadline changes behavior beyond an instantaneous cost.

### Optional follow-up: hand-coded timer

Purpose: test whether any benefit comes from STL as a reusable formal representation or merely from equivalent custom temporal logic.

The hand-coded timer is useful but not required for the first smoke test.

## 14. Stage I work sequence

### Step 1: environment inspection

- run the benchmark;
- inspect observations and simulator state;
- define `d_t`;
- log reward and native cost;
- save sample trajectories.

### Step 2: freeze rule semantics

- select `d_warn`, `d_safe`, and `K`;
- use the already fixed boundary and event semantics;
- generate stable success, violation, and unresolved fixtures.

### Step 3: build and validate the monitor

- use RTAMT as the reference;
- implement minimal online state tracking if needed;
- require agreement on declared test cases.

### Step 4: construct the STL cost wrapper

- preserve task reward;
- preserve native cost in logs;
- expose STL cost separately;
- record monitor diagnostics.

### Step 5: run controlled training

- task-only baseline;
- native-cost Safe RL;
- STL-cost Safe RL;
- matched seeds and training settings.

### Step 6: evaluate

- recovery-deadline violation rate;
- warning entries;
- successful recoveries;
- recovery time;
- goal success;
- episode return;
- native cost;
- variation across seeds.

## 15. What Stage I can address

- known static hazards;
- numeric state signals available from simulation;
- bounded response and recovery requirements;
- one controlled navigation benchmark;
- empirical cost-based Safe RL.

## 16. What Stage I cannot establish

- free-form NL-to-STL accuracy;
- automatic inference of missing safety requirements;
- robustness to camera or lidar perception noise;
- dynamic obstacle safety;
- multi-agent interaction;
- real-world deployment;
- zero violations;
- formal guarantees;
- superiority over all shielding or planning methods.

## 17. Meaning of success

Stage I succeeds only if:

1. the rule is physically feasible;
2. monitor judgments are correct;
3. the STL cost reaches the learner as intended;
4. temporal recovery failures decrease;
5. goal completion does not collapse.

Success justifies adding controlled language in Stage II.

It does not establish that the complete language-grounded safety system is solved.

## 18. Current implementation status

The dedicated `stl-stage1` Conda environment was installed and verified on
2026-07-29. Safety-Gymnasium, MuJoCo, OmniSafe, RTAMT, CPU PyTorch, off-screen
rendering, and trajectory saving passed smoke tests.

The public `hazards_lidar` observation was verified as an exact source of the
nearest center-distance signal within its range:

```text
d_t = 3 * (1 - max(hazards_lidar))
```

Sample random and scripted trajectories were saved locally. On 2026-08-05, the
formal 30-controlled/30-random calibration selected the fixed numerical rule.
The public signal extractor, causal online monitor, independent offline oracle,
fixture generator, agreement runner, and a one-command live/video visualization
surface now exist. Twenty-seven tests passed; online/direct event steps and
costs agreed exactly, and RTAMT agreed on all 13 completed windows with maximum
robustness difference 0. The visualization keeps reward, native cost, and STL
cost separate and stores its generated CSV/video/summary artifacts under
`results/visualization/`.

On 2026-08-10, the OmniSafe wrapper and bounded integration smoke gate passed.
Three registered conditions now share the same 63-dimensional augmented policy
observation while independently retaining native cost, STL cost, and selected
algorithm cost. Eleven wrapper-specific tests passed. A real scripted
terminal-unresolved probe produced one positive STL cost and routed the same
value to the learner-cost surface. OmniSafe PPO-Lagrangian then completed a
64-transition, one-epoch CPU rollout and at least one parameter update with two
vector environments. This proves interface compatibility only, not learned
safety behavior.

No matched-seed main RL result exists yet. The next work package must resolve
the quantitative success and evaluation decisions before freezing the three
main experiment configurations. Language translation remains outside Stage I.

## 19. Continuity rule

When future discussions produce a durable conclusion:

- add confirmed decisions to `DECISIONS.md`;
- update the status in `README.md`;
- add exact commands and versions after they have been tested;
- keep the experiment question stable unless a documented reason requires changing it.

The repository documents, rather than any one Codex account's memory, are the authoritative project context.

## 20. 2026-08-10 novelty correction

A targeted literature refresh showed that the previously considered core idea
is already covered by prior work. Existing papers have introduced compact state
augmentation for STL objectives, STL-constrained Lagrangian DRL, online STL
monitor values as RL inputs/rewards, temporal-logic monitor-to-cost PPO, and
full-STL multi-constrained RL.

The project must therefore not claim that the following pipeline is itself new:

```text
given STL -> monitor state/violation cost -> Lagrangian Safe RL
```

Stage I remains technically valid and necessary, but it is now explicitly the
verified gold-STL downstream baseline rather than the final research
contribution.

## 21. Revised project-level research question

The provisional research question is:

> Under the same online Safe RL backend and environment, does an explicit
> NL-to-STL intermediate representation provide better semantic fidelity,
> trace-level diagnosability, and downstream temporal-safety behavior than a
> direct natural-language-to-cost predictor?

This comparison connects three neighboring lines that have largely been studied
separately:

- direct free-form natural-language cost prediction for Safe RL;
- natural-language-to-temporal-logic translation;
- STL-constrained RL with a formula supplied in advance.

The targeted review found no exact controlled study that compares the first and
second paths under the same online Safe RL backend while also measuring
formula-level, trace-label, and policy-level errors. This is provisional rather
than absolute novelty and must be rechecked before submission.

## 22. Consequence for the staged plan

Stage I is unchanged at the implementation level:

```text
gold STL -> verified monitor -> OmniSafe wrapper -> matched Safe RL evaluation
```

Its result supplies the gold semantic reference and downstream feasibility
baseline for Stage II. It is not a mathematical upper bound on policy return or
violation rate.

Stage II is revised to compare:

```text
gold STL -> verified monitor -> fixed Safe RL backend
NL -> STL -> verified monitor -> fixed Safe RL backend
NL -> learned cost predictor -> fixed Safe RL backend
```

Before any expensive RL run, each cost generator is evaluated on the same saved
trajectory corpus against the gold monitor. The language set must include
minimal semantic pairs involving negation, temporal scope, persistence,
deadline changes, conjunction, and disjunction. This makes small but
meaning-changing language edits measurable rather than anecdotal.

The complete novelty evidence, mathematical error decomposition, implementation
resources, and claim limitations are in
`docs/research_direction_novelty_feasibility.md`.

## 23. Current contribution type

The revised direction is initially a benchmark and evaluation problem. Its
artifact will pair controlled temporal-safety language with gold STL, semantic
minimal pairs, trajectory-level oracle labels, and matched Safe RL experiments.
It does not assume in advance that a new learning algorithm is required. If the
comparison reveals a stable failure mode, that evidence will define the later
method contribution.

## 24. Long-term execution continuity

The complete execution route is now recorded in
`docs/END_TO_END_RESEARCH_PIPELINE.md`. It separates the three research stages
from seven executable work packages and defines each package's required inputs,
outputs, acceptance gate, and predefined result branches.

This resolves an earlier handoff weakness: the repository must not tell a new
computer only the immediate next command. After the current gold-STL control is
complete, the documented route continues through controlled benchmark
construction, published and strong-baseline implementation, offline semantic
evaluation, matched online Safe RL comparison, contribution selection, and
external-validity expansion. Only blocking decisions listed in `DECISIONS.md`
require implementation to pause for confirmation.
