# Stage I 代码失败分析与修复建议

- **日期：** 2026-08-12
- **状态：** 诊断与候选修复建议；不是冻结协议，也不是追加 GPU 训练授权
- **直接证据：** `docs/stage1_pilot_result_report.md`、
  `results/stage1_pilot/analysis/analysis.json`、冻结配置和当前源码
- **决策边界：** 不修改 D31；O8 仍需负责人明确选择；所有建议均须先冻结再运行

## 1. 执行结论

当前 negative pilot 不能归因于“STL monitor 算错”。1,500 条正式评估轨迹上的
online monitor、独立 oracle 和 RTAMT 已完全一致，三种环境的 learner-cost routing
也与声明一致。失败更准确地位于：**正确的时序安全事件已经生成，但当前
PPO-Lagrangian 接收到的训练目标、信用分配和优化时序不足以让策略稳定改变
warning 后的恢复行为。**

最关键的四个问题是：

1. 训练约束优化的是每 episode 的 missed-event 总数，primary metric 却是
   `missed obligations / triggered obligations`；分母会随策略改变，两者并不等价。
2. binary STL cost 只在第 79 步 deadline 或 episode 结束时出现，信号极稀疏且延迟；
   trigger 附近动作得到的直接 cost credit 很弱。
3. `cost_limit=0.1 event/episode` 比“相对 task-only 降低 30%”对应的经验尺度严格得多；
   multiplier 到训练后段才达到明显量级，而 actor learning rate 同时接近零。
4. OmniSafe 0.5.0 的实际 on-policy 实现存在需要项目侧封装和测试的运行语义：
   time-limit cost bootstrap、cost advantage 仅去均值、50-episode 硬编码窗口，以及
   未在该 buffer 路径使用的 `cost_gamma` 配置。

建议优先顺序是：

- **P0：** 不训练，先补 adapter 级回归测试、运行时 contract 和诊断日志；
- **P1：** 只有 O8-C 获批后，运行有上限、非确认性的 optimization / budget /
  credit-assignment 诊断；
- **P2：** 选定设置后从头使用新的五个 matched seeds 做确认性实验；不得续跑当前
  epoch-100 checkpoint，也不得把 D31 pilot 重命名为 main study。

## 2. 与总体研究方向的关系

长期研究要在同一个 Safe RL 后端中比较：

```text
显式 NL -> STL -> verified monitor cost
                    versus
NL + causal history -> learned cost predictor
```

Stage I 的职责是建立前者的 gold downstream reference，而不是加入语言模型。当前结果
说明 gold formula 和 monitor 的**语义正确性**已经成立，但 gold cost 的**策略学习
有效性**尚未成立。如果直接进入 Stage II online policy comparison，可能把
“formal path 的稀疏信用分配失败”误判成“formal representation 不如 learned cost”。

因此：

- Stage II 的 O7 schema、数据生成和 offline label benchmark 可以继续；
- Stage II 的最终 online policy comparison 应等待一个能够对 gold cost 作出可诊断
  响应的 Stage I reference；
- 如果后续形成“保持 gold event 语义和 episode cost 总量、只重分配时序 credit”的
  方法，它可以成为独立候选贡献，但必须先补 reward redistribution、temporal-logic
  shaping 和 CMDP surrogate 的 prior-art 检索，不能现在宣称 novelty。

## 3. 证据分级

| 级别 | 含义 | 当前项目中的项目 |
|---|---|---|
| 已确认事实 | 可由 frozen config、源码、测试或结果直接复核 | metric/learner objective 不同；cost 稀疏延迟；budget 尺度；LR/multiplier 时序；50-window；cost advantage 处理；`cost_gamma` 路径 |
| 已确认语义风险 | 代码行为确定，且与本项目定义存在冲突；实际效应大小未量化 | terminal-unresolved 后仍进行 cost-value bootstrap |
| 高可信因果解释 | 与机制和曲线一致，但尚无隔离实验 | 延迟 credit、过严 budget、晚到的 multiplier 与衰减 LR 共同导致策略响应不足 |
| 待验证假设 | 必须通过 prospectively frozen ablation 才能判断 | 更强 multiplier、不同 event budget、credit redistribution 能否改善 missed/trigger |
| 已排除的主要解释 | 现有验证已经直接否定 | cost route 接错、policy 缺 monitor memory、online/oracle/RTAMT 不一致、final checkpoint/obs normalizer 加载错误 |

