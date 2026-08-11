# Research Direction Novelty and Feasibility Review

- **Review date:** 2026-08-10
- **Status:** current research-positioning document
- **Scope:** literature available through the review date

## 1. Decision Summary

The earlier candidate contribution was:

> Convert an STL specification into monitor state and violation cost, then use
> the result with Lagrangian Safe RL.

This is **not a defensible novelty claim**. Closely matching prior work already
includes:

- compact augmented state for STL-guided RL;
- STL constraints formulated through an extended CMDP and Lagrangian DRL;
- online STL robustness used as observations or reward components;
- LTL monitors translated into costs for PPO-Lagrangian;
- full-STL multi-constraint constrained RL.

Stage I therefore remains useful, but its role changes. It is the verified
**gold-STL downstream baseline** for the broader language-grounded project, not
an independently novel STL-to-Safe-RL algorithm.

The current candidate research question is:

> **Under the same online Safe RL backend and environment, does an explicit
> NL-to-STL intermediate representation provide better semantic fidelity,
> trace-level diagnosability, and downstream temporal-safety behavior than a
> direct natural-language-to-cost predictor?**

The exact controlled comparison above was not found in the targeted review.
This is a **provisional novelty conclusion**, not proof that no relevant paper
exists. It must be refreshed before any submission because this area is moving
quickly.

At the current stage, the intended contribution is therefore an **evaluation
problem and controlled benchmark**, not a claim that the project has already
invented a new translator, monitor, or Safe RL optimizer. A new algorithm
should only be proposed later if the comparison exposes a specific failure that
existing methods cannot address.

## 2. Revised Problem Definition

Let:

- \(x\) be a natural-language temporal safety requirement;
- \(\varphi^*\) be its intended gold STL interpretation;
- \(\tau\) be an environment trajectory;
- \(V_{\varphi^*}(\tau)\in\{0,1\}\) indicate whether \(\tau\) violates the
  intended requirement;
- \(r_t\) be the unchanged task reward;
- \(\mathcal A\) be one fixed online Safe RL algorithm and configuration.

The study compares two ways to construct the cost supplied to \(\mathcal A\).

### 2.1 Explicit formal-intermediate pipeline

```text
natural language x
      -> translator T
      -> STL formula phi_hat
      -> grounded signals
      -> verified monitor M
      -> temporal violation cost
      -> fixed Safe RL backend A
```

Formally,

\[
\widehat{\varphi}=T(x),
\qquad
\widehat V_{\mathrm{formal}}(x,\tau)
=M(\widehat{\varphi},g(\tau)).
\]

### 2.2 Direct learned-cost pipeline

```text
natural language x + observation/trajectory
      -> learned cost predictor C_theta
      -> predicted violation cost
      -> the same Safe RL backend A
```

Formally,

\[
\widehat V_{\mathrm{direct}}(x,\tau)
=C_\theta(x,\tau)
\]

or, for a causal stepwise implementation,
\(\widehat c_t=C_\theta(x,\tau_{0:t})\), implemented with an explicit history
window or recurrent state. A predictor that sees only \(o_t\) cannot in general
represent a non-Markovian deadline requirement.

The comparison is meaningful only when both pipelines use the same task,
training algorithm, policy architecture, cost budget, seeds, and evaluation
oracle.

### 2.3 Scope assumptions that make the problem well-defined

The first comparison assumes:

- each controlled-language requirement explicitly identifies the safety
  object, predicate direction, numerical threshold, and temporal bound;
- the benchmark exposes the physical signals needed to ground those terms;
- the supported STL fragment has causal finite-trace monitoring semantics;
- unresolved terminal obligations use one declared convention;
- both learned paths use the same train/test specification split and the same
  trajectory corpus where applicable; their supervision type, annotation
  count, model capacity, and pretrained resources are reported;
- all final labels and policies are evaluated by a human-verified gold STL
  monitor, not by either learned method itself.

These assumptions deliberately exclude vague phrases such as "stay reasonably
far away" unless a threshold-resolution mechanism is added later. They make
the first experiment finite and measurable without pretending to solve
open-world grounding.

## 3. What Is Already Covered by Prior Work

The following claims must not be presented as new.

