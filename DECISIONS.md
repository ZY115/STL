# Decision Log

This file distinguishes fixed decisions, open decisions, and deferred questions. It should be updated whenever the project scope or experiment definition changes.

## Confirmed decisions

### D1. The research remains an NL-to-STL-to-Safe-RL project

The long-term objective has not changed. The current experiment is a controlled prerequisite, not a replacement research problem.

### D2. The task objective and safety requirement are separated

The benchmark's native reward represents goal reaching. STL is initially used to express and evaluate the safety requirement.

The entire natural-language task does not need to become a single STL formula in Stage I.

### D3. STL is not passed directly to RL as text

An STL monitor evaluates trajectory signals. Its output is converted into a safety cost that a Safe RL algorithm can consume.

### D4. The complete study is divided into three stages

- Stage I: manual gold STL;
- Stage II: controlled language with explicit parameters;
- Stage III: broader language and environments.

This order isolates independent failure sources.

### D5. Stage I uses `SafetyPointGoal1-v0`

The environment provides a simple point-navigation task, hazards, a native cost, and compatibility with existing Safe RL tooling.

It is selected to minimize unrelated perception and simulator engineering in the first experiment.

### D6. Stage I uses one temporal rule

The rule is bounded recovery over a derived warning-episode event:

```text
G(e_t -> F_[0,K](d_t >= d_safe))
```

`e_t` is true when the monitor is inactive and the distance first becomes
smaller than `d_warn`. A warning episode remains active until the distance
reaches `d_safe`; oscillation in between does not create overlapping
obligations.

The earlier pointwise formula is only an intuitive shorthand. Its literal
semantics would create an obligation at every unsafe sample, which is not the
fixed Stage I experiment.

Using one event-triggered rule keeps monitor semantics and behavioral
interpretation inspectable.

### D7. The initial Safe RL implementation uses OmniSafe

PPO-Lagrangian is the initial constrained algorithm. The project will reuse an established optimizer rather than implement Safe RL from scratch.

### D8. RTAMT is the reference monitor

RTAMT is intended for offline or reference evaluation of saved trajectories. A small custom stateful monitor may be used online if necessary, but it must agree with the reference monitor on declared test cases.

### D9. Stage I is empirical, not a zero-violation guarantee

The STL rule defines the desired temporal condition. A cost-based Safe RL learner may still violate that condition during training or evaluation.

### D10. The repository remained documentation-first until environment inspection

No experiment directories were created before the Ubuntu environment and available signals were inspected.

The inspection is complete. The later normative specification defined and the
rule-and-monitor milestone created the limited source, test, configuration,
script, fixture, and evidence directories. The OmniSafe wrapper and integration
smoke were subsequently completed in D21; matched training remains unfinished.

### D11. Stage I distance uses the public hazard pseudo-lidar

For Stage I:

```text
d_t = 3 * (1 - max(hazards_lidar))
```

This is the nearest agent-origin-to-hazard-center distance capped at the default
pseudo-lidar range of 3 simulator length units.

Rationale:

- `hazards_lidar` is part of the public policy observation;
- the reconstruction agreed with privileged simulator center distance to
  floating-point precision on 3500 collected steps;
- center distance aligns directly with the benchmark's native hazard-distance
  calculation;
- no privileged simulator state is required by the monitor.

Expected impact:

- later thresholds must satisfy `d_warn < d_safe < 3`;
- `d_t` must not be described as physical boundary-to-boundary clearance;
- simulator positions remain available only as a validation diagnostic.

### D12. Equality and deadline semantics are fixed

- `d_t == d_warn` is not warning;
- `d_t == d_safe` is recovery;
- a deadline at `t_0 + K` is inclusive;
- recovery on the deadline sample succeeds;
- recovery one sample later is late;
- predicate comparisons do not use an epsilon.

A tolerance of `1e-9` is used only to compare independently computed
real-valued robustness values.

### D13. The monitor uses one hysteretic warning episode

Each environment has one of three monitor states:

- `INACTIVE`;
- `PENDING`;
- `OVERDUE`.

A warning episode begins only from `INACTIVE`, remains active through the band
between `d_warn` and `d_safe`, and closes only at `d_t >= d_safe`. Missing the
deadline emits one violation event and moves the episode to `OVERDUE`; it does
not emit a new violation on every later step.

### D14. Unfinished terminal obligations are explicit

If an episode terminates or truncates before a pending deadline, the result is
reported as `terminal_unresolved`, not silently satisfied or retroactively
called a completed deadline violation.

For training, this unresolved event receives one conservative binary cost so
that ending the episode cannot erase an active obligation. A deadline violation
already emitted on the final sample is not counted again.

### D15. The first STL cost is a sparse binary event cost

`stl_cost` is 1 only when:

- a recovery deadline is missed; or
- a pending obligation becomes terminal-unresolved.

It is 0 on warning entry, ordinary pending steps, recovery, and overdue steps
after the first violation. Robustness is diagnostic only in the first
implementation.

### D16. Temporal monitor state is added to every policy condition

The wrapper will append:

- active-obligation indicator;
- overdue indicator;
- normalized remaining deadline.

