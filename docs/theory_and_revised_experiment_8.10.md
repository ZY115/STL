# NL-to-STL 与直接 NL-to-Cost 比较：理论分析与修订实验路线（8.10）

- **记录日期：** 2026-08-10
- **版本标记：** 8.10
- **状态：** 当前研究路线说明
- **对应研究问题：** 在相同环境、数据划分和 online Safe RL 后端下，系统比较
  `NL -> STL -> verified monitor cost` 与 `NL -> learned cost predictor`，并同时
  分析公式语义、轨迹 cost label 和最终策略行为。

## 1. 结论

这条路线可以包含理论分析，但当前核心问题仍然是一个**以受控实验为主体的研究
问题**。

理论分析可以回答：

- 为什么带 deadline 的时序安全 cost 必须依赖轨迹历史；
- 显式 STL 路线在什么条件下可以产生确定且正确的 cost；
- 翻译、grounding、monitor 和 cost prediction 的错误如何区分；
- cost 漏报如何传递为最终策略的真实安全违反；
- 为什么固定轨迹上的高准确率不能直接推出训练策略是安全的。

理论分析不能预先证明：

- `NL -> STL` 一定比 `NL -> learned cost` 更准确；
- cost label 更准确一定会产生更安全的 RL policy；
- 显式 STL 一定带来更高 task reward 或更低 violation rate；
- PPO-Lagrangian 在训练中一定满足零违反或形式化安全保证。

因此，当前最合理的论文定位是：

> 以一个受控的 representation comparison 和 benchmark 为主体，用理论命题说明
> 比较为什么成立、两条路线各自需要什么信息，以及 cost 错误如何影响最终安全性。

这不是纯理论论文，也不应仅做没有分析框架的经验对比。

## 2. 两条待比较路线

令：

- \(x\) 为自然语言时序安全要求；
- \(\varphi^*\) 为人工确认的 gold STL；
- \(\tau_{0:t}\) 为截至时刻 \(t\) 的轨迹前缀；
- \(g^*(\tau_{0:t})\) 为正确 grounding 后的距离等 STL 信号；
- \(c_t^*\) 为 gold STL monitor 产生的正确 cost；
- \(\mathcal A\) 为固定的 online Safe RL backend。

### 2.1 显式形式化中间表示路线

```text
natural-language requirement x
        -> NL-to-STL translator T
        -> predicted formula phi_hat
        -> grounded trajectory signals
        -> verified monitor M
        -> temporal cost c_hat_formal
        -> fixed Safe RL backend A
```

形式化表示为：

\[
\widehat\varphi=T(x),
\qquad
\widehat c_t^{\mathrm{formal}}
=M(\widehat\varphi,\widehat g(\tau_{0:t})).
\]

### 2.2 直接学习 cost 路线

```text
natural-language requirement x + trajectory history
        -> learned cost predictor C_theta
        -> predicted temporal cost c_hat_direct
        -> the same Safe RL backend A
```

形式化表示为：

\[
\widehat c_t^{\mathrm{direct}}
=C_\theta(x,\tau_{0:t}).
\]

这里必须写成 \(\tau_{0:t}\)，而不能默认只使用当前观测 \(o_t\)。对于带 deadline、
顺序或持续时间的规则，当前状态通常不足以确定正确 cost。

## 3. 可进行的理论分析

### 3.1 命题一：只看当前观测无法一般性表示时序 cost

考虑当前 Stage I 的 bounded-recovery requirement：

> 当 agent 第一次进入 warning zone 后，必须在规定步数内恢复到 safe distance。

在某个时刻，两条轨迹可能具有相同的当前距离：

\[
d_t=0.50.
\]

但它们的历史不同：

- 轨迹 A 从未进入过 (d<0.45)，当前不存在恢复义务；
- 轨迹 B 在 deadline 之前进入过 (d<0.45)，到 deadline 时仍未达到
  (d\geq0.55)，因此已经违反规则。

虽然当前观测相同，正确 cost 分别为：

