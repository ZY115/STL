# Prompt for a New Codex Session

Run Codex from the root of this folder and use the following prompt before requesting implementation:

```text
Read AGENTS.md, README.md, EXPERIMENT_PROGRESS_CHANGELOG.md,
PROJECT_CONTEXT.md, DECISIONS.md,
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
```
