# Project Introduction for Group Sharing

## 中文版本

### 项目进展：Language-Grounded STL for Safe RL

我们的长期目标是：将用户给出的自然语言安全要求翻译成 STL，并通过 STL monitoring 生成安全代价，用于指导 Safe RL 训练。

最新文献核查表明，“STL monitor -> cost -> Lagrangian Safe RL”本身已有直接先例。因此 Stage I 的作用是建立经过验证的 gold-STL 下游基线，而不是声称提出新的 STL-Safe-RL 算法。当前暂定的项目级方向，是在相同环境和 Safe RL 后端下，系统比较“NL -> STL -> verified cost”与“NL -> predicted cost”的语义正确性、轨迹级可诊断性和最终策略表现。现阶段预期产出首先是一个受控比较 benchmark 和评估协议；是否需要提出新算法，要由比较暴露出的具体失败决定。

完整的独立执行路线见 `docs/END_TO_END_RESEARCH_PIPELINE.md`。该文档从当前
gold-STL control 一直定义到 benchmark 构建、已有方法复现、离线语义比较、在线
Safe RL 对比、贡献类型判断和后续环境扩展，而不只记录一个近期步骤。

由于完整链路同时包含语言理解、grounding、STL monitoring、cost design 和 Safe RL learning 等多个相互独立的不确定性，我们将研究拆分为三个阶段。当前聚焦于 **Stage I: Gold-STL Experiment**，即暂时移除语言层，使用一条人工确认正确的 STL 规则，先验证下游的“环境信号 -> STL monitor -> safety cost -> Safe RL”链路。

Stage I 选择 `SafetyPointGoal1-v0` 作为 benchmark，研究机器人进入障碍物 warning zone 后，能否在规定步数内恢复到安全距离，同时保持正常的目标到达能力。

- **Slides**：介绍原始研究问题、完整链路中的不确定性、三阶段拆分、Stage I 的 application、benchmark、STL 规则、实验比较、适用范围，以及 Stage I 成功后如何进入 Stage II。
- **Stage I Engineering Plan**：记录完成 Stage I 所需的开源资源、相关论文、系统模块、现有组件与自行开发部分，以及环境搭建后的工程步骤。

目前已经完成问题定义、环境/规则/monitor/wrapper、CUDA、三条件 sanity，以及 5 seeds × 3 conditions × 1M transitions 的完整 pilot、1,500 条 paired evaluation 和 10,000 次 hierarchical bootstrap。task-only/gold-STL 的 missed-per-trigger 为 25.85%/26.03%，relative reduction 为 -0.71%（95% CI -24.92% 到 +21.88%），没有达到 30% pilot target；两者 goal success 均为 100%，goal non-inferiority 通过。gold-STL cost 仍高于预算且 multiplier 上升，因此不能声称收敛。当前等待 O8 决定 final main-study standard；O7 Stage II benchmark proposal 已准备但未确认。

## English version

### Project Update: Language-Grounded STL for Safe RL

Our long-term goal is to translate natural-language safety requirements into Signal Temporal Logic (STL) and use STL monitoring results as safety costs during Safe RL training.

The updated literature review shows that the chain `STL monitor -> cost -> Lagrangian Safe RL` already has direct precedents. Stage I is therefore a verified gold-STL downstream baseline, not a claim of a new STL-Safe-RL algorithm. The provisional project-level direction is to compare `NL -> STL -> verified cost` with `NL -> predicted cost` under the same environment and Safe RL backend, measuring semantic correctness, trace-level diagnosability, and learned policy behavior. The first intended contribution is a controlled comparison benchmark and evaluation protocol; a new algorithm should only follow if this comparison reveals a reproducible gap.

The authoritative independent execution map is
`docs/END_TO_END_RESEARCH_PIPELINE.md`. It continues beyond the immediate
gold-STL gate through benchmark construction, prior-method reproduction,
offline semantic comparison, matched online Safe RL evaluation, contribution
selection, and broader validation.

Because the complete pipeline contains several independent sources of uncertainty, including language interpretation, grounding, STL monitoring, cost design, and Safe RL optimization, we divide the research into three stages. We currently focus on **Stage I: the Gold-STL Experiment**, which removes the language layer and uses one manually verified STL rule to test the downstream chain:

```text
environment signals -> STL monitor -> safety cost -> Safe RL
```

Stage I uses `SafetyPointGoal1-v0` to examine whether an agent can recover to a safe distance within a fixed number of steps after entering a hazard warning zone, while preserving its ability to reach the goal.

- **Slides:** explain the original problem, independent uncertainties, three-stage decomposition, selected application and benchmark, Stage I rule and experiment, limitations, and the transition to Stage II.
- **Stage I Engineering Plan:** records the required repositories and papers, planned system components, reused and self-developed modules, engineering work packages, and immediate preparation steps.

The environment/rule/monitor/wrapper/CUDA gates and the complete five-seed,
three-condition, 1M-transition pilot are finished, including 1,500 paired
evaluations and 10,000 hierarchical bootstrap replicates. Task-only/gold-STL
missed-per-trigger was 25.85%/26.03%; relative reduction was -0.71% (95% CI
-24.92% to +21.88%), so the 30% pilot target was not met. Both had 100% goal
success and passed goal non-inferiority. Gold-STL cost remained over budget and
its multiplier rose, so convergence is not claimed. O8 now controls any final
main-study compute, while the O7 Stage II benchmark proposal awaits approval.