\[
c_t^A=0,
\qquad
c_t^B=1.
\]

任何只使用当前观测的确定性 predictor

\[
C_\theta(x,o_t)
\]

都会对相同输入给出相同输出，因此不可能同时正确判断这两条轨迹。直接 cost
baseline 必须具有足够的 history window、RNN hidden state 或其他因果记忆。

这个命题说明实验输入应如何设计，但不能作为项目的新颖性主张。STL-guided RL
中的历史压缩和 learned non-Markovian safety constraints 已经研究过这一问题。

### 3.2 命题二：显式 STL 路线具有条件正确性

如果同时满足：

\[
T(x)\equiv\varphi^*,
\qquad
\widehat g=g^*,
\qquad
M\text{ 对支持的 STL fragment 正确},
\]

那么对于支持范围内的所有轨迹：

\[
\widehat c_t^{\mathrm{formal}}=c_t^*.
\]

它的含义不是“NL-to-STL 系统天然正确”，而是：一旦翻译和 grounding 正确，
verified monitor 的输出是机械计算结果，不再是学习模型对违反情况的猜测。

显式路线的错误可以分解为：

1. translation error：
   (T(x)\not\equiv\varphi^*)；
2. grounding error：
   \(\widehat g\neq g^*\)；
3. monitor implementation error；
4. downstream Safe RL optimization failure。

在轨迹标签层面，可以写成：

\[
\Pr[\widehat V_{\mathrm{formal}}\neq V_{\varphi^*}]
\leq
\Pr[T(x)\not\equiv\varphi^*]
+\Pr[\widehat g\neq g^*]
+\Pr[M\text{ incorrect}\mid T,g\text{ correct}].
\]

当前 Stage I 的 online monitor、direct offline oracle 和 RTAMT agreement tests
控制的是最后一项，而不是前两项。Stage II 才加入 translation 和 language
grounding。

直接 predictor 的语言理解、历史理解和违反判断共同存在于
(C_\theta(x,\tau_{0:t})) 中。它可能更灵活，但错误通常不能自然分解为一条错误
公式或一个错误 signal mapping。

### 3.3 命题三：cost 漏报会直接扩大真实安全违反

设 episode horizon 为 \(H\)，gold cost 和预测 cost 都在 \([0,1]\) 内。定义：

\[
J^*(\pi)
=\mathbb E_\pi\left[\sum_{t=0}^{H-1}c_t^*\right],
\qquad
\widehat J(\pi)
=\mathbb E_\pi\left[\sum_{t=0}^{H-1}\widehat c_t\right].
\]

其中 (J^*(\pi)) 是 gold monitor 判断的真实期望安全代价，
\(\widehat J(\pi)\) 是训练时 cost generator 提供的期望代价。

定义策略 \(\pi\) 的平均 cost 漏报误差：

\[
\epsilon_\pi^-
=\frac{1}{H}
\mathbb E_\pi\left[
\sum_{t=0}^{H-1}(c_t^*-\widehat c_t)_+
\right].
\]

则有：

\[
J^*(\pi)
\leq
\widehat J(\pi)+H\epsilon_\pi^-.
\]

如果 Safe RL 只保证预测 cost 不超过预算 \(B\)：

\[
\widehat J(\pi)\leq B,
\]

那么真实安全代价只能保证：

\[
J^*(\pi)\leq B+H\epsilon_\pi^-.
\]

通俗地说：Safe RL 只能约束它实际收到的 cost。cost generator 没有报告的违反，
不会被 PPO-Lagrangian 自动恢复为正确安全信号。

false negative 主要影响真实安全性；false positive 会使 agent 过度保守，通常表现
为 goal success 或 task return 下降。两类错误不能只合并成一个 accuracy 数值。

### 3.4 固定轨迹准确率不能推出训练策略安全

固定 trajectory corpus 只能估计 cost generator 在该数据分布下的错误。RL policy
经过预测 cost 训练后，会改变自己访问的状态和轨迹分布。它可能主动进入 corpus
未覆盖、但 predictor 判断错误的区域。