| Claim | Closest prior evidence | Consequence |
|---|---|---|
| STL objectives need temporal history or augmented state | Venkataraman, Aksaray, and Seiler (2020) | Monitor/state augmentation alone is not novel. |
| STL can be used as a Lagrangian DRL constraint | Ikemoto and Ushio (2022) | STL plus CMDP/Lagrangian learning is not novel. |
| STL robustness can generate online RL rewards | Singh and Saha (2023) | Quantitative STL reward construction is an established line. |
| STL can condition offline Safe RL | Guo, Zhou, and Li (2024) | STL plus Safe RL is not limited to our online setting. |
| Online STL values can become observations/rewards in common RL frameworks | RLRom (2025/2026) | STL monitor integration itself is a tool contribution already demonstrated. |
| Logic monitor violations can be converted to PPO-Lagrangian costs | PPO-LTL (2026) | Monitor-to-cost-to-PPO is not new, even though it uses LTL rather than metric STL. |
| Full STL and multiple constraints can be handled in CRL | Bergamasco, Meli, and Farinelli (2026) | Full-STL CRL and multi-constraint handling cannot be claimed here. |
| Free-form natural language can directly predict Safe RL costs | Free-form NL Constraints for Safe RL (2024) | Direct NL-to-cost is an existing baseline, not our invention. |
| Text and trajectories can replace manually designed constraint costs | TTCT (2024) | Trajectory-level learned textual costs are also an existing direct baseline. |
| Text constraints can be mapped to learned spatial and temporal representations | Yang et al. (2021) | A learned intermediate representation already exists, although it is not executable formal logic. |
| Natural language can be translated to STL for navigation | NL2TL and later NL-to-STL work | NL-to-STL translation alone is not new. |
| NL-to-STL accuracy can be improved through multi-aspect or tool-grounded training | RESTL and ReasonSTL (2026) | A stronger translator alone is not the project-level novelty. |
| NL-to-STL can drive formal trajectory planning | UAV NL-to-STL plus MILP repair (2026) | The formal intermediate representation has already been used outside RL training. |

## 4. Provisional Gap

### 4.1 Search scope and decision rule

The 2026-08-10 review searched combinations of natural-language constraints,
NL-to-STL, STL monitoring, temporal-logic Safe RL, learned cost prediction,
formal intermediate representations, and online constrained RL. Sources
included arXiv, OpenReview, official proceedings pages, and the local
2021--2026 paper collection. The review also followed the closest papers in
three separate lines: language-conditioned Safe RL, NL-to-STL translation, and
STL-constrained RL.

A paper counts as an exact match only if it compares both an executable
NL-to-STL monitor path and a direct learned language-to-cost path, holds the
online Safe RL backend fixed, and evaluates both trace-label fidelity and
learned policy behavior against a shared gold temporal specification. No
reviewed paper met all of these conditions. This decision rule is deliberately
narrow enough to be auditable, but search-index and publication-lag limitations
mean that universal absence cannot be established.

### 4.2 Remaining gap

The reviewed work covers the components separately, but the review did not find
a study that performs all of the following together:

1. uses temporal safety requirements expressed as controlled natural language;
2. compares an explicit NL-to-STL path with a direct NL-to-cost path;
3. holds the online Safe RL backend and environment fixed;
4. tests minimal semantic changes such as negation, persistence, temporal scope,
   and deadlines;
5. evaluates both trace-level cost-label correctness and final learned behavior;
6. attributes failures to translation, grounding, monitoring, or policy learning.

This comparison is the current candidate contribution. Its value is not merely
that STL is interpretable. It tests whether a formal intermediate
representation changes the **error structure** of language-grounded Safe RL.

The nearest studies still leave a specific boundary. Yang et al. learn
spatial/temporal forbidden-state representations, while Lou et al. and TTCT
learn language-conditioned costs. RESTL and ReasonSTL generate STL, and the
2026 language-to-logic navigation architecture uses STL at runtime. The review
did not find one study that places an executable NL-to-STL path and a direct
learned-cost path behind the same online Safe RL algorithm and then evaluates
both against the same gold formula and trajectory oracle at formula, trace, and
policy levels.

The formal path may fail at translation or grounding, but once a correct formula
and correct signal mapping are supplied, its monitor result is mechanically
checkable. A direct learned-cost predictor may be simpler and more flexible, but
its semantic errors are not naturally separated into inspectable stages.

## 5. Why the Revised Direction Is Theoretically Feasible

### 5.1 Error decomposition

For the formal pipeline, an end-to-end label error can arise from:

- translation error: \(T(x)\not\equiv\varphi^*\);
- grounding error: \(\widehat g\neq g^*\);
- monitor implementation error;
- downstream RL optimization failure.

At the trace-label level, a union-bound decomposition is:

\[
\Pr[\widehat V_{\mathrm{formal}}\neq V_{\varphi^*}]
\leq
\Pr[T(x)\not\equiv\varphi^*]
+\Pr[\widehat g\neq g^*]
+\Pr[M\text{ is incorrect}\mid T,g\text{ correct}].
\]

For the supported Stage I rule, the last term is empirically controlled by the
online-monitor, direct-oracle, and RTAMT agreement tests. Stage II will measure
the first two terms rather than hiding them inside one end-to-end score.