## 4. 已确认的问题与影响

### 4.1 Primary metric 与 learner constraint 不同

冻结 primary metric 为：

\[
R(\pi)=\frac{\mathbb{E}_{\pi}[M]}{\mathbb{E}_{\pi}[N]},
\]

其中 \(M\) 是 missed obligations，\(N\) 是 triggered obligations。当前 PPOLag 则约束
episode additive cost：

\[
J_C(\pi)=\mathbb{E}_{\pi}\left[\sum_t c_t\right]
       =\mathbb{E}_{\pi}[M].
\]

`configs/stage1_pilot/protocol.yaml` 明确声明 primary 分母为 `warning_trigger`；
`src/safety_stl/monitor.py` 只在 deadline violation 或 terminal unresolved 时输出
`stl_cost=1`；`src/safety_stl/omnisafe_env.py` 再把这个 event cost 原样路由给 learner。

正式评估恰好展示了差异：

| 条件 | Missed/episode | Triggers/episode | Missed/trigger |
|---|---:|---:|---:|
| task-only | 1.732 | 6.700 | 25.85% |
| gold-STL | 1.724 | 6.622 | 26.03% |

gold 的 missed 总数下降约 0.46%，但 trigger 总数下降约 1.16%，所以最终比率反而略升。
native-cost 更明显：它把 triggers 降到 4.65、missed 降到 1.38，却把条件失败率提高到
29.65%。这不是统计实现错误，而是两个 estimand 回答不同问题。

**影响：** 即使 learner 成功减少 `events/episode`，也不保证 primary ratio 改善。不能
用更多 evaluation episodes 修复这个目标不一致；更多评估只会缩小不确定性。

### 4.2 Binary event cost 极稀疏且延迟

当前 monitor 在 warning trigger 和 pending 阶段不产生 cost。只有以下两种情况产生 1：

- trigger 后第 `K=79` 步仍未恢复；
- episode 在 pending 状态结束，记为 terminal unresolved。

gold 条件最后 20 epochs 平均为 1.650 events / 1,000-step episode，即正 cost 只占
约 0.165% 的 environment steps。PPOLag 使用 `gamma=0.99`、`lam_c=0.95` 的 GAE。
忽略 learned value residual 时，deadline spike 回传到 79 步前 trigger 的递推系数约为：

\[
(\gamma\lambda_c)^{79}=(0.99\times0.95)^{79}\approx0.00786.
\]

**影响：** 策略在接近 hazard 或刚触发 obligation 时，几乎收不到直接、稳定的区分
信号；cost critic 必须从很少的 terminal/deadline 样本中推断长时依赖。policy
observation 已包含 active、overdue、remaining fraction，所以问题不是缺少 temporal
state，而是这个 state 对应的学习信号太晚。

### 4.3 `0.1` budget 与 30% primary target 的尺度不匹配

冻结协议已经正确注明 `0.1` 的单位是 missed events/episode，而不是 10% violation
rate。但这个数值本身仍非常严格：

- task-only primary rate 为 25.85%，其 30% relative-reduction 门槛为 18.10%；
- 若只用 gold 当前 6.622 triggers/episode 作尺度换算，18.10% 约等于
  1.20 missed events/episode；
- `0.1` 在相同 trigger 频率下约等于 1.51% missed/trigger；
- 相对 task-only 的 1.732 missed/episode，`0.1` 要求 event count 下降约 94.2%。

这里的 1.20 只能用于量级判断，因为 trigger frequency 会随 policy 改变，不能把它
冻结为 ratio 的精确等价预算。

**影响：** 当前实验同时在问“能否达到 30% 比率改善”和“能否满足一个近似要求
94% event-count 改善的 CMDP budget”。gold 最后 20 epochs cost 为 1.650，是 limit 的
16.5 倍；这个结果首先表明约束未满足，不能据此判定 30% 的目标本身不可实现。