因此：

- 固定 corpus 是训练前的必要诊断；
- 它不是最终安全结论；
- policy-level evaluation 必须重新使用 gold STL oracle；
- 报告必须区分 offline trace error 和 on-policy true violation。

只有在额外假设 predictor 在所有可能 policy occupancy distribution 上具有统一误差
界时，才能把固定数据集误差直接转化为 policy safety bound。当前神经网络和连续
控制环境不适合轻率采用这一强假设。

## 4. 为什么整体研究仍然必须依靠实验

即使方法 A 的 cost labels 比方法 B 更接近 gold labels，也不能直接推出方法 A
训练出的 policy 更安全。最终行为还受以下因素影响：

- cost 是否稀疏或延迟；
- cost 错误发生在普通状态还是关键状态；
- false positive 是否导致 agent 放弃任务；
- policy 是否具有足够的 temporal memory；
- PPO-Lagrangian 的优化、cost budget 和 multiplier dynamics；
- exploration 过程中是否访问了新的错误区域；
- safety improvement 是否以不可接受的 task-performance loss 为代价。

因此，理论分析用于规定比较边界和解释实验结果，而 representation 的实际优劣
必须通过 formula、trace 和 policy 三层实验回答。

## 5. 当前 Stage I 不应被推翻

Stage I 仍然保留当前环境、规则和参数：

```text
Environment: SafetyPointGoal1-v0
d_warn:     0.45
d_safe:     0.55
K:          79 environment steps
```

其流程仍然是：

```text
gold STL
    -> verified monitor
    -> STL cost
    -> OmniSafe wrapper
    -> fixed Safe RL backend
    -> gold-oracle policy evaluation
```

计划中的三个 Stage I conditions 也继续保留：

| Condition | Learner receives | 作用 |
|---|---|---|
| Task-only | zero safety cost | 判断任务本身能否学习，并观察无安全约束行为 |
| Native safety | Safety-Gymnasium native hazard cost | 提供即时几何安全 cost baseline |
| Gold-STL safety | verified bounded-recovery event cost | 检查时序 cost 是否能进入 Safe RL 并改变行为 |

Stage I 只回答：

> 当安全规则完全正确、语言翻译错误被移除时，gold-STL downstream path 是否能够
> 正确运行，并为后续语言比较提供什么语义和行为参考？

Stage I 不再承担以下主张：

- 首次把 STL 接入 RL；
- 首次把 logic violation 转换为 Lagrangian cost；
- 证明 STL cost 普遍优于所有 native costs；
- 证明整个 NL-to-STL-to-Safe-RL 系统已经成立。

## 6. 修订后的完整实验路线

### 6.1 Part A：完成 gold-STL downstream baseline

OmniSafe wrapper、vectorized monitor lifecycle、positive-cost routing probe 和一次
最小 PPO-Lagrangian update 已于 2026-08-10 通过。继续完成当前最近里程碑：

1. 分别定义 native cost 与 STL event cost 的预算含义和 `cost_limit`；
2. 在真实 PPO-Lagrangian rollout 内验证至少一次非零 STL cost；
3. 预声明 seeds、evaluation episodes 和 task-performance tolerance；
4. 冻结 task-only、native-cost 和 gold-STL-cost matched conditions；
5. 使用同一 offline gold STL oracle 评价所有 policies。

这部分是后续比较的控制实验，不是项目最终贡献。

### 6.2 Part B：建立受控语言与轨迹 benchmark

Stage II 不能只包含一句语言和一个固定公式，因为这只能测试一个接口是否运行，
不能比较两种 representation 的语义能力。需要构造一个小型、受控的数据集：

```text
controlled natural-language requirement
        + human-verified gold STL
        + grounded signal definition
        + saved trajectory or trajectory prefix
        + gold monitor cost labels
```

第一版可以从当前 bounded-recovery 规则族开始，变化：

- meaning-preserving paraphrases；
- warning distance；
- safe distance；
- deadline (K)；
- 参数组合的 train/test split。

随后再加入少量真正改变语义的结构：