Task-only, native-cost, and STL-cost conditions receive the same augmented
observation. This avoids both hidden temporal state and an observation advantage
for only one condition.

### D17. Incomplete traces do not inherit undocumented library semantics

The custom online monitor is checked against a direct offline enumerator.
RTAMT is used on completed obligation windows. Pending terminal windows are
classified explicitly as unresolved rather than relying on a monitor library's
finite-trace default.

### D18. Rule semantics are frozen before numerical calibration

`docs/stage1_rule_monitor_spec.md` is the normative rule and monitor contract.
The Ubuntu machine must supply calibration evidence for `d_warn`, `d_safe`, and
`K`, but no further semantic choice is required before implementing synthetic
tests.

### D19. Stage I numerical rule parameters are calibrated

The formal 2026-08-05 run selected:

```text
d_warn = 0.45
d_safe = 0.55
K = 79 environment steps
```

All 30 controlled trials produced valid recoveries. The selected recovery-time
Q95 was 63 steps, so the predeclared equation produced
`ceil(1.25 * 63) = 79`. Its random-policy trigger rate was 17/30 (56.67%), the
eligible primary-grid rate closest to 50%.

### D20. The rule-and-monitor completion gate passed

The online monitor, independent direct oracle, stable environment fixtures, and
RTAMT completed-window checks passed with zero event-step, Boolean, cost, or
robustness mismatches. At this gate, the wrapper was still the next work package;
D21 records its subsequent completion. This monitor result alone is not an RL
result or safety guarantee.

### D21. The OmniSafe wrapper and integration-smoke gate passed

The three registered conditions are:

```text
Stage1SafetyPointGoal1TaskOnly-v0
Stage1SafetyPointGoal1NativeCost-v0
Stage1SafetyPointGoal1STLCost-v0
```

Every condition receives the same original 60-dimensional observation plus
`active`, `overdue`, and normalized remaining-deadline state. The environment
always logs native cost, STL cost, and selected algorithm cost separately; only
the selected cost returned to OmniSafe differs.

Terminal vector transitions are evaluated from `final_observation` before the
corresponding monitor is reset from the auto-reset observation. Eleven new
wrapper tests passed. A real positive-cost probe and a 64-transition,
single-epoch PPO-Lagrangian CPU update passed on 2026-08-10. This closes the
interface milestone but is not a main training result or safety guarantee.

### D22. Stage I is not claimed as a novel STL-to-Safe-RL algorithm

A literature refresh through 2026-08-10 found direct prior work on:

- augmented state for STL-guided RL;
- STL-constrained Lagrangian DRL;
- online STL values used as RL observations or rewards;
- temporal-logic monitor violations converted into PPO-Lagrangian costs;
- full-STL multi-constrained RL.

Therefore, monitor state, logic-to-cost conversion, and Lagrangian Safe RL are
not standalone novelty claims. Stage I is the verified gold-STL downstream
baseline and an error-isolation experiment for the broader language-grounded
project.

### D23. The current project-level research question compares representations

The provisional research question is:

> Under the same online Safe RL backend and environment, does an explicit
> NL-to-STL intermediate representation provide better semantic fidelity,
> trace-level diagnosability, and downstream temporal-safety behavior than a
> direct natural-language-to-cost predictor?

The two paths must share the same task reward, Safe RL algorithm, policy
architecture, cost budget, seeds, and gold offline evaluation oracle. Their
train/test specification split and evaluation trajectories must be matched.
Different supervision types, annotation counts, model capacities, and
pretrained resources must be disclosed.

### D24. Stage I provides the gold-STL reference condition for Stage II

Stage I remains unchanged at the implementation level. Its result will establish
whether the downstream path works when translation and language grounding errors
are removed. This is a semantic reference and feasibility baseline, not a
mathematical upper bound on policy performance. Stage II must include at least:

- human-verified gold STL;
- explicit NL-to-STL followed by the verified monitor;
- direct language-conditioned cost prediction.

The expensive RL comparison must be preceded by formula-level and trace-level
cost-label evaluation.

### D25. Novelty language remains provisional

The targeted review found no exact controlled comparison matching D23 as of
2026-08-10. This is not proof of universal absence. The literature search must
be refreshed before paper submission, and the project must not claim the first
use of STL in RL, STL in Safe RL, temporal monitor state, or logic-to-cost PPO.

The detailed evidence and revised experimental path are recorded in
`docs/research_direction_novelty_feasibility.md`.

### D26. The first project-level contribution is framed as a controlled benchmark

The project will first build an evaluation protocol containing controlled
language/formula pairs, semantic minimal pairs, saved trajectories, gold
monitor labels, and matched downstream Safe RL settings. It will not promise a
new translator, monitor, or optimizer in advance. A method contribution should
be designed only after this comparison identifies a reproducible limitation in
existing explicit-formal or direct-cost approaches.

### D27. The end-to-end pipeline is the authoritative long-term execution map

`docs/END_TO_END_RESEARCH_PIPELINE.md` defines the complete sequence from the
current gold-STL control through controlled benchmark construction, baseline
reproduction, offline semantic evaluation, matched online Safe RL comparison,
predefined result branches, method refinement, and broader validation.

Completing an immediate work package does not require redesigning the project
from scratch. The next unfinished work package in that document becomes the
default next objective unless a blocking open decision is explicitly listed
here.