This inequality does not prove that the formal path is always more accurate.
It proves that the proposed comparison and failure attribution are well-defined.

### 5.2 Gold-STL reference condition

The manually verified Stage I formula provides a semantic reference and a
downstream feasibility baseline:

```text
gold STL -> verified monitor -> Safe RL
```

If this path cannot learn useful behavior, a language translator cannot repair
the downstream control problem. If it does work, later language experiments can
measure how translation or direct cost prediction changes semantic labels and
policy behavior.

This is not a mathematical upper bound on policy return or violation rate. A
learned predictor could be more conservative than the gold monitor and
therefore report or induce fewer violations while also changing task behavior.

### 5.3 Semantically meaningful cost

For the current bounded-recovery rule, the monitor emits one event cost when a
recovery obligation misses its deadline. Therefore,

\[
\sum_t v_t
=\text{number of missed recovery obligations}.
\]

This is still an additive CMDP cost, but addition occurs **after** temporal
semantics have identified complete violation events. It is not the same as
arbitrarily adding predicate distances, robustness values, or heterogeneous
safety requirements.

For later multiple, non-exchangeable safety requirements, the project must not
silently sum them into one scalar. Separate constraints, priorities, or a
declared aggregation rule will be required.

## 6. Revised Experimental Path

### 6.1 Stage I: verified gold-STL baseline

Stage I remains focused on one bounded-recovery rule in
`SafetyPointGoal1-v0`.

Required remaining work:

1. predeclare condition-specific cost budgets, seeds, evaluation episodes, and
   task-performance tolerance;
2. verify that a nonzero STL cost occurs inside an actual PPO-Lagrangian rollout;
3. freeze matched task-only, native-cost, and gold-STL-cost configurations;
4. train the three policies under the declared protocol;
5. evaluate every policy with the same offline STL oracle.

The OmniSafe wrapper, vectorized monitor lifecycle, positive-cost routing probe,
and a minimal PPO-Lagrangian update passed on 2026-08-10. That integration gate
shows that the software path is connected; it does not yet show that the
learned policy changes its behavior.

Stage I answers only:

> Is the verified downstream gold-STL control path operational, and what
> semantic and behavioral reference does it provide for later language
> experiments?

It does not claim to invent STL-constrained RL.

### 6.2 Stage II: representation comparison

Stage II adds a controlled language set whose objects, signals, thresholds, and
time bounds are all defined in advance.

The minimum comparison is:

| Condition | Language processing | Cost source |
|---|---|---|
| Gold STL | Human-verified formula | Verified monitor |
| Explicit STL | NL-to-STL translator | Verified monitor |
| Direct cost | Language-conditioned cost predictor | Predicted labels |

The same Safe RL backend is used after cost construction.

The explicit translator and direct predictor should use the same controlled
language split and the same trajectory corpus wherever their interfaces
permit. Their label types are inherently different: the translator needs
formula supervision, whereas the direct predictor needs trace or step labels.
Annotation counts, pretrained models, and parameter counts must therefore be
reported rather than described as identical; otherwise an observed difference
could be caused by unequal resources rather than by the intermediate
representation.

Before expensive policy training, all methods are first evaluated on a fixed
trajectory corpus. Only methods that pass basic cost-label checks proceed to RL
training.

### 6.3 Semantic contrast set

The language set should contain controlled minimal pairs such as:

- `recover within K steps` versus `do not recover within K steps`;
- `reach a safe distance once` versus `remain safe for H steps`;
- `within K steps` versus `after K steps`;
- conjunction versus disjunction;
- the same requirement with meaning-preserving paraphrases.

These cases directly test the concern that a small linguistic change can alter
logical meaning while a scalar similarity-based cost predictor may not change
appropriately.

### 6.4 Evaluation levels

Evaluation is performed at three levels:

1. **Formula level:** syntax validity and semantic equivalence to gold STL.
2. **Trace level:** cost-label accuracy against the gold monitor, including
   minimal-pair flip accuracy.
3. **Policy level:** violation per trigger, goal success, return, trigger rate,
   and uncertainty across matched seeds.

This order avoids spending large training budgets before verifying that a cost
generator represents the intended requirement.

## 7. Existing Resources and New Work

### Reusable resources

- Safety-Gymnasium and `SafetyPointGoal1-v0`;
- OmniSafe PPO-Lagrangian;
- RTAMT;
- the calibrated Stage I distance signal and parameters;
- the validated online monitor and independent oracle;
- existing NL2TL/NL-to-STL datasets and methods;
- the published direct free-form NL-to-cost method as a baseline design.

### Work that the project must implement