- `within K steps` 与 `after K steps`；
- `eventually safe` 与 `remain safe for H steps`；
- conjunction 与 disjunction；
- negation 或 polarity change。

不合理或会鼓励危险行为的否定样例可以只用于 offline semantic test，不必进入 RL
training。

轨迹 corpus 必须覆盖：

- 未触发 warning；
- 触发后及时恢复；
- 在 inclusive deadline 恢复；
- deadline violation；
- terminal unresolved；
- 距离阈值边界；
- 两条当前观测相同但 monitor history 不同的轨迹；
- task-only、native-safe 和 gold-STL policies 可能访问的不同区域。

### 6.3 Part C：比较 cost generator，而不是立即训练 RL

最小比较条件为：

| Condition | Language processing | Cost source |
|---|---|---|
| Gold reference | Human-verified gold STL | Verified monitor |
| Explicit formal | NL-to-STL translator | Verified monitor on predicted STL |
| Direct learned cost | Language plus causal trajectory history | Learned cost labels |

直接 learned-cost baseline 至少应包含一个 history-aware 强基线，例如 recurrent
model 或 trajectory Transformer。只使用当前 observation 的 direct model 可以作为
弱基线展示结构性限制，但不能作为主要对手，否则比较结果在开始前就已由输入不足
决定。

两条学习路线使用相同的：

- controlled-language specification split；
- trajectory corpus；
- environment signals；
- evaluation oracle；
- downstream Safe RL algorithm and configuration。

但两条路线的 supervision 类型天然不同：NL-to-STL 需要 formula supervision，
direct predictor 需要 trajectory/step cost labels。因此不能简单声称训练资源完全相同。
必须报告 annotation count、model capacity、pretrained model、training compute 和可见
数据，避免把资源差异误认为 representation 差异。

### 6.4 Part D：按三层顺序评价

#### 第一层：formula level

仅对 explicit NL-to-STL path 评价：

- syntax validity；
- operator、predicate、threshold 和 deadline 是否正确；
- predicted STL 是否与 gold STL 语义等价；
- minimal semantic pair 是否产生应有的公式变化。

direct predictor 没有公式输出，因此 formula-level metric 是显式路线的诊断指标，
不是两条路线共有的最终分数。

#### 第二层：trace level

两条路线都在相同 saved trajectories 上与 gold monitor 比较：

- violation precision、recall 和 F1；
- false-negative rate；
- false-positive rate；
- violation event timing error；
- deadline boundary accuracy；
- terminal-unresolved accuracy；
- minimal-pair flip accuracy；
- paraphrase consistency。

在安全问题中，不能只报告整体 accuracy。由于非违反样本可能远多于违反样本，一个
总是输出 0 的模型也可能得到看似很高的 accuracy。

#### 第三层：policy level

只有通过基本 trace-level gate 的方法才进入 RL training。之后固定：

- environment；
- task reward；
- online Safe RL backend；
- policy architecture；
- cost budget；
- training steps；
- random seeds；
- evaluation episodes。

最终 policy evaluation 只使用 gold STL monitor，而不使用方法自己的 predicted cost。
主要报告：

- gold violation per trigger；
- missed recovery obligations；
- terminal unresolved rate；
- goal success；
- episode return；
- trigger rate；
- 不同 seeds 的不确定性。

## 7. Stage II 必须修改的公平性问题

当前 Stage I specification 要求 task-only、native-cost 和 gold-STL-cost conditions
都获得相同的 gold monitor temporal state：

```text
active obligation
overdue indicator
normalized remaining deadline
```

这在 Stage I 中合理，因为公式固定，目标是只比较三种 learner cost。

但是在 Stage II 的 representation comparison 中，如果直接把 gold monitor state
提供给 `NL -> learned cost` 路线，就等于提前把正确 STL 解析出的 obligation 和
deadline 状态告诉了 direct baseline。这样会泄漏形式化路线的答案，不能用于主
实验。

Stage II 主实验应采用以下原则之一：