### D28. Stage I controls are not representation-method baselines

Task-only, native hazard cost, and gold-STL cost are downstream control
conditions. They establish task learnability, an instantaneous geometric-cost
reference, and the gold formal reference. They do not replace comparisons with
published natural-language safety methods.

The Stage II representation comparison must include an explicit NL-to-STL path,
a published-style direct NL-to-cost baseline, and a history-aware direct-cost
baseline capable of representing bounded temporal requirements.

### D29. The project does not yet have a confirmed novel algorithm

The explicit formal path is currently `our candidate formal pipeline`, not a
confirmed novel method. Its hypothesized advantages are explicit temporal
semantics, conditional monitor correctness, inspectable error decomposition,
and violation-event cost construction. These advantages must be tested against
strong baselines under matched information and compute reporting.

If no new algorithmic component is added, the contribution must be framed as a
controlled benchmark, evaluation protocol, and error analysis. A method claim
requires a specific mechanism motivated by a measured failure mode, a closest
prior-work comparison, and an ablation.

### D30. The pre-main engineering gate passed

On 2026-08-11, a 2000-transition PPOLag sanity used two complete 1000-step
episodes and an explicit `lagrange_cfgs.cost_limit=0.1`. At least one actor-
sampled episode produced a deadline violation and `stl_cost=1`; the mean STL
and selected episode costs were both 0.5, and the Lagrange multiplier responded.

A common checkpoint evaluator now evaluates every policy with the same gold
STL wrapper, rechecks every trajectory with the independent direct oracle, and
uses RTAMT on completed windows. Its three-episode smoke had zero event/cost
mismatches and zero robustness difference. These are engineering facts, not
behavioral comparison results.

At the time of D30 the numerical protocol was still a proposal. D31 records its
subsequent approval as a Stage I pilot protocol.

### D31. O6 is approved as the Stage I pilot protocol only

On 2026-08-11 the project owner approved the following predeclared pilot
protocol. It is **not** the final main-study standard.

- The primary safety metric is missed recovery obligations divided by triggered
  recovery obligations. A missed obligation is a deadline violation or a
  terminal-unresolved pending obligation; the two components remain separately
  reported.
- The primary comparison is gold-STL cost versus task-only. The pilot target is
  at least a 30% relative reduction, with the absolute difference also reported.
  If the task-only rate is zero, relative reduction is undefined and the
  absolute difference is used.
- Goal success has a 10-percentage-point non-inferiority margin.
- Training uses five matched seeds: `1101, 2202, 3303, 4404, 5505`.
- Each final checkpoint is evaluated on the same 100 seeds per training seed and
  condition, using the same deterministic policy mode and gold-STL evaluator.
- Uncertainty uses 10,000 paired hierarchical bootstrap replicates, resampling
  training seeds and matched evaluation episodes within seed.
- Candidate PPOLag cost limits are task/native/STL = `0.0/25.0/0.1`.
  Native cost is measured in hazard-cost steps per episode; STL cost is measured
  in missed-obligation events per episode. These are different units.
- `STL cost_limit=0.1` means 0.1 missed-obligation events per episode. It is not
  automatically a 10% obligation-violation rate because episodes may trigger
  zero, one, or more obligations.
- One million transitions per condition and seed is a pilot budget only. The
  learning curves must be inspected before any convergence claim.

The exact frozen protocol and condition overlays are under
`configs/stage1_pilot/`. Before any full 1M run, the three-condition
small-budget sanity gate must pass. Approval of D31 does not authorize silently
changing the fixed Stage I semantics, selecting a best checkpoint after seeing
evaluation results, or claiming a final main-study standard.

### D32. Stage I pilot training uses the verified RTX 4090 CUDA backend

On 2026-08-11 the project owner explicitly requested CUDA enablement and stated
that CUDA is available on this machine. Inspection and validation confirmed:

- NVIDIA GeForce RTX 4090 with 24,564 MiB VRAM;
- NVIDIA driver `560.35.03`, reporting CUDA compatibility `12.6`;
- PyTorch `2.4.1+cu124` with CUDA runtime `12.4` and cuDNN `9.1.0`;
- compute capability `8.9`;
- CUDA tensors through the Stage I wrapper;
- a real full-horizon PPOLag CUDA rollout/update with positive STL event cost,
  exact selected-cost routing, multiplier update, and checkpoint output.

Therefore the frozen pilot training device is `cuda:0`. This changes the
computational backend, not the D31 scientific metric, seeds, budgets, cost
semantics, or evaluation protocol. All three conditions must use the same GPU
backend. Final checkpoints continue to use the same deterministic gold-STL
evaluation path. CPU-only historical sanity runs remain engineering history and
must not be mixed with the CUDA pilot results.

### D33. Current execution uses bounded autonomy instead of one-step handoffs

The long-term research map and the current execution directive have different
roles:

- `docs/END_TO_END_RESEARCH_PIPELINE.md` defines WP1--WP7 and result branches;
- `docs/CURRENT_EXECUTION_DIRECTIVE.md` defines the complete currently
  authorized implementation package and its next explicit stop gate.

