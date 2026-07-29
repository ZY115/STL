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
Begin only the Stage I environment-inspection milestone.

Check the current official requirements of Safety-Gymnasium, OmniSafe,
RTAMT, MuJoCo, and Ubuntu. Propose a compatible, reproducible environment
before installing anything.

The first technical objective is to run SafetyPointGoal1-v0 and determine
which public signal can define distance to the nearest hazard. Do not begin
RL training or add the language layer.
```
