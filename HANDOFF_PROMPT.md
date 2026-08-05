# Prompt for a New Codex Session

Run Codex from the root of this folder and use the following prompt before requesting implementation:

```text
Read AGENTS.md, README.md, PROJECT_CONTEXT.md, DECISIONS.md,
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
The Stage I environment-inspection and rule-and-monitor milestones are complete.
The calibrated rule is d_warn=0.45, d_safe=0.55, K=79 environment steps.

Begin only the OmniSafe wrapper and small integration-smoke milestone.

Treat docs/stage1_rule_monitor_spec.md and configs/stage1_rule.yaml as
normative. Preserve native reward, native cost, and STL cost separately. Append
the same active/overdue/remaining temporal observation state to task-only,
native-cost, and STL-cost conditions. Keep independent monitor state per
vectorized environment and test reset, step, termination, truncation, and logs.

Verify that PPO-Lagrangian can consume the selected cost in a minimal smoke
integration. Do not begin the main RL study or language layer. Before main
training, first predeclare the quantitative success criterion, seeds,
evaluation episodes, task-performance tolerance, and uncertainty reporting.
```