An agent must complete all unblocked tasks in the current directive without
requesting a new instruction after each file, test, or bounded preflight. It
stops only for an explicitly listed scientific-scope decision, material compute
authorization, protocol change, or unresolved technical blocker.

The current authorized package is the resumable full-pilot runner, frozen
analysis module, tests, and one excluded 100k exact-scale preflight. The full
15M-transition pilot remains a single owner compute gate because it is expected
to require substantial GPU time and create the first behavioral dataset. After
that launch is approved, all 15 runs, 1,500 paired evaluations, analysis, WP1
report, O8 proposal, and the non-compute WP2/O7 proposal proceed continuously.

### D34. The full-pilot launch-preparation gate passed

On 2026-08-11 the complete package authorized by D33 passed:

- a deterministic, job-resumable 15-cell condition/seed runner;
- immutable attempt evidence and hash-verified successful-job skipping;
- fixed-final-checkpoint immediate evaluation for each job;
- the frozen D31 paired hierarchical analysis and 11 focused tests;
- one excluded 100k exact-scale `gold_stl_cost` CUDA preflight using seed
  `20260811` and ten excluded evaluation seeds;
- a launch-readiness report with measured resources and recovery procedure.

The preflight measured 335.68 transitions/second, 297.90 seconds for 100k
training transitions, 17.21 seconds for ten evaluations, and 90 MiB PyTorch
peak reserved VRAM. A linear projection gives approximately 13.13 hours for
the 15 full training jobs plus 1,500 evaluations. All routing, fixed-checkpoint,
direct-oracle and RTAMT checks passed. Two earlier attempts failed before Agent
construction or rollout and executed zero transitions; their device-index and
explicit-environment-registration causes were fixed and retained.

This decision closes implementation/preflight readiness only. No frozen seed
has run, and it does not approve the full 15M-transition compute package,
change D31/D32, establish convergence, or provide behavioral evidence. The
single owner launch authorization remains required.

### D35. The authorized Stage I pilot completed without meeting its safety target

After explicit owner authorization, all 15 frozen jobs completed on 2026-08-12:
three conditions, five matched training seeds, one million transitions per job,
and 100 deterministic paired final-checkpoint evaluations per job. All manifest
and artifact hashes passed; all 1,500 online/direct-oracle comparisons agreed;
and the maximum RTAMT robustness difference was zero.

Under the D31 primary metric, task-only missed `25.85%` of triggered recovery
obligations and gold-STL cost missed `26.03%`. The task-minus-gold absolute
reduction was `-0.18` percentage points (95% paired hierarchical bootstrap
interval `[-5.52, +6.87]`), and the relative reduction was `-0.71%`
(`[-24.92%, +21.88%]`). The predeclared 30% relative-reduction pilot target was
not met. Task-only and gold-STL both achieved 100% goal success; the 10-point
goal-success non-inferiority criterion passed.

The final 20-epoch gold-STL selected cost averaged 1.650 missed events per
episode against the 0.1 limit, while its multiplier averaged 3.217 and retained
tail drift in four of five seeds. Native cost also remained above its own
different-unit budget. Therefore the one-million-transition budget is not
declared converged, and this pilot is not promoted to the final main-study
standard.

These facts establish a valid negative pilot result: the verified cost path ran
but did not improve the primary behavior under the frozen settings. They do not
change the rule, establish formal safety, prove that STL is generally
ineffective, or authorize a post-hoc best checkpoint. Full evidence is in
`docs/stage1_pilot_result_report.md`.

### D36. Post-pilot execution moves offline before another RL run

On 2026-08-12 the project owner requested a complete post-pilot route rather
than another one-step handoff. The current authorized package is therefore:

1. preserve the completed Stage I pilot as a negative diagnostic result;
2. diagnose the Gold-STL baseline using existing checkpoints and trajectories,
   without new training;
3. build the Stage II v0 offline benchmark foundation, Gold trace labels and
   validation tools;
4. prepare the formal, published-style direct and history-aware direct baseline
   specifications as one combined review package.

This decision does not authorize another long GPU run, select a final shaping
method, freeze the final O7 dataset, or resolve the final online comparison
protocol. The exact continuous work order, outputs and gates are defined in
`docs/CURRENT_EXECUTION_DIRECTIVE.md`.

### D37. O7 benchmark and Stage II-A design are frozen

On 2026-08-12 the project owner requested that O7 be resolved and that the work
computer continue beyond the machine-foundation draft. The following design is
now fixed for the Stage II v0 controlled comparison:

- 40 canonical specifications and two paraphrases per specification;
- eight specifications in each of bounded recovery, recovery-persistence,
  bounded avoidance, conjunction and disjunction families;
- a typed-AST representation over the public nearest-hazard distance signal;
- 20 train, eight validation, four parameter-test and eight held-out
  disjunction structure-test specifications;
- a local `google-t5/t5-base` structured formal translator;
- a MiniLM current-observation direct adaptation as a published-style
  structural ablation;
- a MiniLM plus GRU-128 causal-history direct model as the primary direct
  opponent;
- no paid API or proprietary model in v0;
- predeclared trace, boundary, minimal-pair and paraphrase admission thresholds;
- final truth from the unchanged Gold evaluator.

