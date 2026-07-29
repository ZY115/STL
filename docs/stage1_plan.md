# Stage I Engineering Plan: Gold-STL Safe RL Experiment

## 1. Purpose and Stage I Objective

The long-term research goal is to accept a natural-language task containing both a task objective and a temporal safety requirement, translate the safety requirement into Signal Temporal Logic (STL), and use the resulting specification during Safe Reinforcement Learning (Safe RL) training.

Stage I deliberately removes the language component. It asks a narrower question:

> If one correct STL safety rule is already available, can we monitor it correctly, convert its evaluation into a Safe RL cost, and reduce temporal safety failures without making the navigation task unusable?

The Stage I experiment will use one manually written, or gold, STL rule in one controlled navigation benchmark. Its purpose is to test the downstream chain:

```text
environment signal
      -> STL monitoring
      -> STL-derived safety cost
      -> Safe RL training
      -> behavioral evaluation
```

Stage I does **not** include:

- natural-language input or NL-to-STL translation;
- an LLM in the training or execution loop;
- camera-based perception;
- moving hazards or multiple agents;
- real-robot deployment;
- a formal guarantee of zero safety violations.

These restrictions are intentional. If the downstream STL-to-Safe-RL chain does not work with a known-correct rule, adding a language model would make failures harder to diagnose.

---

## 2. Fixed Experimental Setting

### 2.1 Application

The concrete application is simulated mobile-robot navigation around static hazards. A point agent must reach a target in a known two-dimensional workspace while responding to unsafe proximity to a hazard.

### 2.2 Benchmark

The first benchmark is:

```text
SafetyPointGoal1-v0
```

This environment is provided by Safety-Gymnasium. It contains a Point agent, a goal-directed reward, hazards, hazard-related observations, and a native instantaneous hazard cost. These properties allow us to compare an existing Safe RL cost with a temporal STL cost without building a simulator from scratch.

### 2.3 Task Objective

The task objective remains the benchmark's original goal-reaching objective:

> Reach the target efficiently.

The task reward should remain unchanged across the main experimental conditions.

### 2.4 Safety Signal

Let $d_t$ denote the agent's distance from the nearest hazard at environment step $t$.

The environment inspection fixed the Stage I definition:

```text
d_t = 3 * (1 - max(hazards_lidar))
```

This is the nearest agent-origin-to-hazard-center distance, capped at the public
pseudo-lidar range of 3 simulator length units. It is reconstructed from the
default public policy observation and does not require privileged simulator
state.

On 3500 collected steps, this signal agreed with the simulator center distance,
capped at 3, to floating-point precision. It is not boundary-to-boundary
clearance. The later parameter choice must satisfy
$d_{\mathrm{warn}} < d_{\mathrm{safe}} < 3$ so that lidar-range clipping cannot
change a warning or recovery judgment.

### 2.5 Single STL Rule

The Stage I rule is:

> If the agent enters a warning zone, it must return to a safe distance within $K$ environment steps.

One STL representation is:

$$
\mathbf{G}\left(d_t < d_{\mathrm{warn}}
\rightarrow
\mathbf{F}_{[0,K]}\left(d_t \ge d_{\mathrm{safe}}\right)\right),
$$

where:

- $d_{\mathrm{warn}}$ is the warning-distance threshold;
- $d_{\mathrm{safe}}$ is the recovered-safe-distance threshold;
- $K$ is the maximum permitted recovery time in environment steps;
- $d_{\mathrm{warn}} < d_{\mathrm{safe}}$ creates separation between entering the warning region and completing recovery.

The numerical values will not be chosen arbitrarily. They should be fixed after examining example trajectories and checking that recovery within $K$ steps is physically feasible.

### 2.6 Initial Training Choice

The initial constrained RL algorithm will be PPO-Lagrangian, using the implementation provided by OmniSafe.

The smallest useful comparison is:

| Condition | Task reward | Safety cost |
|---|---|---|
| Task only | Native reward | None |
| Native safety | Native reward | Safety-Gymnasium hazard cost |
| Temporal STL safety | Native reward | STL-derived cost |

A hand-coded recovery timer can later be added as a close alternative baseline. It is not required for the first environment smoke test.

---

## 3. Planned System Structure

The intended Stage I structure is:

