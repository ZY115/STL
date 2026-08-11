# Project Instructions

## Project objective

This repository records the complete staged study on language-grounded Signal
Temporal Logic (STL) for Safe Reinforcement Learning and currently implements
its Stage I gold-STL control.

The long-term project translates natural-language safety requirements into STL and uses STL monitoring results during Safe RL training.

Stage I does not contain a language model. It tests the downstream chain with one manually verified STL rule.

## Required reading

Before proposing changes or running installation commands, read:

1. `README.md`
2. `docs/END_TO_END_RESEARCH_PIPELINE.md`
3. `DECISIONS.md`
4. `EXPERIMENT_PROGRESS_CHANGELOG.md`
5. `PROJECT_CONTEXT.md`
6. `docs/research_direction_novelty_feasibility.md`
7. `docs/theory_and_revised_experiment_8.10.md`
8. `docs/minimum_research_delivery_8.10.md`
9. `docs/stage1_rule_monitor_spec.md`
10. `docs/stage1_plan.md`
11. `docs/omnisafe_integration_report.md`
12. `references/REFERENCES.md`

Then summarize:

- the long-term objective;
- why the project is split into stages;
- the exact Stage I research question;
- fixed decisions;
- open decisions;
- the immediate next step;
- the subsequent work packages and their gates.

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

## Research positioning

- Do not claim novelty for STL state augmentation, STL monitoring, conversion
  of temporal violations into cost, or Lagrangian Safe RL integration.
- Stage I is the verified gold-STL downstream baseline.
- The provisional project-level contribution is a controlled benchmark that
  compares explicit `NL -> STL -> verified cost` with direct
  `NL -> predicted cost` under the same online Safe RL backend.
- Treat this novelty conclusion as time-bounded and refresh the search before
  submission.

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
and a minimal PPO-Lagrangian update passed their gates by 2026-08-10. On
2026-08-11, a real PPOLag rollout produced a nonzero deadline-event cost, the
explicit-cost-limit check passed, and the common checkpoint evaluator achieved
zero online/direct-oracle/RTAMT mismatches.

O6 is confirmed by D31 as a Stage I pilot protocol only, not as the final
main-study standard. The exact protocol and three condition overlays are frozen
under `configs/stage1_pilot/`. The three-condition 10,000-transition-per-
condition sanity gate passed on 2026-08-11 with exact cost routing and common
gold-oracle evaluation. The complete 1M runs have not started.

The next work package is the frozen Stage I pilot:

1. keep task/native/STL cost units and limits `0.0/25.0/0.1` explicit;
2. use five matched training seeds and 1M transitions per condition/seed;
3. preserve full-episode rollout alignment;
4. evaluate fixed final checkpoints deterministically on the same 100 seeds;
5. use missed obligations / triggered obligations as the primary safety metric;
6. report both relative and absolute STL-vs-task-only differences, using only
   the absolute difference when the task-only baseline is zero;
7. apply the 10-percentage-point goal-success non-inferiority margin and 10,000
   paired hierarchical bootstrap replicates;
8. inspect learning curves before any convergence claim;
9. treat 1M as a pilot budget and keep the final main-study standard open as O8.

D32 fixes the matched training backend to the verified RTX 4090 `cuda:0` device
with PyTorch 2.4.1+cu124. Launch deterministic CUDA training with
`CUBLAS_WORKSPACE_CONFIG=:4096:8`. Do not mix historical CPU sanity outputs with
CUDA pilot results.

Do not add the Stage II language layer during this milestone.
After completing the current gate, continue with the next unfinished work
package in `docs/END_TO_END_RESEARCH_PIPELINE.md`; do not reduce the handoff to
one isolated next-step instruction.

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
- update the status table in `docs/END_TO_END_RESEARCH_PIPELINE.md`;
- update `DECISIONS.md` when a decision is made;
- record commands and versions in a reproducible setup document;
- record failures and unresolved questions;
- keep generated experimental outputs out of the research-document directories.

The completed rule-and-monitor milestone created the limited `src/`, `tests/`,
`configs/`, `scripts/`, and evidence surface declared by the normative
specification. Keep future wrapper/training outputs separate from calibration
and semantic-test evidence.
