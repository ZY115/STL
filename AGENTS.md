# Project Instructions

## Project objective

This repository records and will later implement Stage I of a staged study on language-grounded Signal Temporal Logic (STL) for Safe Reinforcement Learning.

The long-term project translates natural-language safety requirements into STL and uses STL monitoring results during Safe RL training.

Stage I does not contain a language model. It tests the downstream chain with one manually verified STL rule.

## Required reading

Before proposing changes or running installation commands, read:

1. `README.md`
2. `EXPERIMENT_PROGRESS_CHANGELOG.md`
3. `PROJECT_CONTEXT.md`
4. `DECISIONS.md`
5. `docs/stage1_rule_monitor_spec.md`
6. `docs/stage1_plan.md`
7. `docs/omnisafe_integration_report.md`
8. `references/REFERENCES.md`

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
  `G(e_t -> F_[0,K](d_t >= d_safe))`, where `e_t` begins one
  hysteretic warning episode.
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

Environment inspection, calibration, monitor/oracle agreement, visualization,
the OmniSafe wrapper, vectorized lifecycle tests, positive-cost routing probe,
and a minimal PPO-Lagrangian update passed their gates by 2026-08-10.

The next milestone is the pre-main-study experimental declaration. Before any
main training:

1. propose and explicitly record the required violation-rate reduction;
2. define acceptable goal-success or return degradation;
3. fix matched training seeds and evaluation episode count;
4. fix the uncertainty reporting method;
5. freeze matched task-only, native-cost, and STL-cost configurations;
6. align per-vector rollout length with complete episode horizons so an
   OmniSafe epoch reset cannot erase a pending obligation;
7. distinguish proposed values from user-confirmed decisions.

Do not run the main RL study until these choices are confirmed and recorded in
`DECISIONS.md`. Do not add the Stage II language layer during this milestone.

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

The completed rule-and-monitor milestone created the limited `src/`, `tests/`,
`configs/`, `scripts/`, and evidence surface declared by the normative
specification. Keep future wrapper/training outputs separate from calibration
and semantic-test evidence.