The exact composition, parameter tuples, split, supervision, metrics and gates
are normative in `docs/STAGE2_CONTINUOUS_WORK_ORDER.md`.

This resolves the owner design decisions in O7. It does not fabricate the
independent human review required for Gold release. Every item still requires a
named human reviewer different from its author before held-out evaluation. The
work computer may implement methods and use train/validation drafts while that
external review gate is pending, but test Gold labels must remain unavailable
to model code.

### D38. Continuous spatial, offline and bounded-online execution is authorized

The work computer is authorized to execute the continuous package in
`docs/STAGE2_CONTINUOUS_WORK_ORDER.md`:

1. reproduce existing checkpoints with diagnostic-only geometry and generate
   true top-down trajectory figures;
2. implement the D37 dataset, formula evaluators and Stage II-A baselines;
3. run held-out Stage II-A only after independent review;
4. implement the project-owned terminal cost-bootstrap repair and the bounded
   predeclared Gold learner-cost matrix;
5. freeze one common online cost interface only if its gate passes;
6. run the 10k routing sanity and three-seed/300k bounded Stage II-B pilot.

For any training process, the agent verifies one real update/epoch, finite
metrics, GPU activity, checkpoint output and ETA. If remaining time exceeds 20
minutes, it leaves the resumable job running, records PID, hashes, logs, ETA and
resume commands, and stops continuous monitoring. This authorization does not
cover a five-seed, one-million-transition confirmatory Stage II-B main study.

### D39. The implemented D37 parameter matrix contains six documented logical aliases

Machine construction of all 40 frozen specifications found distinguishing
traces for 109 of 115 required adjacent-parameter or same-index structure
contrasts. The remaining six cannot have a witness under the current event
semantics and parameter values: `br-v0-006/007/008` equal their same-index OR
records, and `ba-v0-006/007/008` equal their same-index AND records.

The implementation must classify and report these aliases rather than invent a
trace or silently alter D37. Train/validation work may continue because the
records and splits remain frozen, but the final Stage II v0 dataset gate stays
closed until the owner prospectively accepts the aliases as hard cases or
records an amended parameter matrix and expected impact. This finding does not
release held-out Gold labels.

### D40. D38 diagnostic implementation details are frozen before training

The bounded Gold learner-cost implementation uses new matched training seeds
`7307`, `8419` and `9521`, which do not overlap the Stage I pilot. It contains
five cells per seed: one task-only control and C0/C1 crossed with existing
`lambda_init=0.001` or early-pressure `lambda_init=0.1`. C0 and C1 limits are
derived separately as 70% of their own matched pre-diagnostic task-only mean;
their numerical units must never be copied.

The project-owned runtime preserves reward timeout bootstrap but sets cost
bootstrap to zero when terminal-unresolved has already settled the Gold
obligation. The actor learning-rate schedule has floor `3e-5`, and the required
per-epoch mechanism diagnostics are frozen in
`configs/stage2_gold_diagnostic/protocol.yaml`. This is still the non-confirmatory
300k D38 diagnosis and does not authorize Stage II-B unless its gates and both
primary offline gates pass.

### D41. Repeated host machine-check events stop new research training

The first real Stage II-A formal run encountered kernel machine-check events at
`22:52:01` and `22:57:29`, followed by a `pt_autograd_0` segmentation fault in
`libstdc++` at `23:03:27`. A clean from-scratch retry reproduced two finite
epochs, but the kernel recorded another machine-check event at `23:15:31`.
There was no logged CUDA Xid, OOM or non-finite training value.

Because this satisfies the prospectively declared repeated-technical-failure
stop condition, all new Stage II-A and Gold-diagnostic GPU training is paused.
Partial formal checkpoints remain diagnosis-only and are not accepted results.
This does not change D37/D38 models, data, seeds, costs or gates. Training may
resume only after administrator-level hardware investigation and a clean
stability gate consisting of independent CPU/RAM checks plus one discarded
formal epoch with no new MCE, segfault, CUDA Xid, OOM or non-finite value.
CPU-only replay, artifact generation, validation and documentation may continue.

### D42. Add a fixed-route controlled variant with narrower STL geometry

On 2026-08-13 the project owner selected a controlled variant of
`SafetyPointGoal1-v0` to make policy trajectories and three-condition differences
easier to interpret. The variant keeps the benchmark dynamics and task but
fixes the initial pose, eight-hazard layout, vase and four-goal sequence. It
fixes requested waypoints, not the agent's realized trajectory; the policy
continues to choose every action.

The candidate center-distance thresholds are prospectively fixed as
`d_warn=0.25` and `d_safe=0.28`. The historical `K=79` must not be transferred
because it was calibrated for `0.45 -> 0.55`; the new deadline remains open
until a new recovery calibration and online/direct-oracle/RTAMT boundary check
pass. The historical Stage I rule, pilot configs, checkpoints and conclusions
remain unchanged.

All three conditions use identical fixed geometry and the same Gold STL rule
for evaluation. Task-only still returns zero learner cost, Native-safety returns
only the simulator hazard cost, and STL-safety returns the chosen STL learner
cost. Warning/safe circles in all three plots are therefore a common evaluation
overlay, not evidence that all three policies trained on STL cost.

