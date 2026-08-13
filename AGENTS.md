# Project Instructions

## Project objective

This repository records the complete staged study on language-grounded Signal
Temporal Logic (STL) for Safe Reinforcement Learning. Its Stage I gold-STL
pilot is complete; current work diagnoses that baseline and builds the Stage II
offline benchmark foundation.

The long-term project translates natural-language safety requirements into STL and uses STL monitoring results during Safe RL training.

Stage I does not contain a language model. D37 and D38 now authorize the
spatial replay, frozen Stage II-A implementation, bounded Gold learner-cost
diagnostic and gated Stage II-B pilot defined in
`docs/STAGE2_CONTINUOUS_WORK_ORDER.md`.

## Required reading

Before proposing changes or running installation commands, read:

1. `README.md`
2. `docs/END_TO_END_RESEARCH_PIPELINE.md`
3. `docs/CURRENT_EXECUTION_DIRECTIVE.md`
4. `docs/STAGE2_CONTINUOUS_WORK_ORDER.md`
5. `docs/stage1_pilot_result_report.md`
6. `docs/stage1_code_failure_analysis_and_repair_recommendations.md`
7. `docs/stage1_o8_main_study_decision_proposal.md`
8. `docs/stage2_o7_benchmark_design_proposal.md`
9. `DECISIONS.md`
10. `EXPERIMENT_PROGRESS_CHANGELOG.md`
11. `PROJECT_CONTEXT.md`
12. `docs/research_direction_novelty_feasibility.md`
13. `docs/theory_and_revised_experiment_8.10.md`
14. `docs/minimum_research_delivery_8.10.md`
15. `docs/stage1_rule_monitor_spec.md`
16. `docs/stage1_plan.md`
17. `docs/omnisafe_integration_report.md`
18. `references/REFERENCES.md`

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
gold-oracle evaluation.

The complete authorized preparation package in
`docs/CURRENT_EXECUTION_DIRECTIVE.md` passed on 2026-08-11: the resumable
15-job runner, frozen paired hierarchical analysis, focused tests, excluded
100k exact-scale throughput preflight, and launch-readiness report are complete.
The preflight measured 335.68 transitions/second and projected approximately
13.13 hours for training plus 1,500 evaluations. This is retained as historical
pre-launch evidence; the authorized pilot later completed as recorded below.

The owner subsequently authorized the full pilot. By 2026-08-12 all 15 jobs,
15M transitions and 1,500 paired final-checkpoint evaluations completed. The
frozen analysis found task/gold missed-per-trigger rates of 25.85%/26.03% and a
-0.71% relative reduction (95% interval -24.92% to +21.88%); the 30% target was
not met. Both primary conditions had 100% goal success, so goal non-inferiority
passed. Costs above their semantic budgets and rising multipliers prevent a
convergence claim. D35 and `docs/stage1_pilot_result_report.md` are
authoritative.

The post-pilot diagnosis is complete. D37 freezes O7 and D38 authorizes the
continuous package in `docs/STAGE2_CONTINUOUS_WORK_ORDER.md`. Complete spatial
replay, dataset implementation, all unblocked train/validation work, Stage II-A
after human review, the bounded Gold cost diagnostic, online-interface freeze
and bounded Stage II-B pilot without asking after each substep.

Do not rerun the same sparse binary-cost configuration merely to prove that
cost can enter PPO. Do not let model code access held-out Gold labels before
the independent human review gate. Do not silently expand the bounded Stage
II-B pilot into a final five-seed/one-million-transition main study.

D32 fixes the matched training backend to the verified RTX 4090 `cuda:0` device
with PyTorch 2.4.1+cu124. Launch deterministic CUDA training with
`CUBLAS_WORKSPACE_CONFIG=:4096:8`. Do not mix historical CPU sanity outputs with
CUDA pilot results.

Stage II-A model training is authorized after its train/validation artifacts
pass. The complete order, inputs, outputs, models, gates and 20-minute
monitoring rule are authoritative in `docs/STAGE2_CONTINUOUS_WORK_ORDER.md`.
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
