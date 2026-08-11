# Prompt for a New Codex Session

Run Codex from the root of this folder and use the following prompt before requesting implementation:

```text
Read AGENTS.md, README.md, docs/END_TO_END_RESEARCH_PIPELINE.md,
DECISIONS.md, EXPERIMENT_PROGRESS_CHANGELOG.md, PROJECT_CONTEXT.md,
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
The Stage I environment-inspection, rule-and-monitor, visualization, and
OmniSafe wrapper/integration-smoke milestones are complete.
The calibrated rule is d_warn=0.45, d_safe=0.55, K=79 environment steps.

Begin only the pre-main-study experimental declaration milestone.

Read docs/omnisafe_integration_report.md and its tracked smoke summary. Preserve
the fixed rule, three cost-routing conditions, identical temporal observation,
and independent costs.

Propose explicit quantitative success criteria, matched seeds, evaluation
episodes, task-performance tolerance, and uncertainty reporting. Clearly mark
proposals versus confirmed decisions. Do not begin the main RL study or
language layer until these choices are approved and recorded in DECISIONS.md.

After this gate is complete, return to docs/END_TO_END_RESEARCH_PIPELINE.md and
continue with the next unfinished work package. Do not stop at the immediate
milestone or redesign the downstream plan from memory. If a listed blocking
decision lacks confirmation, prepare a decision proposal with candidate values,
evidence, risks, and downstream impact; do not silently choose it.
```
