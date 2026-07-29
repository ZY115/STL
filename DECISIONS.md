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

The rule is bounded recovery:

```text
G(d_t < d_warn -> F_[0,K](d_t >= d_safe))
```

Using one rule keeps monitor semantics and behavioral interpretation inspectable.

### D7. The initial Safe RL implementation uses OmniSafe

PPO-Lagrangian is the initial constrained algorithm. The project will reuse an established optimizer rather than implement Safe RL from scratch.

### D8. RTAMT is the reference monitor

RTAMT is intended for offline or reference evaluation of saved trajectories. A small custom stateful monitor may be used online if necessary, but it must agree with the reference monitor on declared test cases.

### D9. Stage I is empirical, not a zero-violation guarantee

The STL rule defines the desired temporal condition. A cost-based Safe RL learner may still violate that condition during training or evaluation.

### D10. No experiment directories are created yet

The repository remains documentation-first until the Ubuntu environment and available signals are inspected.

## Open decisions

### O1. Definition of distance

Decide whether `d_t` is:

- center-to-center distance;
- boundary clearance;
- a quantity reconstructed from hazard lidar;
- a privileged simulator-state quantity used only in Stage I.

The final definition must be reproducible and recorded.

### O2. Rule parameters

Choose:

- `d_warn`;
- `d_safe`;
- `K`.

The values must be feasible under the environment dynamics and fixed before training.

### O3. Boundary semantics

Decide:

- whether equality counts as warning or recovery;
- how floating-point tolerance is handled;
- whether warning obligations overlap;
- what happens when a new warning occurs during recovery;
- how unfinished obligations are treated at truncation.

### O4. Online cost mapping

Possible initial mappings include:

- binary cost only when a deadline expires;
- cost while an obligation is active;
- robustness-based dense cost;
- a combination of event cost and robustness.

The first mapping should be the simplest one whose semantics can be tested clearly.

### O5. Agent observation

Decide whether monitor state, such as remaining recovery time, must be added to the policy observation to avoid hidden temporal state.

### O6. Quantitative success criterion

Before the main training study, predeclare:

- required reduction in bounded-recovery violation rate;
- acceptable loss in goal success or return;
- number of seeds;
- evaluation episode count;
- uncertainty reporting.

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