- the Stage I matched training/evaluation harness and explicit cost-budget protocol;
- a controlled temporal-safety language set with gold STL formulas;
- semantic minimal-pair generation and validation;
- one explicit NL-to-STL implementation;
- one direct language-conditioned cost baseline;
- a common trace-level cost-label evaluator;
- end-to-end failure attribution and matched Safe RL experiments.

This is feasible without creating a new simulator or a new Safe RL algorithm.
The main new workload is the controlled comparison and evaluation harness, not
low-level robotics infrastructure.

The first research artifact should consequently be framed as a small benchmark
and evaluation protocol. It should contain language/formula pairs, semantic
minimal pairs, saved trajectories, gold monitor labels, and matched downstream
training settings. It is premature to promise a new learning method before
this benchmark identifies a reproducible weakness in either representation
path.

## 8. Claims and Limitations

The project may currently claim:

- a verified gold-STL baseline is being built on a public Safe RL benchmark;
- the proposed study isolates the effect of an explicit formal intermediate
  representation from the downstream RL algorithm;
- targeted searches found no exact controlled comparison matching the revised
  question as of 2026-08-10.

The project must not currently claim:

- the first use of STL in RL or Safe RL;
- the first monitor-state augmentation for temporal logic;
- the first logic-to-cost mechanism;
- the first NL-to-STL navigation system;
- formal safety guarantees from PPO-Lagrangian;
- proof that explicit STL will outperform direct learned costs.

The final point is the experimental hypothesis. The formal path could be more
accurate but less flexible, while the direct path could handle broader language
but make more polarity, temporal-scope, or persistence errors.

## 9. Literature Used for the Novelty Decision

The verified local PDF set is indexed in
`references/papers/related/CLOSEST_PRIOR_WORK_8.10.md`. Its filenames use the
`_8.10.pdf` suffix. The full-STL multi-constraint paper remains a documented
download pending item because OpenReview currently requires browser
verification.

- Venkataraman, Aksaray, and Seiler. [Tractable Reinforcement Learning of
  Signal Temporal Logic Objectives](https://proceedings.mlr.press/v120/venkataraman20a.html),
  L4DC 2020.
- Ikemoto and Ushio. [Deep Reinforcement Learning under Signal Temporal Logic
  Constraints Using Lagrangian Relaxation](https://arxiv.org/abs/2201.08504),
  IEEE Access 2022.
- Singh and Saha. [STL-Based Synthesis of Feedback Controllers Using
  Reinforcement Learning](https://arxiv.org/abs/2212.01022), AAAI 2023.
- Guo, Zhou, and Li. [Temporal Logic Specification-Conditioned Decision
  Transformer for Offline Safe Reinforcement Learning](https://proceedings.mlr.press/v235/guo24j.html),
  ICML 2024.
- Gómez-Ruiz, Donzé, and Dang. [RLRom: Monitoring and Training Reinforcement
  Learning Agents using Signal Temporal Logic](https://ceur-ws.org/Vol-4142/paper18.pdf).
- Zhang et al. [Integrating LTL Constraints into PPO for Safe Reinforcement
  Learning](https://arxiv.org/abs/2603.01292), 2026.
- Bergamasco, Meli, and Farinelli. [Multi-Constrained Learning Robots under
  Full Signal Temporal Logic Specifications](https://openreview.net/pdf?id=MIcZ9q09Q4),
  AAMAS 2026.
- Yang et al. [Safe Reinforcement Learning with Natural Language
  Constraints](https://arxiv.org/abs/2010.05150), ICLR 2021.
- Lou et al. [Safe Reinforcement Learning with Free-form Natural Language
  Constraints and Pre-Trained Language Models](https://arxiv.org/abs/2401.07553),
  AAMAS 2024.
- Dong et al. [From Text to Trajectory: Exploring Complex Constraint
  Representation and Decomposition in Safe Reinforcement
  Learning](https://openreview.net/forum?id=MDpIQ9hQ7H), NeurIPS 2024.
- Fang et al. [RESTL: Reinforcement Learning Guided by Multi-Aspect Rewards for
  Signal Temporal Logic
  Transformation](https://doi.org/10.1609/aaai.v40i36.40324), AAAI 2026.
- Ye et al. [ReasonSTL: Bridging Natural Language and Signal Temporal Logic via
  Tool-Augmented Process-Rewarded
  Learning](https://arxiv.org/abs/2605.06483), 2026.
- Sakano, Harrington, and Xu. [From Language to Logic: A Theoretical
  Architecture for VLM-Grounded Safe Navigation](https://arxiv.org/abs/2605.04327),
  2026.
- The local UAV NL-to-STL plus MILP repair paper,
  `references/papers/2026_UAV_NL_STL_MILP_Repair_8.10.pdf`, arXiv:2603.27583.
