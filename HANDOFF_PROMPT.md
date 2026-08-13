# Prompt for a New Codex Session

Run Codex from the root of this folder and use the following prompt before requesting implementation:

```text
Read AGENTS.md, README.md, docs/END_TO_END_RESEARCH_PIPELINE.md,
docs/CURRENT_EXECUTION_DIRECTIVE.md,
docs/STAGE2_CONTINUOUS_WORK_ORDER.md, DECISIONS.md,
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
The Stage I environment, monitor, oracle, wrapper, PPOLag routing, full 15-job
pilot, frozen analysis, figures and result report are complete. The calibrated
rule remains d_warn=0.45, d_safe=0.55 and K=79 environment steps.

Read D35 and docs/stage1_pilot_result_report.md. The pilot produced task/gold
missed-per-trigger rates of 25.85%/26.03% and did not meet its 30% target. Treat
this as a valid negative pilot. The monitor is a verified trajectory evaluator,
but the current sparse binary event cost is not a validated training baseline.
Do not rerun the same configuration to prove that STL cost can enter PPO.

Read D37, D38, docs/CURRENT_EXECUTION_DIRECTIVE.md and
docs/STAGE2_CONTINUOUS_WORK_ORDER.md. Follow the full work order continuously:
produce true top-down Stage I replay figures, implement the frozen 40-item O7
benchmark and review packet, implement the frozen Stage II-A baselines, run
held-out evaluation only after independent human review, diagnose the two
predeclared Gold learner costs, freeze the common online interface if its gate
passes, and run the bounded Stage II-B pilot.

Do not use paid APIs, change Gold semantics or leak held-out labels. For any
training process, verify one real update/epoch, finite metrics, GPU activity,
checkpoint output and ETA. If remaining time exceeds 20 minutes, leave the
resumable job running, record PID/log/hash/ETA/resume information, and stop
continuous polling rather than terminating the job.
```