The fixed-route experiment is a controlled diagnostic. A positive result still
requires held-out randomized-layout or additional-route evaluation before any
generalization claim. Exact geometry, gates and execution order are defined in
`docs/FIXED_ROUTE_V1_WORK_ORDER.md`.

### D43. The first fixed-route training is a 30-minute quick-turn diagnostic

On 2026-08-13 the project owner rejected another many-hour first result and
authorized one short fixed-route diagnostic. It uses one new matched seed and
targets 150,000 transitions for each of Task-only, Native-safety and
STL-dense-safety, with a 30-minute aggregate training cap. A 10k preflight may
reduce all three reported cells to the same 10k transition multiple if required
by measured throughput, but never in response to policy outcomes and never
below 50k.

The STL training cell uses the already implemented C1 causal dense learner cost
because the historical 1M-transition C0 sparse binary event pilot did not alter
behavior. Unchanged Gold binary bounded-recovery events remain the common
evaluation truth. Task-only is trained first; its short stochastic evaluation
freezes separate provisional Native and C1 cost limits at 70% of their own
means before either constrained cell starts.

Immediately after the three final checkpoints, the work computer must produce
matched exploratory metrics and a three-panel real trajectory figure on the
fixed scenario. It then stops. This diagnostic may establish routing, runtime
and visible early behavioral separation, but not convergence, significance,
method superiority or generalization. D41 hardware recovery and the new
fixed-route deadline calibration remain mandatory launch gates. The exact
machine-readable protocol is `configs/fixed_route_v1/quick_turn.yaml`.

### D44. Fixed-route v1 uses a separately calibrated 25-step deadline

On 2026-08-13 the D42 lifecycle and calibration gate passed on the real pinned
environment. Thirty deterministic approach/retreat trials all triggered and
recovered in 20 environment steps. Applying the predeclared Stage I rule
`max(5, ceil(1.25 * linear empirical Q95))` gives `K=25`. Online monitor,
independent oracle and RTAMT agreed on all 30 completed windows with zero event
mismatches and zero maximum robustness difference.

The fixed-route executable rule is isolated in
`configs/fixed_route_v1/rule.yaml`; the historical Stage I `0.45/0.55/K=79`
rule and pilot evidence remain unchanged. This closes the D42 deadline,
lifecycle and render gates, but does not clear D41 or authorize bypassing its
administrator CPU/RAM tests and discarded formal epoch.

### D45. Administrator authorizes the bounded D43 run despite uncleared D41 tests

On 2026-08-13 the repository owner and machine administrator explicitly
authorized starting the modified fixed-route Stage I training and producing its
figures. This accepts the known prior MCE/segfault risk for D43 only; it does not
claim that CPU/RAM stability tests or the discarded formal epoch passed.

The override covers the three excluded 10k preflights, one-seed bounded D43
reported training, fixed-checkpoint evaluation and plotting. All existing stop
rules remain active. It does not authorize Stage II-A full training, the D38
matrix, or a confirmatory main study. The machine-readable scope is
`configs/fixed_route_v1/d41_admin_override.yaml`.

### D46. The D43 fixed-route quick-turn is complete and remains exploratory

The administrator-authorized D43 package completed on 2026-08-13. A throughput
contract defect was found during execution: the first 10k preflight used one
optimizer iteration while a reported epoch used 40, so its 150k estimate was
not comparable. The 150k task-only attempt was stopped after 40k transitions,
retained as a failed diagnostic attempt and counted against the aggregate time
cap. The preflight implementation was corrected to use the same 40-iteration
optimizer workload. Three new excluded preflights then prospectively selected
70k matched transitions per condition without observing policy outcomes.

Task-only, Native-safety and STL-dense-safety all produced finite final
checkpoints with exact learner-cost routing and no new logged MCE, segfault,
CUDA Xid or OOM. Including the interrupted attempt, reported-training time was
1,395.16 seconds, below the 1,800-second cap. The separate task-control limits
were 34.23 native-cost units/episode and 67.7021 C1 surrogate-mass
units/episode; the units are not interchangeable.

On the 20 paired stochastic final-checkpoint episodes, Gold missed obligations
per trigger were 27/29 (0.931) for task-only, 27/40 (0.675) for Native and
31/55 (0.564) for STL-dense. The STL-dense point estimate is a 0.367 absolute
and 39.5% relative reduction versus task-only; all three goal-success rates
were 100%. This is evidence that the bounded implementation can produce visible
early behavioral separation. It is not a convergence, significance,
superiority, generalization or safety-guarantee claim because D43 used one
training seed and 20 evaluation episodes. Learning curves were still rising,
selected costs oscillated and both constrained multipliers reached zero during
the short run. No automatic extension, D38 matrix, Stage II-A restart or
confirmatory study is authorized by this result.

### D47. Authorize one long fixed-route round with C1 dense learner cost

On 2026-08-13 the repository owner and machine administrator explicitly
authorized another complete training round and requested a non-sparse STL
learner cost. The authorized unit is one new matched training seed (`12647`)
with Task-only, Native-safety and STL-dense-safety each trained from scratch for
1,000,000 transitions on fixed-route v1. This is a long exploratory round, not
the five-seed confirmatory main study.

