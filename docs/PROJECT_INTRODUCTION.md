# Project Introduction for Group Sharing

## 中文版本

### 项目进展：Language-Grounded STL for Safe RL

我们的长期目标是：将用户给出的自然语言安全要求翻译成 STL，并通过 STL monitoring 生成安全代价，用于指导 Safe RL 训练。

由于完整链路同时包含语言理解、grounding、STL monitoring、cost design 和 Safe RL learning 等多个相互独立的不确定性，我们将研究拆分为三个阶段。当前聚焦于 **Stage I: Gold-STL Experiment**，即暂时移除语言层，使用一条人工确认正确的 STL 规则，先验证下游的“环境信号 -> STL monitor -> safety cost -> Safe RL”链路。

Stage I 选择 `SafetyPointGoal1-v0` 作为 benchmark，研究机器人进入障碍物 warning zone 后，能否在规定步数内恢复到安全距离，同时保持正常的目标到达能力。

- **Slides**：介绍原始研究问题、完整链路中的不确定性、三阶段拆分、Stage I 的 application、benchmark、STL 规则、实验比较、适用范围，以及 Stage I 成功后如何进入 Stage II。
- **Stage I Engineering Plan**：记录完成 Stage I 所需的开源资源、相关论文、系统模块、现有组件与自行开发部分，以及环境搭建后的工程步骤。

目前已经完成问题定义、Stage I 实验规划和 environment inspection。独立实验环境已安装，`SafetyPointGoal1-v0`、RTAMT、OmniSafe PPO-Lagrangian 构造和无头渲染均已验证；公开 `hazards_lidar` 可以可靠重建最近 hazard center distance。warning episode、deadline、episode 结束、binary cost 和 monitor 的规范语义也已冻结。尚未实现 monitor、wrapper 或开始 RL 训练。下一步是在 Ubuntu 工作电脑上按固定协议校准 `d_warn`、`d_safe` 和 `K`，随后一次性实现并验证 monitor 与 offline oracle；当前步骤不开始 RL 训练。

## English version

### Project Update: Language-Grounded STL for Safe RL

Our long-term goal is to translate natural-language safety requirements into Signal Temporal Logic (STL) and use STL monitoring results as safety costs during Safe RL training.

Because the complete pipeline contains several independent sources of uncertainty, including language interpretation, grounding, STL monitoring, cost design, and Safe RL optimization, we divide the research into three stages. We currently focus on **Stage I: the Gold-STL Experiment**, which removes the language layer and uses one manually verified STL rule to test the downstream chain:

```text
environment signals -> STL monitor -> safety cost -> Safe RL
```

Stage I uses `SafetyPointGoal1-v0` to examine whether an agent can recover to a safe distance within a fixed number of steps after entering a hazard warning zone, while preserving its ability to reach the goal.

- **Slides:** explain the original problem, independent uncertainties, three-stage decomposition, selected application and benchmark, Stage I rule and experiment, limitations, and the transition to Stage II.
- **Stage I Engineering Plan:** records the required repositories and papers, planned system components, reused and self-developed modules, engineering work packages, and immediate preparation steps.

The problem definition, Stage I experiment plan, and environment inspection are complete. The dedicated environment, `SafetyPointGoal1-v0`, RTAMT, OmniSafe PPO-Lagrangian construction, and off-screen rendering have been verified. Public `hazards_lidar` reconstructs the nearest hazard center distance. Warning-episode, deadline, terminal, binary-cost, and monitor semantics are now fixed. Monitor and wrapper implementation and RL training have not started. The immediate next milestone is to calibrate `d_warn`, `d_safe`, and `K` on the Ubuntu work computer, then implement and verify the monitor and offline oracle in one documented pass. RL training does not begin in this milestone.
