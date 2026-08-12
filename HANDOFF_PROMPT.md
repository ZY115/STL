# Prompt for a New Codex Session

Run Codex from the root of this folder and use the following prompt before requesting implementation:

```text
Read AGENTS.md, README.md, docs/END_TO_END_RESEARCH_PIPELINE.md,
docs/CURRENT_EXECUTION_DIRECTIVE.md, DECISIONS.md,
EXPERIMENT_PROGRESS_CHANGELOG.md, PROJECT_CONTEXT.md,
docs/research_direction_novelty_feasibility.md,
docs/theory_and_revised_experiment_8.10.md,
docs/minimum_research_delivery_8.10.md,
docs/stage1_rule_monitor_spec.md, docs/stage1_plan.md, and
references/REFERENCES.md.

First summarize:
1. the long-term research objective;
2. how the complete natural-language-to-Safe-RL pipeline works;
3. why the project was divided into three stages;
4. the exact Stage I research question;
5. fixed decisions and open decisions;
6. what has and has not been implemented;
7. the immediate next milestone.
8. why Stage I is a gold-STL baseline rather than the project novelty;
9. the provisional Stage II comparison between explicit STL and direct cost.
10. every later work package, its required input/output, gate, and predefined
    failure branch;
11. which controls are not language-method baselines and whether a novel method
    currently exists.

Do not install packages, create experiment directories, or modify files
until this summary is complete and consistent with the documents.
```

After confirming the summary, use:

```text
The Stage I environment-inspection, rule-and-monitor, visualization,
OmniSafe wrapper/integration-smoke, on-policy positive-cost sanity, common
checkpoint evaluator, pilot-protocol freeze, three-condition small-budget
sanity, resumable runner, excluded 100k preflight, full 15-job pilot, frozen
analysis, figures and WP1 report are complete.
The calibrated rule is d_warn=0.45, d_safe=0.55, K=79 environment steps.

Read docs/stage1_pilot_result_report.md, D35 and the compact outputs under
results/stage1_pilot/analysis/. The completed pilot produced task/gold
missed-per-trigger rates of 25.85%/26.03% and -0.71% relative reduction (95%
interval -24.92% to +21.88%), so the 30% target was not met. Both primary
conditions had 100% goal success. Constraint costs remained over budget and
multipliers rose, so do not claim convergence or formal safety.

Read docs/stage1_code_failure_analysis_and_repair_recommendations.md. It records
the metric/learner-objective mismatch, sparse delayed event credit, budget and
optimizer timing, terminal cost-bootstrap risk, and OmniSafe effective-runtime
differences. Treat P0 as proposed non-GPU engineering work and P1/P2 as
unapproved candidates; do not silently change D31 or the gold evaluator.

Read docs/omnisafe_integration_report.md and its tracked smoke summary. Preserve
the fixed rule, three cost-routing conditions, identical temporal observation,
and independent costs.

Read D31, configs/stage1_pilot/, and docs/stage1_pilot_sanity_report.md. D31 is
approved only for the pilot, not as the final main-study standard. Preserve the
primary missed-obligations-per-trigger metric, absolute-difference reporting,
zero-baseline rule, 10-point goal margin, five matched seeds, 100 paired
evaluation episodes, 10,000 hierarchical bootstrap replicates, fixed final
checkpoints, and the different cost units. Treat 1M transitions as a pilot
budget and inspect learning curves before any convergence claim.

The 10k-per-condition sanity, 100k exact-scale preflight and full 1M×3×5 pilot
all passed their engineering gates. Keep O8 open for the final main-study
standard; the completed negative pilot is evidence, not an automatically
selected final configuration.

D32 enabled and validated RTX 4090 CUDA training with torch 2.4.1+cu124. The
frozen backend is cuda:0 for every condition, and deterministic launchers must
set CUBLAS_WORKSPACE_CONFIG=:4096:8. Read docs/cuda_enablement_report.md and do
not mix historical CPU sanity artifacts with the CUDA pilot.

The work is currently stopped at O8 for any additional GPU compute. Read
docs/stage1_o8_main_study_decision_proposal.md and do not launch another run
until the owner chooses close, longer same-method, or bounded diagnostic. Read
docs/stage2_o7_benchmark_design_proposal.md; O7 formula families, exact dataset
composition, split, baselines and offline gates remain proposals. Do not add a
Stage II language model before O7 is confirmed. Continue every other unblocked
non-compute item from docs/END_TO_END_RESEARCH_PIPELINE.md.
```