1. 所有 policies 使用同一个 recurrent policy，并只读取相同的原始环境历史；或
2. 所有 policies 获得同一个与具体 STL 无关的 causal history window，例如最近
   (K_{\max}) 步的 safety signals。

在主 cost-source comparison 中：

- formal monitor 可以在内部维护 monitor state，用于产生 cost；
- direct predictor 可以维护自己的 learned hidden state，用于产生 cost；
- gold monitor state 不直接作为 direct policy 的输入；
- policy 看到的通用环境与历史信息必须一致。

可以另外进行一个 system-level ablation，让 formal route 显式向 policy 提供 monitor
state，并测量该结构化状态的额外价值。但该结果必须与“只比较 cost source”的主
实验分开解释。

## 8. 两类 direct baseline

为了避免选择明显过弱的对手，建议区分：

### 8.1 Published-style current-observation baseline

输入自然语言 constraint 和当前 observation description，直接预测当前 cost。该类
方法与已有 free-form natural-language cost prediction 工作接近，工程简单，但原则上
无法完整表示 bounded-recovery deadline。

它可以用于说明即时 semantic similarity cost 的限制，但不应是唯一 direct baseline。

### 8.2 History-aware direct baseline

输入自然语言和 trajectory prefix，通过 RNN、Transformer 或其他 causal memory
直接预测 cost。它没有显式 STL 公式，但有能力表示 non-Markovian safety labels。

它应作为显式 NL-to-STL path 的主要公平对手。否则实验只能说明“有记忆的方法优于
无记忆的方法”，而不能说明“显式形式化中间表示优于直接学习 cost”。

## 9. 修改前后，当前实验各部分的角色

| 当前内容 | 修改后的处理 | 新的准确定位 |
|---|---|---|
| 一条 (K=79) bounded-recovery rule | 保留 | 第一个 gold-STL control case |
| Online monitor、oracle、RTAMT agreement | 保留 | gold label generator 和 monitor-correctness evidence |
| Task-only / native / gold-STL 三条件 | 保留 | Stage I downstream controls，不是最终研究问题 |
| 所有 Stage I conditions 获得 monitor state | Stage I 保留 | 只隔离 learner cost 的影响 |
| Stage II direct baseline 获得 gold monitor state | 不采用 | 会泄漏 formal representation 的答案 |
| 单一自然语言句子 | 扩展 | 小型 controlled specification set |
| 直接开始多组 RL training | 修改 | 先 formula/trace gate，再训练 policy |
| 用各方法自己的 cost 评价安全性 | 不采用 | 最终统一使用 gold STL oracle |
| 只比较 violation 和 reward | 扩展 | 同时比较公式、cost labels、policy behavior 和 failure source |

## 10. 最简化的新实验叙事

修改后的完整逻辑可以用以下流程说明：

```text
1. 先完成当前 Gold-STL -> monitor -> Safe RL baseline
2. 建立少量受控语言、gold STL 和共同轨迹
3. 用 gold monitor 为轨迹生成统一正确答案
4. 比较 NL -> STL 与 history-aware NL -> cost
5. 先检查公式和轨迹 cost labels
6. 再把两种 cost 接入相同 Safe RL backend
7. 用 gold monitor 评价最终 policies
8. 将失败定位到 translation、grounding、cost prediction 或 RL optimization
```

通俗地说，这不再只是证明“STL cost 能不能用”，而是比较两种理解人类安全要求
的方法：

- 一种先把语言写成可检查的正式规则，再按规则判断轨迹；
- 另一种不写正式规则，直接从语言和轨迹预测有没有违反。

我们要研究的是：前者是否更准确、更容易检查和定位错误，并最终让 Safe RL 更可靠；
同时也要公平检验后者是否能用更简单、更灵活的方式达到相同效果。

## 11. 预期贡献和限制

### 可以主张的内容

- 建立一个 matched NL-to-STL versus direct NL-to-cost comparison；
- 在 formula、trace 和 policy 三层评价表示选择的影响；
- 使用 semantic minimal pairs 检查否定、时间范围、持续性和参数变化；
- 使用统一 gold monitor 将 language error 与 RL optimization error 分开；
- 通过理论命题说明 temporal memory 和 cost underestimation 的影响。