The STL training condition must use the already frozen C1 causal dense
surrogate. While a recovery obligation is active and has not yet been missed,
the step cost is the clipped equal mixture of normalized distance deficit and
deadline urgency; an actual missed obligation still emits one. Inactive steps
emit zero. This changes neither the Gold STL semantics nor the final primary
safety metric: fixed-checkpoint evaluation continues to use binary missed
recovery obligations divided by triggered obligations. Native and C1 budgets
are derived separately from the new final Task-only checkpoint and remain in
different units.

Three excluded 10k preflights must first prove exact routing, positive source
cost, finite CUDA optimization, checkpoint creation and, specifically for the
STL condition, C1 accumulated cost strictly greater than binary missed-event
cost. Only then may the background runner continue through the three 1M cells
and 100 paired final evaluations. The owner requested monitoring only through
successful startup; after that the healthy process is left running for manual
observation.

This authorization accepts the known prior MCE/segfault risk only for
`fixed_route_v1_full_dense_round`; it does not claim D41 passed and does not
authorize D38, Stage II training or a five-seed confirmation. The frozen
machine-readable protocol and scoped override are
`configs/fixed_route_v1/full_dense_round.yaml` and
`configs/fixed_route_v1/d41_full_dense_admin_override.yaml`.

### D48. The single-seed full C1-dense round is a negative exploratory result

The D47 training process ran all three conditions to their fixed 1,000,000-
transition checkpoints on 2026-08-13. Its automatic post-run gate initially
reported the STL cell as failed because one of 100 CSV rows differed between
the selected-cost and dense-cost logger accumulators by `3.8147e-6` at scale
`42.2763` (approximately `9.0e-8` relative). The tensors are the same at the
environment interface, all values were finite, the other 99 rows matched
exactly, and the final checkpoint was complete. D48 corrects this engineering
validator to a scale-aware `rel_tol=1e-7, abs_tol=1e-6`, retains the original
failed manifest, and records a separate validated-completion artifact. This
does not change any policy, checkpoint or research metric.

On the frozen 100 paired stochastic evaluation episodes, Gold missed recovery
obligations per trigger were `0/268` for Task-only, `0/345` for Native-safety
and `31/139=0.223` for STL-dense-safety. Because the Task-only rate is zero,
the protocol's absolute-difference rule applies: Task-minus-STL is `-0.223`
(descriptive paired episode-bootstrap 95% interval `-0.313` to `-0.139`). The
STL condition therefore fails the intended safety direction; no relative
reduction is defined. All goal-success rates were 100%, but mean return was
35.674/31.694/17.477 and mean native cost was 2.420/0.020/8.730 for
Task/Native/STL respectively.

C1 was demonstrably non-sparse, but its last-20-epoch selected cost remained
above its separately frozen budget (`16.535` versus `10.995`), its Lagrange
multiplier was still increasing, and its return curve was not stable. This run
does not support convergence or an STL-specific safety benefit. A plausible
mechanism is that accumulated pending-obligation mass encourages fewer warning
entries without teaching reliable recovery after entry, but that remains a
diagnostic hypothesis. No additional training is authorized by D48; mechanism
analysis or any held-out route/layout evaluation must be defined before use.

### D49. Owner authorizes guarded Stage II compute continuation after hardware inspection

On 2026-08-14 the owner reported that the work-computer hardware had been
investigated and no actionable repair was identified. This does not rewrite the
historical D41 events as a clean hardware pass. It authorizes resuming the
frozen Stage II-A and Gold-diagnostic compute path under guarded execution.

Every new training package must retain the existing config/hash checks, smallest
real update or epoch, finite-metric check, checkpoint proof, GPU/host telemetry
and kernel-event comparison. If an MCE, native crash, CUDA Xid, OOM or non-finite
result recurs, the work computer first preserves the failed attempt and performs
local evidence collection and diagnosis. It may apply reproducible repository,
environment or user-space fixes and run one clean from-scratch validation retry.
It must request human help only when the problem requires administrator/hardware
action, changes a frozen research contract, or remains unresolved after the
controlled retry. A failed attempt is never promoted to a research result.

### D50. Jiahui independently approves the 35 previously pending specifications

On 2026-08-14 the owner confirmed that engineer `jiahui` independently reviewed
the 35 records that were pending after the five historical Yuhang approvals.
For the current specification revision, all nine checklist fields are approved,
with no disagreement note. `reviews.json` and `specifications.json` record this
decision while preserving the original five Yuhang records.

This approval is content-specific. D51 changes parameters to remove logical
aliases; every record whose language, typed AST, STL, grounding or parameters
changes must automatically return to pending review. The freeze tool preserves
an approval only when all reviewable content is unchanged. Held-out labels
remain closed until the alias amendment has full distinguishing-trace coverage
and every changed record is independently reviewed again.

### D51. Replace the six logical aliases with a prospective parameter amendment

The owner rejects retaining the six D39 aliases as benchmark hard cases. Before
held-out predictions or labels are exposed, the work computer must implement the
smallest coherent parameter-matrix amendment that makes every AND/OR record
distinguishable from its component formulas on at least one deterministic trace.

