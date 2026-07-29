# Project Instructions

## Project objective

This repository records and will later implement Stage I of a staged study on language-grounded Signal Temporal Logic (STL) for Safe Reinforcement Learning.

The long-term project translates natural-language safety requirements into STL and uses STL monitoring results during Safe RL training.

Stage I does not contain a language model. It tests the downstream chain with one manually verified STL rule.

## Required reading

Before proposing changes or running installation commands, read:

1. `README.md`
2. `PROJECT_CONTEXT.md`
3. `DECISIONS.md`
4. `docs/stage1_plan.md`
5. `references/REFERENCES.md`

Then summarize:

- the long-term objective;
- why the project is split into stages;
- the exact Stage I research question;
- fixed decisions;
- open decisions;
- the immediate next step.

## Fixed Stage I decisions

- Application: simulated 2D point-agent navigation around static hazards.
- Benchmark: `SafetyPointGoal1-v0`.
- Task objective: preserve the benchmark's native goal-reaching reward.
- Safety rule:
  `G(d_t < d_warn -> F_[0,K](d_t >= d_safe))`.
- Initial Safe RL framework: OmniSafe.
- Initial constrained algorithm: PPO-Lagrangian.
- Reference STL monitor: RTAMT.
- Native hazard cost and STL-derived cost must remain separate.
- The first experiment uses one STL rule only.

Do not change these decisions silently. Record any proposed change in `DECISIONS.md` with its rationale and expected impact.

## Stage I scope

Do not add any of the following during Stage I unless the user explicitly changes the research scope:

- natural-language translation;
- GPT, T5, or another LLM in the experiment loop;
- free-form language grounding;
- camera-based perception;
- moving hazards;
- multi-agent settings;
- UAV or real-robot deployment;
- shielding or action intervention;
- MILP specification repair;
- counterexample-driven language repair;
- multiple STL rule families.

## Immediate task

The next milestone is environment inspection, not RL training.

The first implementation task must:

1. establish a compatible Ubuntu environment;
2. run `SafetyPointGoal1-v0`;
3. inspect the public observation and simulator interfaces;
4. determine how to define distance to the nearest hazard;
5. log native reward and native cost separately;
6. save sample trajectories;
7. document exact package and repository versions.

Do not begin monitor integration or training until the distance signal is defined and documented.

## Engineering expectations

- Prefer official repositories and documentation.
- Pin exact versions or commits after the first successful setup.
- Keep the first test minimal and diagnosable.
- Add tests for temporal boundary cases before training.
- Treat RTAMT as the reference trajectory evaluator.
- If a custom online monitor is implemented, compare it against RTAMT on saved trajectories.
- Preserve the original task reward.
- Record native cost and STL cost independently.
- Separate confirmed facts from assumptions.
- Do not claim formal safety guarantees from empirical Safe RL results.

## Documentation expectations

After each milestone:

- update `README.md` current status;
- update `DECISIONS.md` when a decision is made;
- record commands and versions in a reproducible setup document;
- record failures and unresolved questions;
- keep generated experimental outputs out of the research-document directories.

Experiment folders such as `src/`, `tests/`, `configs/`, and `results/` have intentionally not been created yet. Create them only after the environment inspection clarifies the implementation structure.