### 当前不能主张的内容

- STL-to-Safe-RL 本身是新方法；
- monitor state augmentation 是新方法；
- logic violation to PPO-Lagrangian cost 是新方法；
- 显式 STL 必然优于 learned cost；
- PPO-Lagrangian 提供零违反保证；
- 一个 benchmark 的结果可以直接推广到动态障碍、视觉感知或真实机器人。

### 主要限制

- 第一版使用受控语言，不处理开放式模糊表达；
- environment signals 和数值参数必须已定义；
- gold STL 和 gold grounding 仍需要人工确认；
- learned direct cost 与 NL-to-STL 的 supervision 不同，资源公平需要透明报告；
- SafetyPointGoal1-v0 是简单静态导航环境，external validity 有限；
- 最终结论是统计和经验性的，不是形式化闭环安全保证。

## 12. 与当前工作进度的关系

截至 2026-08-10：

- Stage I 的环境信号、规则参数、online monitor、offline oracle、fixtures 和 RTAMT
  agreement 已完成；
- 当前 `d_warn=0.45`、`d_safe=0.55`、`K=79`；
- OmniSafe wrapper、三个 cost-routing 条件、vectorized lifecycle tests、真实
  positive-cost probe 和一次 64-transition PPO-Lagrangian update 已完成；
- 尚未开始 RL training；
- controlled language dataset、NL-to-STL translator 和 direct learned-cost baseline
  尚未进入实现阶段。

因此，当前工作不再是继续证明 benchmark 可以启动。立即顺序是先冻结 cost budget
与 evaluation protocol，完成一个会在 policy rollout 中真实触发 STL cost 的小型
sanity run，再决定是否进行 matched-seed Stage I 主训练。同时，应把 Stage I 描述为
gold-STL baseline，把上述 representation comparison 作为项目级核心问题。

## 13. 直接相关参考资料

- Venkataraman, Aksaray, and Seiler. [Tractable Reinforcement Learning of
  Signal Temporal Logic Objectives](https://proceedings.mlr.press/v120/venkataraman20a.html),
  L4DC 2020. 说明 STL-RL 对历史状态的需求及紧凑历史表示。
- Ikemoto and Ushio. [Deep Reinforcement Learning under Signal Temporal Logic
  Constraints Using Lagrangian Relaxation](https://arxiv.org/abs/2201.08504),
  2022. 说明 STL constraint 与 Lagrangian DRL 的直接先例。
- Yang et al. [Safe Reinforcement Learning with Natural Language
  Constraints](https://openreview.net/forum?id=Ua5yGJhfgAg), NeurIPS 2021.
  提供自然语言 constraint interpreter 与 Safe RL 的早期直接相关设置。
- Lou et al. [Safe Reinforcement Learning with Free-form Natural Language
  Constraints and Pre-Trained Language Models](https://arxiv.org/abs/2401.07553),
  AAMAS 2024. 提供 direct language-conditioned cost prediction baseline。
- Low and Kumar. [Safe Reinforcement Learning with Learned Non-Markovian
  Safety Constraints](https://arxiv.org/abs/2405.03005), 2024. 提供 history-aware
  learned safety model 的相关方法。
- Dong et al. [From Text to Trajectory: Exploring Complex Constraint
  Representation and Decomposition in Safe Reinforcement Learning](https://openreview.net/forum?id=MDpIQ9hQ7H),
  NeurIPS 2024. 提供 trajectory-level textual constraint translator baseline。
- Zhang et al. [Integrating LTL Constraints into PPO for Safe Reinforcement
  Learning](https://arxiv.org/abs/2603.01292), 2026. 说明 monitor violation to
  cost to PPO-Lagrangian 已有直接工作。

本地 2026-08-10 相关论文集合见：

```text
references/papers/related/CLOSEST_PRIOR_WORK_8.10.md
```