### 4.4 Multiplier 生效晚，actor 学习能力同时衰减

五个 gold runs 的 multiplier 首次跨过 1 约在 270k–280k transitions，跨过 2 在
520k–570k，跨过 3 在 790k–880k。与此同时，actor 使用从 `3e-4` 线性衰减到 0 的
learning-rate schedule：最后 20 epochs 平均约 `2.85e-5`，最后一行记录为 0。

另外，gold 的 500 个 epochs 中有 426 个（85.2%）在 40 次 policy update 之前触发
KL early stop，平均 `StopIter=21.18`。early stop 本身是 PPO 的保护机制，不应单独
视为 bug；但它说明实际 policy optimization 次数显著低于 nominal 40。

**影响：** cost pressure 到后半段才明显增强时，actor 的步长和实际 update 数都已经
受限。继续现有 final checkpoint 尤其不合理，因为其 schedule 已到零。任何 longer
run 都应从初始化开始，并为新的总预算重新定义 schedule。

### 4.5 Cost advantage 没有按标准差归一化

冻结配置设置 `standardized_rew_adv=true` 和 `standardized_cost_adv=true`。但已安装的
OmniSafe 0.5.0 在 `vector_onpolicy_buffer.py` 中实际执行：

```text
adv_r <- (adv_r - mean_r) / std_r
adv_c <- adv_c - mean_c
```

PPOLag 随后计算 `(adv_r - lambda * adv_c) / (1 + lambda)`。因此 reward advantage
被标准化到无量纲尺度，cost advantage 只去均值，没有除以其标准差。

**分类：** 这是已确认的 runtime behavior；它是否是 OmniSafe 上游的有意设计尚不
确定，不能简单称为上游 bug。

**影响：** sparse cost advantage 的方差和量级直接影响 lambda 所代表的有效权重；
仅比较不同 cost 单位下的 lambda 数值没有意义。后续应记录 `adv_r/std`、`adv_c/std`
以及 reward/cost policy-gradient norm，再决定是否需要项目侧显式 scale。

### 4.6 Episode 截断后的 cost bootstrap 与 monitor 结算语义不一致

当前链路的行为是：

1. `monitor.py` 在 episode time limit 且 obligation pending 时输出
   `terminal_unresolved=1` 和 `stl_cost=1`；
2. `omnisafe_env.py` 把 reset 前的 active monitor state 放入 `final_observation`；
3. OmniSafe `onpolicy_adapter.py` 把 truncation 当作可 bootstrap 的 timeout，同时从
   `final_observation` 计算 reward value 和 cost value；
4. buffer 因而收到该步 event cost，同时以非零 `last_value_c` 结束路径。

对 reward 来说，time-limit bootstrap 是常见处理；但本项目已经把 unresolved
obligation 在 episode 边界结算并在下一 episode reset。按这个定义，结算后的未来
STL episode cost 应为 0，不能同时假设 active obligation 在边界后继续。

正式 gold 评估的 862 个 missed obligations 中有 178 个是 terminal unresolved，约
20.6%，所以这不是完全罕见的边界。

**影响：** cost critic target 可能同时含“本步已经结算的 1”和“active final state 的
未来 cost value”。这不会改变保存的 raw event count 或 gold evaluator，但可能扭曲
cost critic 和 policy gradient。当前没有隔离实验，不能声称它导致了多少性能损失。

**修复原则：** reward 和 cost 必须允许不同的 truncation bootstrap 语义。对已经按
episode 结算的 STL cost，应在 project-owned adapter 中令 `last_value_c=0`；不得直接
修改 Conda 环境中的 `site-packages`。

### 4.7 配置表面与实际运行不一致

#### Logger rolling window

冻结配置为 `logger_cfgs.window_lens=100`，但 OmniSafe `PolicyGradient._init_log()`
对 `Metrics/EpRet`、`Metrics/EpCost`、`Metrics/EpLen` 硬编码 `window_length=50`。
PPOLag 的 multiplier update 又直接读取这个 `Metrics/EpCost` 均值。因此 10 个 vector
env 下，lambda 依据的是约 5 epochs / 50 completed episodes 的滚动值，而不是配置
表面暗示的 100 episodes。