```text
SafetyPointGoal1-v0
        |
        v
hazard-distance signal extractor
        |
        v
bounded-recovery STL monitor
        |
        v
STL safety-cost wrapper
        |
        v
OmniSafe PPO-Lagrangian
        |
        v
trajectory and evaluation logs
```

The STL formula is not passed to the RL algorithm as raw text. Instead:

1. the environment produces a trajectory and measurable signals;
2. the monitor evaluates whether the temporal requirement is being satisfied;
3. the wrapper converts the monitor output into a safety cost;
4. the Safe RL algorithm optimizes task reward subject to the cost signal.

The native hazard cost and the STL-derived cost must remain separate in the logs. Otherwise, it would be impossible to determine whether a result comes from the benchmark's original instantaneous safety definition or from the new temporal rule.

---

## 4. Required Open-Source Resources

### 4.1 Environment: Safety-Gymnasium

- GitHub repository: [PKU-Alignment/safety-gymnasium](https://github.com/PKU-Alignment/safety-gymnasium)
- Main documentation: [Safety-Gymnasium Documentation](https://safety-gymnasium.readthedocs.io/en/latest/)
- Goal environment documentation: [Safe Navigation: Goal](https://safety-gymnasium.readthedocs.io/en/latest/environments/safe_navigation/goal.html)

Safety-Gymnasium provides the simulator and the selected `SafetyPointGoal1-v0` task. Its environment API exposes reward and cost separately, which is suitable for constrained RL experiments. The Goal1 documentation also identifies the hazards, hazard-related observations, and native `cost_hazards` used by this task.

**Planned use in Stage I:**

- execute the navigation task;
- obtain the task reward;
- retain the native hazard cost as a baseline;
- extract the signal required to calculate $d_t$;
- collect trajectories for monitor testing and evaluation.

### 4.2 Safe RL Training: OmniSafe

- GitHub repository: [PKU-Alignment/omnisafe](https://github.com/PKU-Alignment/omnisafe)
- Documentation: [OmniSafe Documentation](https://omnisafe.readthedocs.io/en/latest/)
- Environment customization guide: [OmniSafe Environment Customization](https://omnisafe.readthedocs.io/en/latest/start/env.html)

OmniSafe provides implementations of standard Safe RL algorithms, including PPO-Lagrangian, and already supports Safety-Gymnasium environments. Its custom-environment and wrapper interfaces are the intended integration point for the STL-derived cost.

**Planned use in Stage I:**

- run the task-only and constrained training conditions;
- use PPO-Lagrangian for the native-cost and STL-cost conditions;
- retain standard training, evaluation, and logging infrastructure;
- avoid implementing a Safe RL optimizer from scratch.

### 4.3 STL Monitoring: RTAMT

- GitHub repository: [nickovic/rtamt](https://github.com/nickovic/rtamt)
- PyPI package: [rtamt](https://pypi.org/project/rtamt/)
- Tool paper: [RTAMT: Online Robustness Monitors from STL](https://arxiv.org/abs/2005.11827)

RTAMT supports offline and online monitoring of discrete-time STL, bounded-future temporal operators, and quantitative robustness values. These capabilities match the form of the bounded-recovery rule.

**Recommended role in Stage I:**

RTAMT should initially serve as a reference monitor, or offline oracle, for checking saved trajectories. Because a bounded-future rule cannot be fully judged until its time window has elapsed, direct per-step integration may introduce delayed outputs. For the single Stage I rule, a small stateful online monitor may therefore be simpler for training, provided that its trajectory-level judgments agree with RTAMT.

### 4.4 Version and Platform Record

The first successful setup was completed on 2026-07-29 and is recorded in
`docs/environment_setup.md`. The exact resolved environment is stored in
`environment.stage1.yml`.

The core package versions are:

| Component | Version |
|---|---:|
| Python | 3.8.20 |
| PyTorch | 2.4.1+cpu |
| Safety-Gymnasium | 1.0.0 |
| Gymnasium | 0.28.1 |
| MuJoCo | 2.3.3 |
| OmniSafe | 0.5.0 |
| RTAMT | 0.3.5 |

The tested host is Ubuntu 22.04.5 LTS. `MUJOCO_GL=egl` is used for off-screen
rendering, and the Conda environment clears the host's global ROS/Isaac
`PYTHONPATH`.

---

## 5. Most Relevant Papers

The core reading list is intentionally limited to four papers. Each paper supports one necessary part of Stage I.

### 5.1 Benchmark and Environment

**Safety-Gymnasium: A Unified Safe Reinforcement Learning Benchmark**  
J. Ji et al., NeurIPS 2023.

- [NeurIPS paper PDF](https://proceedings.neurips.cc/paper_files/paper/2023/file/3c557a3d6a48cc99444f85e924c66753-Paper-Datasets_and_Benchmarks.pdf)
- [arXiv page](https://arxiv.org/abs/2310.12567)
- [GitHub repository](https://github.com/PKU-Alignment/safety-gymnasium)

**Why it is needed:** it defines the benchmark family, environment API, safety costs, and intended Safe RL evaluation setting.

### 5.2 Safe RL Infrastructure

**OmniSafe: An Infrastructure for Accelerating Safe Reinforcement Learning Research**  
J. Ji et al., Journal of Machine Learning Research, 2024.

- [JMLR paper page](https://jmlr.org/papers/v25/23-0681.html)
- [Paper PDF](https://www.jmlr.org/papers/volume25/23-0681/23-0681.pdf)
- [GitHub repository](https://github.com/PKU-Alignment/omnisafe)

**Why it is needed:** it documents the Safe RL framework and algorithms that will be reused instead of reimplemented.

### 5.3 STL Runtime Monitoring

**RTAMT: Online Robustness Monitors from STL**  
D. Nickovic and T. Yamaguchi, 2020.

- [arXiv page](https://arxiv.org/abs/2005.11827)
- [GitHub repository](https://github.com/nickovic/rtamt)

**Why it is needed:** it provides the formal monitoring tool used to check the correctness of the bounded-recovery monitor on saved trajectories.

### 5.4 Connecting STL and RL

**Tractable Reinforcement Learning of Signal Temporal Logic Objectives**  
H. Venkataraman, D. Aksaray, and P. Seiler, L4DC 2020.

- [PMLR paper page](https://proceedings.mlr.press/v120/venkataraman20a.html)
- [Paper PDF](https://proceedings.mlr.press/v120/venkataraman20a/venkataraman20a.pdf)

**Why it is needed:** it explains why STL-based RL requires temporal history and how that history affects the learning-state representation and computational problem.

### 5.5 Stage II and Future References

The following papers remain relevant to the complete research direction but are not direct engineering dependencies for Stage I:

- [NL2TL: Transforming Natural Languages to Temporal Logics using Large Language Models](https://aclanthology.org/2023.emnlp-main.985/): relevant when Stage II adds language-to-STL translation.
- [LLM-Enabled Low-Altitude UAV Natural Language Navigation via Signal Temporal Logic Specification Translation and Repair](https://arxiv.org/abs/2603.27583): relevant to later language grounding, parameter repair, and more realistic UAV applications.
- [Safe Reinforcement Learning via Shielding](https://arxiv.org/abs/1708.08611): an alternative safety-enforcement direction that can be compared with cost-based Safe RL in later work.

---

## 6. Engineering Work Packages

The following work packages describe what must eventually be implemented. They do not yet prescribe a final code organization.

### Work Package 1: Environment Inspection

**Goal:** verify that the selected benchmark runs and exposes enough information to construct the safety signal.

**Status:** completed on 2026-07-29.

Required checks:

- reset and step through `SafetyPointGoal1-v0`;
- confirm the action and observation formats;
- locate agent and hazard information;
- determine whether exact geometry or only hazard lidar is available through the public interface;
- record native reward, native cost, termination, and truncation behavior;
- save several random or scripted trajectories.

**Output:** `docs/environment_inspection.md`, the environment lock file, and
locally saved trajectories under `results/environment_inspection/`.

### Work Package 2: Rule and Parameter Definition

**Goal:** turn the plain-language bounded-recovery rule into a fixed experimental specification.

Required decisions:

- confirm use of the fixed public-lidar $d_t$ definition;
- values of $d_{\mathrm{warn}}$ and $d_{\mathrm{safe}}$;
- value of $K$ in environment steps;
- treatment of equality at each boundary;
- treatment of an episode that ends before a pending recovery deadline;
- handling of repeated warning events while a recovery obligation is active.

**Output:** one fixed rule definition and a small set of hand-labeled success and failure trajectories.

### Work Package 3: Trajectory Monitor

**Goal:** evaluate the bounded-recovery rule consistently.

The minimal online monitor must:

- detect entry into the warning zone;
- create or update a recovery obligation;
- track the remaining recovery window;
- detect successful recovery;
- detect expiration of the recovery deadline;
- produce a clear trajectory-level satisfaction or violation result;
- optionally produce a robustness value.

Saved trajectories should also be evaluated with RTAMT. The custom monitor and RTAMT should agree except for explicitly documented numerical boundary tolerances.

**Output:** a tested monitor and an agreement report on example trajectories.

### Work Package 4: STL Safety-Cost Wrapper

**Goal:** expose the temporal-rule result through an interface that OmniSafe can use.

The wrapper should conceptually provide:

```text
observation
reward
native_cost
stl_cost
termination status
monitor diagnostics
```

Useful diagnostic fields include:

- current distance;
- warning-zone status;
- active recovery obligation;
- remaining recovery time;
- successful recovery event;
- deadline violation event;
- STL robustness, if used.

The first implementation should use one clearly defined cost mapping. Binary violation cost is the simplest starting point. Robustness-based shaping can be added only after the binary semantics are verified.

**Output:** an environment wrapper that preserves the original task while exposing an independent STL-derived cost.

### Work Package 5: Safe RL Integration

**Goal:** connect the wrapped environment to OmniSafe without changing unrelated components.

The main conditions should share:

- the same environment configuration;
- the same task reward;
- the same training budget;
- matched random seeds;
- the same network and optimizer settings where applicable.

The primary change between conditions should be the safety cost supplied to the constrained learner.

**Output:** reproducible configurations for task-only, native-cost, and STL-cost training.

### Work Package 6: Evaluation and Logging

**Goal:** determine whether the temporal rule changes behavior in the intended way.

At minimum, record:

- goal success rate;
- episode return;
- native hazard cost;
- number of warning-zone entries;
- number of successful recoveries;
- number and rate of recovery-deadline violations;
- time required to recover after a warning;
- training stability across matched seeds.

Stage I should proceed to Stage II only if:

1. the rule is feasible in the selected environment;
2. the custom monitor agrees with the reference evaluation;
3. the STL-derived cost reaches the Safe RL learner correctly;
4. the STL-cost condition reduces bounded-recovery failures;
5. the reduction is not achieved by destroying goal-reaching performance.

---

## 7. Existing Components and Required Development

| Component | Source | Stage I responsibility |
|---|---|---|
| Navigation simulator | Safety-Gymnasium | Reuse |
| `SafetyPointGoal1-v0` task | Safety-Gymnasium | Reuse and configure |
| Native task reward | Safety-Gymnasium | Reuse unchanged |
| Native hazard cost | Safety-Gymnasium | Reuse as baseline |
| PPO-Lagrangian | OmniSafe | Reuse and configure |
| Reference STL evaluation | RTAMT | Reuse for trajectory checking |
| Hazard-distance extraction | Our work | Implement |
| Rule parameterization | Our work | Define and justify |
| Stateful bounded-recovery monitor | Our work | Implement and test |
| STL-to-cost conversion | Our work | Design and implement |
| Safe RL wrapper integration | Our work | Implement |
| Temporal evaluation metrics | Our work | Implement and analyze |

The central engineering contribution of Stage I is therefore not a new simulator, STL parser, or Safe RL algorithm. It is the carefully tested connection between existing components, together with the temporal monitor, cost definition, and evaluation needed for the selected safety rule.

---

## 8. Immediate Preparation

The first preparation milestone was completed on 2026-07-29:

1. **Compatible Python environment:** installed and locked as `stl-stage1`.
2. **Core tools:** official package releases of Safety-Gymnasium, OmniSafe, and
   RTAMT installed; no mutable editable checkout is used.
3. **Environment-only smoke test:** random and scripted policies, RTAMT,
   PPO-Lagrangian construction, EGL rendering, and trajectory saving verified.

The inspection answered:

- the benchmark runs for its full 1000-step horizon;
- public `hazards_lidar` defines $d_t$ without privileged state;
- native reward and native cost are logged separately;
- no additional wrapper access is required for the primary distance signal.

The next milestone is Work Package 2. Use controlled trajectories to choose
$d_{\mathrm{warn}}$, $d_{\mathrm{safe}}$, and $K$, then freeze equality,
floating-point, repeated-trigger, and truncation semantics. Do not begin RL
training during this milestone.
