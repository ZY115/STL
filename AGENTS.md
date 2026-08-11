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
3. `docs/CURRENT_EXECUTION_DIRECTIVE.md`
4. `DECISIONS.md`
5. `EXPERIMENT_PROGRESS_CHANGELOG.md`
6. `PROJECT_CONTEXT.md`
7. `docs/research_direction_novelty_feasibility.md`
8. `docs/theory_and_revised_experiment_8.10.md`
9. `docs/minimum_research_delivery_8.10.md`
10. `docs/stage1_rule_monitor_spec.md`
11. `docs/stage1_plan.md`
12. `docs/omnisafe_integration_report.md`
13. `references/REFERENCES.md`

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

The complete authorized preparation package in
`docs/CURRENT_EXECUTION_DIRECTIVE.md` passed on 2026-08-11: the resumable
15-job runner, frozen paired hierarchical analysis, focused tests, excluded
100k exact-scale throughput preflight, and launch-readiness report are complete.
The preflight measured 335.68 transitions/second and projected approximately
13.13 hours for training plus 1,500 evaluations. No frozen pilot job started.

The immediate task is now the one explicit compute-authorization gate for the
15M-transition full pilot. Do not launch it before the owner reviews
`docs/stage1_pilot_launch_readiness.md` and explicitly approves. After launch
approval, training, final-checkpoint evaluation, analysis, WP1 reporting, O8
proposal, and the non-compute WP2/O7 proposal form one continuous package.

D32 fixes the matched training backend to the verified RTX 4090 `cuda:0` device
with PyTorch 2.4.1+cu124. Launch deterministic CUDA training with
`CUBLAS_WORKSPACE_CONFIG=:4096:8`. Do not mix historical CPU sanity outputs with
CUDA pilot results.

Do not add the Stage II language model during this milestone, but the benchmark
schema and O7 decision proposal may begin after the WP1 pilot report as the
long-term pipeline directs.
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