#### `cost_gamma`

冻结配置同时写有 `gamma=0.99` 和 `cost_gamma=0.99`。当前 on-policy
`PolicyGradient` 构造 `VectorOnPolicyBuffer` 时只传入 `gamma`、`lam`、`lam_c`；buffer
内部 reward 和 cost return 共用传入的 `gamma`，没有读取 `cost_gamma`。

本次两者恰好相同，因此没有数值差异；但以后只改 `cost_gamma` 会产生“配置已变、
实际 cost discount 未变”的静默错误。

**修复原则：** 启动时生成 effective-runtime contract，明确记录实际 window、reward
discount、cost discount、advantage transform 和 bootstrap policy；发现声明与运行
不一致时 fail fast。

## 5. 已排除的问题

以下部分不应继续作为主要根因消耗实验预算：

- task/native/gold 三条 selected cost route 在训练日志中逐点一致；
- wrapper 保留 native reward，并分别记录 native cost、raw STL cost 和 selected cost；
- policy observation 已从 60 维扩展为 `60 + 3`，包含 monitor temporal state；
- vector slot 各自维护 monitor，并在 final observation 后 reset；
- 1,500/1,500 正式评估的 online/direct oracle event label 一致；
- RTAMT 最大 robustness difference 为 0；
- evaluator 加载 fixed epoch-100 checkpoint 和保存的 observation normalizer；
- 54 项自动测试通过。

这些结论只排除了现有测试覆盖范围内的 wiring/semantic disagreement，不构成形式化
安全保证，也不表示训练算法一定正确。

## 6. 分层修复建议

### P0 — 先完成、无需 GPU 的代码审计与测试

#### P0.1 截断 bootstrap 回归测试

用 scripted one-slot buffer 构造：final step `terminal_unresolved=1`，fake cost critic
返回非零值。测试应分别断言：

- legacy OmniSafe path 当前确实把非零 `last_value_c` 送入 `finish_path`；
- project episodic-STL path 在相同 transition 上使用 `last_value_c=0`；
- reward `last_value_r` 是否 bootstrap 由 task time-limit 定义单独决定；
- saved raw STL event 仍为 1，monitor reset 后下一 episode 不继承 obligation。

先让测试展示当前行为，再实现项目内 adapter；不要 patch 已安装包。

#### P0.2 Effective-runtime contract

每个 run 的 manifest 除当前 config/hash 外，新增并校验：

- effective reward gamma 与 cost gamma；
- reward/cost timeout bootstrap policy；
- EpCost rolling-window episode 数；
- reward/cost advantage 的中心化、标准差归一化方式；
- actor LR schedule 的起点、终点和非零 floor；
- multiplier init、optimizer、LR、实际用于 update 的 `Jc` 统计窗口。

只记录用户输入 config 不足以复现第三方库的实际行为。

#### P0.3 诊断日志

后续 screening 至少逐 epoch 保存：

- raw current-epoch cost、10-episode mean、实际 rolling-50 `Jc`；
- `adv_r`/`adv_c` 的 mean、std、非零比例和分位数；
- reward/cost critic target、prediction、calibration error；
- reward 与 cost 部分对 actor 的 gradient norm；
- trigger 到 recovery/violation 的 latency、pending occupancy、deadline proximity；
- terminal-unresolved 和 deadline-violation 分开统计；
- LR、KL stop iteration、lambda 及其增量。

这一步的目标是让“惩罚没生效”可以定位为 value learning、policy gradient、lambda
时序或 cost definition 中的某一环，而不是再依赖总曲线猜测。

### P1 — O8-C 获批后才可运行的 bounded diagnostic

#### P1.1 Optimization diagnostic

保留 binary gold event 和 gold evaluator，prospectively 比较当前 optimization control
与一个更强但单一的候选设置。候选设置应同时满足：

