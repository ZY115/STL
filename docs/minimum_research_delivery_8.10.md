# 8.10 方向调整后的最低可汇报交付版本

> 本文只定义近期可向老师汇报的最低 artifact，不替代长期研究路线。完成本文要求后，
> 应继续按照 `docs/END_TO_END_RESEARCH_PIPELINE.md` 的 WP1--WP7 推进。

## 1. 这次交付要回答什么

老师质疑的重点不是 Safety-Gymnasium 能否启动，而是：使用已有 benchmark 之后，
项目到底在研究什么。

当前回答是：

> 在相同环境、相同轨迹和相同 Safe RL 后端下，比较两种把自然语言安全要求变成
> 训练 cost 的方式：显式 `NL -> STL -> verified monitor cost`，以及直接
> `NL -> learned cost predictor`。研究显式形式化中间表示是否带来更准确的时序
> 语义、更容易定位的错误，以及不同的最终策略行为。

因此，SafetyPointGoal1-v0 只是固定的受控试验台，不是项目贡献。项目要隔离的
科学变量是“安全要求如何表示、如何变成 cost”。

## 2. 当前已经完成的基础

- 环境、距离信号和一条 bounded-recovery STL 规则已经固定；
- online monitor、independent oracle 和 RTAMT agreement 已通过；
- STL violation 可以通过 wrapper 路由到 OmniSafe；
- 三个 cost 条件共享同一 observation contract；
- 一次 positive-cost scripted probe 和一次最小 PPO-Lagrangian update 已通过。

这些结果证明实验基础设施已经连通，但尚未证明 STL 改变了学习行为，也尚未回答
新的 representation-comparison 问题。

## 3. 最低可交付版本必须包含什么

### A. 一页清楚的问题与假设

必须明确写出：

- 被比较的两条路径；
- 固定不变的环境、任务、轨迹、训练后端和 gold oracle；
- STL 可能的优势：精确表达 negation、deadline、persistence 和 temporal scope，
  并可把错误分成 translation、grounding、monitoring 和 RL optimization；
- direct cost 可能的优势：减少人工形式化，更灵活，可能更适合开放语言；
- 可证伪条件：如果 direct cost 在语义标签、错误诊断和策略行为上不差于 STL path，
  则当前“显式 STL 有实际价值”的假设不成立。

### B. 一个小型受控语义测试集

不需要立刻构建大规模 benchmark。最低版本应有约 30--50 条受控自然语言安全要求，
并为每条提供：

- human-verified gold STL；
- 已定义的 signal 与数值参数；
- train/test specification split；
- semantic minimal pairs，例如加入 `not`、修改 deadline、把“最终恢复”改成
  “持续保持”，或交换 conjunction/disjunction；
- 一组保存的轨迹，以及 gold monitor 给出的 violation event 和 cost label。

只有当前单条规则无法比较语言表示方法，也无法回答老师提出的研究价值问题。

### C. 两条可以在同一数据上运行的 cost 路径

最低版本不要求发明新模型，但必须能够运行：

1. `NL -> STL -> verified monitor cost`；
2. `NL + trajectory/history -> direct predicted cost`；
3. human-verified `gold STL -> oracle cost` 作为共同参考。

两条路径的 supervision、预训练资源、模型容量和人工标注量必须公开，不能只写
“使用相同模型”来掩盖资源不公平。

### D. 先离线、后在线的一组初步结果

先在同一批保存轨迹上比较：

- formula validity / equivalence；
- cost-label false positive、false negative 和 event timing error；
- semantic minimal-pair consistency；
- 每类错误可以定位到哪一步。

只有离线结果表明两条路径确实存在可解释差异后，才进行一个小型在线 RL pilot。
该 pilot 至少要做到：

- 显式设置每个条件的 `lagrange_cfgs.cost_limit`；
- PPO-Lagrangian rollout 中真实出现非零 STL cost；
- 使用相同后端和 matched seeds；
- 最终用 gold STL oracle 统一评估 task success 与 temporal violation；
- 报告一个失败案例，而不仅是最好结果。

## 4. 什么算“可以给老师汇报”

最低交付包应包含：

1. 6--8 页方向调整 slides 或一页 problem statement；
2. 受控 NL/gold-STL 数据文件及 split；
3. 保存轨迹和 gold cost labels；
4. 两条 cost 路径的可运行入口；
5. 一张离线比较表和 3--5 个具体错误案例；
6. 一个小型 RL pilot 的表格或曲线；
7. 可复现命令、版本和限制说明。

这不是论文完整实验。它的标准是：老师可以看到明确的问题、可公平比较的变量、
第一批证据和可能推翻该想法的结果，而不是只看到 benchmark 被跑通。

## 5. 工作电脑的最短执行顺序

1. 完成 Stage I 的 cost-budget 声明、positive-cost on-policy sanity 和统一 evaluation
   runner；不要直接开始大规模多 seed 训练。
2. 建立 30--50 条受控 NL/gold-STL 样本和对应 semantic minimal pairs。
3. 生成固定轨迹集和 gold oracle labels。
4. 接入一个 NL-to-STL baseline 和一个 history-aware direct-cost baseline。
5. 完成 formula/trace-level 离线比较，先找出真实语义差异。
6. 选择最有代表性的规则做一个小型 matched Safe RL pilot。
7. 把问题、方法、公平性、初步结果、失败案例和限制整理成老师可独立阅读的材料。

## 6. 这次交付暂时不要求什么

- 不要求新 simulator 或新 Safe RL optimizer；
- 不要求开放式模糊自然语言；
- 不要求大规模多 seed 主实验；
- 不要求 GPU 才能开始；
- 不要求动态障碍、视觉输入或真实机器人；
- 不要求提前宣称 STL path 一定优于 direct cost。

最低版本的价值在于把“为什么要用 STL”变成一个可以被数据支持或否定的问题。
