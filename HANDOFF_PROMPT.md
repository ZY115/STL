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
The Stage I environment-inspection milestone is complete.

Begin only the bounded-recovery rule-and-monitor milestone.

Treat docs/stage1_rule_monitor_spec.md as normative. Do not redesign its
equality, deadline, warning-episode, terminal, cost, or observation semantics.

On the Ubuntu work computer, execute its one-pass work order: add reproducible
calibration scripts, collect the declared controlled rollouts, choose d_warn,
d_safe, and K using the fixed protocol, generate stable fixtures, implement the
monitor and direct offline oracle, and verify them against the declared
semantic tests and RTAMT completed-window checks.

Deliver all artifacts listed in the completion gate. Do not begin the OmniSafe
wrapper, RL training, or the language layer during this milestone.
```