- 从初始化训练，不续跑 epoch-100 checkpoint；
- actor 使用 constant LR 或明确的非零 floor，使后期 lambda 压力仍能更新策略；
- multiplier init/LR 只选一个预声明变体，不能看结果后追加搜索；
- 实际 rolling window 明确、可测试；
- 选择依据是预声明的 curve/gradient gate，不是挑 final evaluation 最好的 cell。

#### P1.2 Budget diagnostic

STL limit 必须继续使用 `missed events/episode` 单位。建议围绕 pilot 的经验尺度预先
冻结至多三个候选值，例如把约 1.20 的 primary-target scale 放在 sweep 中间附近，
同时保留一个更严格和一个更宽松值。具体数字当前**不批准、不冻结**；它们必须写入
新的 O8 config，并说明 trigger frequency 依赖 policy，所以不是 ratio 的精确换算。

不要把 native `25.0` 与 STL limit 做数值比较，也不要把 `0.1` 解释为 10%。

#### P1.3 首选 credit repair：保持 event mass 的 rollout 后时序重分配

对第 \(i\) 个 obligation，令 \(z_i=1\) 表示最终 missed，\(W_i\) 是从 trigger 到
deadline 的窗口；terminal unresolved 使用 trigger 到 episode end 的已观察前缀。把
单个 deadline spike 替换为：

\[
\tilde c_t=\sum_i z_i w_{i,t},\qquad
w_{i,t}\ge 0,\qquad \sum_{t\in W_i}w_{i,t}=1.
\]

成功恢复的 obligation 令 \(z_i=0\)。于是每个 episode 都满足：

\[
\sum_t\tilde c_t=\sum_i z_i=\text{raw missed-obligation count}.
\]

建议第一个 ablation 使用 uniform weights，避免额外调参。这个 transform 在 rollout
收集后、PPO return 计算前回填 buffer；它使用 outcome hindsight，但不会把未来信息
提供给动作选择，也不改变 policy observation。为避免“causal”一词产生歧义，报告中
应称其为 **post-rollout temporal credit redistribution**，而不是 online causal cost。

必须同时保留两列：

- `raw_gold_stl_event_cost`：评价、统计、budget 和 oracle 真值；
- `learner_redistributed_cost`：仅供 policy update。

并逐 episode 断言 mass conservation。该 shaping cell 仍用 unchanged raw gold oracle
评估，不能用自身 shaped signal 给自己判分。

这个方案比直接使用 distance robustness 更适合作为第一修复，因为它保持 missed-event
的 episode 总量和单位，只改变时间 credit。robustness、deadline urgency 或 active-risk
auxiliary 可以作为后续独立方法，但会引入尺度和语义变化，不应与第一轮混在一起。

#### P1.4 不建议第一步直接优化 ratio

直接把 learner cost 改成 `missed/triggers` 会引入非加性、随机分母、zero-trigger 和
跨 episode 估计问题。也不能简单把每次 violation 除以 episode 的最终 trigger 数，
因为这同样使用 hindsight 且改变每个 transition 的 policy-gradient estimand。

较稳妥顺序是先修正 adapter 语义、验证 additive event learner 能响应，再把
obligation-normalized CMDP estimator 作为单独研究方法设计和评审。

### P2 — 确认性实验

如果 bounded diagnostic 通过预声明 gate：

1. 先把最终 Stage I standard 写入新的 decision/config，不覆盖 D31；
2. 使用五个新的 matched training seeds，从初始化训练；
3. 固定 final checkpoint、deterministic policy mode 和 unchanged gold evaluator；
4. 继续使用 100 paired evaluation episodes/seed/condition 和 10,000 次 paired
   hierarchical bootstrap；
5. 同时报 missed/trigger、missed/episode、trigger/episode、goal success 和 return；
6. 原 15M-transition D31 pilot 永久保留为 pilot-driven negative evidence，不能并入
   confirmatory confidence interval。

## 7. 建议的最小诊断顺序

以下只是 O8-C 的候选结构，不是执行授权：

