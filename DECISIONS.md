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

**Current status (2026-08-12):** the pilot is complete and D35 records that the
safety target was not met while goal non-inferiority passed. The proposal in
`docs/stage1_o8_main_study_decision_proposal.md` recommends a bounded
optimization/budget/credit-assignment diagnostic before freezing a final
standard. Option A (close Stage I), Option B (longer same-method run), and
Option C (bounded diagnostic) remain owner choices. No additional GPU run is
authorized by this proposal.

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

**Current status (2026-08-12):** a non-compute candidate design is recorded in
`docs/stage2_o7_benchmark_design_proposal.md`. It proposes a 30--50-item pilot,
typed grounding, semantic minimal pairs, causal-history fairness, leakage-safe
splits and independent human confirmation. Formula families, exact item count,
split, baselines and numerical offline gates remain unconfirmed until the owner
resolves O7.

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