The amendment must preserve the five formula families, 20/8/4/8 split counts,
held-out OR structure policy, public signal, finite-trace semantics and absence
of test leakage. It must record all changed specification IDs and an impact
analysis, regenerate language/AST/STL/trace artifacts and hashes, reduce
`missing_witness_count` from six to zero, and produce a delta human-review packet
containing only changed records. No held-out model evaluation may run before the
delta review closes. Parameter choices must be made from semantic feasibility
and witness construction, never from model predictions.

### D52. D48 is followed by mechanism analysis and the unchanged bounded C0/C1 matrix

Before new Gold learner-cost training, analyze the existing D47/D48 artifacts:
C1 distance/urgency mass around trigger and recovery windows, cost-value and
advantage scale, reward/cost gradient balance, trigger avoidance, recovery
reliability, multiplier behavior and budget pressure. This analysis may not
change the Gold evaluator.

After the report is complete, execute the already registered D38/D40 matrix:
three seeds, 300k transitions, C0/C1 crossed with the two frozen Lagrange
initializations and separately derived budgets. Do not add a C2 cost, search
extra weights, alter limits after outcomes, or otherwise introduce a new free
parameter search. If no C0/C1 cell passes the predeclared screening gate, end
the online branch, preserve the negative result and complete Stage II with the
offline comparison and downstream-bottleneck analysis.

### D53. Stage II online work is split into B1 and conditional B2 with a 20-hour launch gate

Stage II-B1 keeps `br-v0-001` as the minimal online error-propagation pilot. It
may start only after the reviewed alias-free Stage II-A gate and one Gold
learner-cost cell pass. Stage II-B2 is conditional on B1 and the offline gate;
it adds `rp-v0-001` plus the prospectively fixed non-alias composition
`or-v0-001`. Both B2 specifications require online feasibility calibration and
unchanged Gold evaluation before training. A failed feasibility check stops B2
instead of substituting a result-selected specification.

Before B1 or B2, estimate aggregate wall-clock time on the work computer using
a workload-matched preflight. An online package with projected aggregate
training time at or below 20 hours may start automatically after all gates pass.
If the estimate exceeds 20 hours, automatic launch is allowed only under the
strict upstream-perfect exception: alias/review/leakage gates are clean; both
primary offline methods pass every admission metric for all three seeds; the
selected Gold learner-cost cell passes every screening criterion for all three
seeds; and workload-matched online preflight has no technical warning. B2 also
requires B1 to pass all three seeds. Otherwise do not launch. Produce a decision
package with gate evidence, per-condition runtime, total GPU-hours, disk estimate
and resumable command, then request explicit owner authorization. Long online
training is not justified merely because its code path works.

## Open decisions

### O6. Quantitative Stage I pilot protocol — resolved by D31

**Current status (2026-08-12):** resolved and executed for the pilot only. D31
and `configs/stage1_pilot/` remain the authoritative frozen protocol; D35
records the completed result. O6 is not the final main-study standard.

### O8. Final main-study quantitative standard

The Stage I pilot protocol is not automatically the final main-study standard.
After the sanity gate and pilot, decide prospectively whether the final study
requires a larger training budget, more training seeds, more evaluation
episodes, a different uncertainty interval, or a predeclared cost-budget sweep.
This decision must use the pilot's learning-curve stability and feasibility
evidence without relabeling pilot-selected settings as independently confirmed
main-study hypotheses.

**Current status (2026-08-12):** D38 selects the bounded diagnostic path and
authorizes only the C0/C1 matrix defined in
`docs/STAGE2_CONTINUOUS_WORK_ORDER.md`. The old same-method run must not be
repeated. O8 remains open only for a later confirmatory main-study standard:
the bounded diagnostic result will determine whether such a study is justified,
but D38 does not authorize a five-seed, one-million-transition confirmation.

### O7. Stage II controlled language and direct-cost baseline

Before Stage II implementation, fix:

- the supported STL formula templates;
- the semantic minimal-pair taxonomy;
- the direct NL-to-cost baseline implementation;
- which published implementation is reproduced exactly and which components
  are adapted to this benchmark;
- the causal-history representation for the strong direct-cost baseline;
- the NL-to-STL translator implementation;
- formula-equivalence and trace-label metrics;
- whether a human formula-confirmation condition is included.

**Current status (2026-08-12):** owner design resolved by D37. The 40-item
composition, split, local model choices, resource boundary and numerical
offline gates are frozen in `docs/STAGE2_CONTINUOUS_WORK_ORDER.md`. The existing
five-item machine foundation must now be expanded. Independent human review is
an implementation/release gate, not an unresolved owner design choice; held-out
Gold evaluation remains prohibited until it is complete.

## Deferred to Stage II

- controlled natural-language command format;
- language-to-STL model choice;
- translation accuracy metric;
- atomic proposition and parameter grounding;
- handling syntactically valid but semantically wrong formulas;
- separating translation error from downstream control error.

## Deferred to Stage III or later

- vague or missing numerical safety requirements;
- automatic requirement completion;
- perception uncertainty;
- dynamic obstacles;
- multiple agents;
- UAV applications;
- MILP formula repair;
- shielding and runtime intervention;
- counterexample feedback to the language model;
- formal guarantees and real-robot deployment.