| 顺序 | 比较 | 固定项 | 要回答的问题 |
|---|---|---|---|
| D0 | adapter scripted tests | 无 RL training | terminal cost 是否被重复 bootstrap；runtime contract 是否真实 |
| D1 | current binary optimization vs 一个预声明 optimization variant | rule、raw cost、budget、gold evaluator | learner 是否因 LR/lambda 时序而无响应 |
| D2 | 至多三个 event/episode limits | 采用 D1 预声明 gate 选出的 optimizer | budget 是否可学习且与经验尺度相容 |
| D3 | binary spike vs 一个 mass-conserving redistribution | optimizer、event budget、raw oracle | 问题是否主要来自时序 credit |

每阶段只在前一阶段工程 gate 通过后继续，使用 O8 proposal 中的非 pilot seeds、
300k–500k transitions/cell 和 30–50 paired screening episodes 的候选上限。所有数值和
stop rules 必须在启动前冻结；screening 不作最终显著性声明。

## 8. 修复后的验收标准

### 工程 gate

- monitor/direct oracle/RTAMT 继续 exact agree；
- raw event、learner cost、native cost 三者独立且命名明确；
- project adapter 的 reward/cost truncation tests 通过；
- runtime contract 与有效代码路径逐项一致；
- mass-conserving cell 每 episode 的 learner-cost sum 等于 raw missed count；
- checkpoint/config/source/evaluator hashes 继续可追溯。

### Screening gate

- matched non-pilot seeds 上 missed/trigger 有方向一致的下降趋势；
- 下降不是仅靠把 trigger 数降得更快造成；
- goal success 无明显坍塌；
- lambda、cost critic 和 gradient 指标表现出可解释的响应；
- 若曲线仍未稳定，只能称 diagnostic evidence，不能称 converged。

### Final gate

沿用负责人已批准的主标准：gold-STL 相对 task-only 至少降低 30%，同时报告绝对差；
task-only rate 为零时只使用绝对差；goal success 使用 10 percentage-point
non-inferiority margin。任何新 shaping/adapter 都必须用 unchanged gold evaluator
接受最终判定。

## 9. 建议的代码归属

不要修改 `/home/jerry/anaconda3/envs/stl-stage1/.../site-packages/omnisafe`。若 O8-C
批准，建议把变化放在仓库内：

| 建议位置 | 职责 |
|---|---|
| `src/safety_stl/omnisafe_adapter.py` | 项目定义的 reward/cost timeout bootstrap 和 effective-runtime contract |
| `src/safety_stl/credit_assignment.py` | raw event 到 learner credit 的显式、可测试 transform |
| `tests/test_omnisafe_adapter.py` | truncation、epoch cut、true termination 和 vector-slot regression |
| `tests/test_credit_assignment.py` | mass conservation、成功义务为零、overlap/terminal boundary |
| 新的 `configs/stage1_o8_diagnostic/` | 与 D31 隔离的候选 cells、seeds、budget 和 stop gates |
| runner manifest | 保存 effective runtime、raw/learner cost 定义和所有 hashes |

现有 `monitor.py` 和 gold evaluator 应保持为 reference semantics；不要为了让训练更容易
而改写 gold label。

## 10. 明确不建议的做法

- 不要只增加 evaluation episodes；它不能修复 learner；
- 不要续跑 final checkpoint；actor LR 已衰减到零；
- 不要把更多 transitions 当成默认答案；当前 multiplier/cost 曲线不支持这一结论；
- 不要覆盖冻结的 D31 configs、结果或报告；
- 不要直接 patch Conda `site-packages`，否则环境不可审计；
- 不要比较 native 与 STL multiplier/limit 的数值大小；单位不同；
- 不要把 robustness 或 dense proximity cost 静默称为 gold STL event cost；
- 不要用 shaped learner cost 代替 unchanged gold oracle 做最终评价；
- 不要从 empirical improvement 推出 formal safety guarantee；
- 不要在完成新增 prior-art review 前宣称 credit redistribution 是新方法。

## 11. 当前建议的决策

从研究解释力和计算成本看，建议负责人选择 **O8-C：bounded diagnostic**，并按
`P0 -> D1 -> D2 -> D3` 的顺序逐门执行。当前最先应该做的是 P0 的无 GPU 测试与
runtime instrumentation 设计；在 O8-C 的具体参数、cell 数和 stop rules 正式冻结前，
不启动任何新的 GPU training。

