# Prompt for a New Codex Session

Run Codex from the root of this folder and use the following prompt before requesting implementation:

```text
Read AGENTS.md, README.md, PROJECT_CONTEXT.md, DECISIONS.md,
docs/stage1_plan.md, and references/REFERENCES.md.

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
The Stage I environment-inspection milestone is complete.

Begin only the bounded-recovery rule-definition milestone.

Use the saved environment-inspection trajectories and controlled rollouts to
choose feasible values for d_warn, d_safe, and K. Freeze equality,
floating-point, repeated-trigger, and episode-truncation semantics and prepare
hand-labeled temporal boundary cases. Do not begin monitor integration, RL
training, or the language layer until these decisions are documented.
```
