# Stage I 结果与 Stage II 转入状态

> **Current execution note (2026-08-12):** Sections 2--10 preserve the Stage I
> experiment and its historical gates. D37 has since frozen O7, and D38 has
> authorized the continuous Stage II work package. For current execution order,
> use [`STAGE2_CONTINUOUS_WORK_ORDER.md`](STAGE2_CONTINUOUS_WORK_ORDER.md) and
> [`CURRENT_EXECUTION_DIRECTIVE.md`](CURRENT_EXECUTION_DIRECTIVE.md). Any older
> statement below saying that only Stage I is authorized or that O7 awaits an
> owner decision is historical and superseded.

## 1. 文档目的

本文档记录截至 2026-08-12 的 Stage I 完整状态，集中回答四个问题：

1. 已经完成了哪些研究和工程步骤；
2. 当前可视化具体展示了什么；
3. 哪些结果可以从可视化中得出，哪些不能；
4. 还有哪些工作未完成，下一里程碑应如何实施和验收。

本文件是当前执行状态的总览。规则的规范语义仍以
[`stage1_rule_monitor_spec.md`](stage1_rule_monitor_spec.md) 为准，研究决策仍以
[`DECISIONS.md`](../DECISIONS.md) 为准。

## 2. 项目目标与当前边界

长期项目链路是：

```text
natural-language requirement
        ->
grounding to measurable signals and parameters
        ->
STL specification
        ->
trajectory monitoring and STL-derived cost
        ->
Safe RL training and evaluation
```

完整研究被拆成三个阶段，是为了分别定位语言理解、grounding、monitor/cost 和
Safe RL 学习产生的错误。

- **Stage I：**移除语言模型，人工固定一条正确 STL 规则，验证下游链路；
- **Stage II：**加入对象、距离和时间参数明确的受控语言；
- **Stage III：**再研究模糊语言、感知噪声、动态环境和更多规则结构。

Stage I 当时的研究问题是：

> 在一个已知静态障碍的简单导航环境中，一条人工确认正确的 bounded-recovery
> STL 规则能否被正确监测并转换成 Safe RL cost，从而减少超时恢复失败，同时
> 不造成不可接受的目标完成能力下降？

目前已经完成环境、信号、规则、参数、monitor、reference agreement、可视化、
STL-cost wrapper、on-policy positive-cost sanity、统一 checkpoint evaluator、O6
pilot protocol 冻结、三条件 small-budget sanity、resumable runner、15M-transition
full pilot、1,500 条 paired evaluation、10,000 次 bootstrap、四组结果图和 WP1
正式报告。结果没有达到 30% safety target，但 goal-success non-inferiority 通过；
学习曲线不支持 convergence claim。

### 2.2 2026-08-12 full-pilot 结论

- task-only/gold-STL missed obligations per trigger = `25.85%/26.03%`；
- relative reduction = `-0.71%`，95% CI `[-24.92%, +21.88%]`；
- task-only/gold-STL goal success 均为 `100%`；
- gold-STL final-20 selected cost = `1.650` events/episode，高于 `0.1` limit；
- multiplier 继续上升，因此 pilot 不等于 final main study 或已收敛解。

完整解释和图表见 [`stage1_pilot_result_report.md`](stage1_pilot_result_report.md)。

### 2.1 2026-08-10 研究定位修正

最新文献核查发现，以下方法成分均已有直接先例：STL 的历史/状态扩展、STL
constraint 的 Lagrangian DRL、online STL monitor 输出作为 observation/reward、
logic violation 转 PPO-Lagrangian cost，以及 full-STL multi-constraint CRL。

因此 Stage I 不再被描述为一个新的 STL-to-Safe-RL 算法。它的作用是建立：

```text
gold STL -> verified monitor -> Safe RL
```

这一可验证下游基线。后续 Stage II 才测试当前暂定的项目级研究问题：在相同
environment 和 online Safe RL backend 下，显式 `NL -> STL -> verified cost`
是否比直接 `NL -> predicted cost` 具有更好的语义忠实度、轨迹级可诊断性和
最终时序安全表现。

该新问题的文献边界、理论可行性和修订实验路线见
[`research_direction_novelty_feasibility.md`](research_direction_novelty_feasibility.md)。

## 3. 固定的 Stage I 实验定义

| 项目 | 固定内容 |
|---|---|
| Application | 二维 Point agent 绕静态 hazards 导航 |
| Benchmark | `SafetyPointGoal1-v0` |
| Task objective | 保留 benchmark 原生 goal-reaching reward |
| Safe RL framework | OmniSafe 0.5.0 |
| Initial algorithm | PPO-Lagrangian |
| Reference monitor | RTAMT 0.3.5 |
| Distance signal | 公开 `hazards_lidar` 重建的最近 hazard 中心距离 |
| STL rule family | 单条 hysteretic bounded-recovery 规则 |
| Cost | 首版使用稀疏 binary deadline-event cost |

距离定义为：

```text
d_t = 3 * (1 - max(hazards_lidar))
```

该距离是 agent 原点到最近 hazard 中心的距离，并在 lidar range 3 处截断；它不是
boundary-to-boundary clearance。

固定规则参数为：

```text
d_warn = 0.45
d_safe = 0.55
K = 79 environment steps
```

规范规则为：

```text
G(e_t -> F_[0,79](d_t >= 0.55))
```

其中 `e_t` 只在 monitor 为 `INACTIVE` 且 `d_t < 0.45` 时开始一个新的 warning
episode。episode 在 `d_t >= 0.55` 时关闭；在中间 hysteresis 区间内不会重复触发。

## 4. 已完成的步骤

### 4.1 研究定义与阶段拆分

已完成：

- 原始 NL-to-STL-to-Safe-RL 问题定义；
- 核心文献和相关路线比较；
- Stage I、II、III 的责任边界；
- application、benchmark、STL 规则、Safe RL framework 和 reference monitor 选择；
- task reward 与 safety requirement 分离；
- Stage I 不加入语言模型、视觉感知、动态障碍、shielding 和多规则族等范围限制。

### 4.2 可复现软件环境

已建立并验证 Conda 环境 `stl-stage1`。主要版本为：

| 组件 | 版本 |
|---|---:|
| Ubuntu | 22.04.5 LTS |
| Python | 3.8.20 |
| Safety-Gymnasium | 1.0.0 |
| Gymnasium | 0.28.1 |
| MuJoCo | 2.3.3 |
| OmniSafe | 0.5.0 |
| RTAMT | 0.3.5 |
| PyTorch | 2.4.1+cu124 |
| GPU | NVIDIA GeForce RTX 4090, 24,564 MiB |
| NVIDIA driver | 560.35.03 |
| PyTorch CUDA / cuDNN | 12.4 / 9.1.0 |
| NumPy | 1.23.5 |
| Pillow | 10.4.0 |
| ImageIO | 2.35.1 |
| ImageIO-FFmpeg | 0.5.1 |

已验证：

- 隔离环境下 `pip check` 无 broken requirement；
- Safety-Gymnasium、MuJoCo、OmniSafe、RTAMT 和 PyTorch 可导入；
- `SafetyPointGoal1-v0` 可运行完整 1000-step horizon；
- PPO-Lagrangian 可以在 CPU 和 `cuda:0` 上构造并更新；
- EGL 离屏渲染、H.264 视频和 GLFW 实时窗口均可运行；
- ROS/Isaac 的全局 Python 路径不会污染 Python 3.8 实验环境。

完整记录见 [`environment_setup.md`](environment_setup.md)。

### 4.3 环境接口和距离信号检查

已确认环境接口为：

```text
reset -> observation, info
step  -> observation, reward, native_cost, terminated, truncated, info
```

已完成：

- observation/action shape 检查；
- reward 与 native cost 分开记录；
- `hazards_lidar` 字段定位；
- public distance 与 privileged simulator center distance 交叉验证；
- 3500 个样本上的最大重建误差约 `7.8e-16`；
- 随机和 scripted sample trajectory 保存；
- 环境渲染和视频证据保存。

完整记录见 [`environment_inspection.md`](environment_inspection.md)。

### 4.4 规则语义和参数校准

以下语义已经冻结：

- `d_t == d_warn` 不触发 warning；
- `d_t == d_safe` 算作 recovery；
- deadline sample `t_0 + K` 包含在允许窗口内；
- deadline 上恢复成功，下一步恢复算 late recovery；
- warning episode pending 时不会重复触发；
- pending obligation 遇到 environment termination/truncation 时标为
  `terminal_unresolved`；
- deadline violation 或 terminal unresolved 各产生一次 binary `stl_cost=1`；
- ordinary pending、recovery 和 violation 后的 overdue step 不重复产生 cost。

参数使用 30 条 controlled trajectory 和 30 条 random trajectory 校准。最终选择：

- `d_warn=0.45`；
- `d_safe=0.55`；
- recovery-time Q95 为 63 steps；
- `K=ceil(1.25*63)=79`；
- random-policy trigger rate 为 17/30，即 56.67%。

完整证据见 [`rule_calibration_report.md`](rule_calibration_report.md)。

### 4.5 Online monitor、offline oracle 和 RTAMT agreement

已经实现：

- public distance extractor；
- causal online bounded-recovery monitor；
- 不调用 online monitor 的 direct offline enumerator；
- RTAMT completed-window robustness evaluation；
- on-time、deadline violation、terminal unresolved fixtures；
- equality、deadline、late recovery、重复触发、vector independence 和 terminal
  boundary tests。

验证结果：

- 当前自动测试共 27 项，全部通过；
- online monitor 与 direct oracle 的 event-step mismatch 为 0；
- Boolean mismatch 和 cost mismatch 为 0；
- RTAMT 在 13 个 completed obligation window 上全部一致；
- 最大 robustness difference 为 0。

完整结果见 [`monitor_agreement_report.md`](monitor_agreement_report.md)。

### 4.6 一键实时和视频可视化

已经实现统一入口：

```bash
./scripts/visualize_stage1.sh
```

当前支持：

- `--render human`：MuJoCo 原生实时窗口；
- `--render video`：EGL 离屏渲染并生成 annotated H.264 MP4；
- `--render none`：无渲染端到端运行；
- `--policy scripted`：稳定产生 warning/recovery 的演示 controller；
- `--policy random`：使用固定 seed 的 random policy；
- 每次运行保存 trajectory CSV 和 summary JSON；
- reward、native cost 和 STL cost 始终分列记录；
- 实时画面显示距离、monitor state、remaining deadline 和 monitor event。

- 参考视频：[`stage1_demo.mp4`](../results/visualization/stage1_demo.mp4)
- 参考摘要：[`summary.json`](../results/visualization/summary.json)
- 使用说明：[`visualization.md`](visualization.md)

### 4.7 OmniSafe wrapper 与 integration smoke

已经实现三个注册环境：task-only、native-cost 和 STL-cost。所有条件共享原始
60 维 observation 加 3 维 temporal state，native reward 保持不变，native cost、
STL cost 和 selected learner cost 始终分开。

新增 11 项 wrapper 测试，完整测试总数为 38。真实 seed 44 positive-cost probe
在 100-step smoke horizon 上产生一次 terminal-unresolved，`stl_cost=1` 且
selected cost 为 1。随后 PPO-Lagrangian 使用两个 vector env 完成 64 transitions、
一个 epoch 和至少一次 update，并写出 checkpoint 与独立 cost metrics。

一键复现：

```bash
./scripts/run_omnisafe_smoke.sh
```

完整结果见 [`omnisafe_integration_report.md`](omnisafe_integration_report.md)。

### 4.8 Pre-main engineering gate

2026-08-11 已完成：

- 2000-transition PPOLag rollout，每个 vector slot 恰好一个完整 1000-step episode；
- 真实 actor rollout 中至少一次 deadline violation，mean STL/selected cost 均为 0.5；
- 强制 PPOLag config 显式声明 `lagrange_cfgs.cost_limit`；
- 统一 checkpoint evaluator，逐 episode 保存 task/native/STL 指标；
- 每条轨迹由 independent direct oracle 重新计算；
- completed windows 由 RTAMT 复核，3-episode smoke 最大 robustness difference 为 0；
- 新增 2 项 evaluator 测试。

该工程 gate 的完整证据见
[`pre_main_engineering_gate_report.md`](pre_main_engineering_gate_report.md)。

### 4.9 Pilot protocol freeze 和三条件 sanity

2026-08-11 负责人将 O6 批准为 Stage I pilot protocol，而不是最终 main-study
标准。已固定：主要 safety metric、30% 相对降低 pilot target、绝对差、baseline=0
处理、10 percentage-point goal margin、5 个 matched training seeds、每 seed/condition
100 个 paired evaluation episodes、10,000 次 paired hierarchical bootstrap、三个
不同单位的 cost limits，以及每 condition/seed 1M transitions 的 pilot budget。

随后完成每条件 10,000 transitions 的 task-only/native-cost/gold-STL engineering
sanity。三个条件的 cost routing 每个 epoch 都精确一致，positive native/STL cost
均实际出现，三个 final checkpoints 在同一组三条 deterministic evaluation 轨迹上
与 direct oracle 和 RTAMT 完全一致。完整测试总数现为 43。

该 sanity seed 不属于五个 pilot seeds，三条 evaluation 也远少于正式 100 条，不能
用于检验 30% target 或 goal non-inferiority。详细说明见
[`stage1_pilot_sanity_report.md`](stage1_pilot_sanity_report.md)。

## 5. 当前可视化的实际架构

当前可视化运行的是以下链路：

```text
scripted or random action
          |
          v
SafetyPointGoal1-v0
          |
          +------------------> native reward
          +------------------> native hazard cost
          |
          v
public flattened observation
          |
          v
hazards_lidar -> public distance d_t
          |
          v
BoundedRecoveryMonitor
          |
          +------------------> state / deadline / events
          +------------------> binary STL cost
          |
          v
MuJoCo overlay + CSV + JSON + optional MP4
```

这张图描述的是独立的 scripted visualization 路径；该演示本身不经过 OmniSafe
wrapper，也不包含策略更新或神经网络训练。项目中的 wrapper 和最小训练更新已在
后续独立 integration smoke 中通过，见第 9 节。

### 5.1 Scripted controller 的作用

默认演示 controller 会：

1. 选择 reset 时最近的 hazard；
2. 转向并靠近该 hazard；
3. 进入 warning zone 后继续到一个可见的近距离；
4. 沿原方向后退；
5. 在恢复到安全距离后结束演示。

controller 使用 privileged hazard geometry 是为了稳定地产生可观察事件。这个
privileged geometry 只参与演示动作生成，不进入 distance extractor 或 STL monitor。
因此该 controller：

- 不是学习得到的 policy；
- 不是实验对照条件；
- 不能用于报告 Safe RL 性能；
- 不能证明 agent 因为 STL cost 而学会了恢复。

### 5.2 参考运行的时间线

参考运行使用 `scripted` policy、seed 44，共 146 个 actions 和 147 个 samples。

| 时刻 | `d_t` | Monitor | 含义 |
|---:|---:|---|---|
| sample 0 | 0.894 | `INACTIVE` | 初始位于 warning zone 外 |
| sample 75 | 0.446 | `PENDING` | `d_t<0.45`，产生 warning trigger |
| sample 100 | 0.265 | `PENDING` | 正在后退恢复，距离仍未达到 0.55 |
| sample 130 | 0.550 | `INACTIVE` | 达到 `d_safe`，on-time recovery |
| sample 146 | >0.9 | `INACTIVE` | scripted demonstration 正常结束 |

trigger deadline 为：

```text
75 + 79 = sample 154
```

实际 recovery 在 sample 130，因此：

```text
recovery time = 130 - 75 = 55 steps
remaining deadline = 154 - 130 = 24 steps
```

该 episode 按时恢复，所以 `stl_cost_total=0`。

### 5.3 三个数值为什么不同

参考摘要中的主要累计量是：

| 指标 | 结果 | 解释 |
|---|---:|---|
| Episode return | `-0.0507` | benchmark 原生 task reward 累计值 |
| Native cost | `0` | 没有进入 benchmark 更近的即时 hazard-cost 区域 |
| STL cost | `0` | warning 后在 79 steps 内完成恢复 |
| Goal events | `0` | scripted 演示不以到达 goal 为目标 |
| Minimum public distance | `0.2569` | 本次轨迹最接近 hazard 的中心距离 |

`native_cost=0` 不等于“没有进入 STL warning zone”。两种 cost 表达不同概念：

- native cost 是 benchmark 的即时近距离 hazard cost；
- STL cost 是 warning episode 是否在 deadline 内完成恢复的 temporal event cost。

本次运行先触发 STL warning，但没有触发 native cost，并且按时恢复，所以两种 cost
最终都为 0。这证明日志能够区分它们，但不能证明其中一种比另一种更有效。

### 5.4 画面字段含义

| 字段 | 含义 |
|---|---|
| `Distance d_t` | 从公开 hazard lidar 得到的最近 hazard 中心距离 |
| `Monitor=INACTIVE` | 当前没有未完成 obligation |
| `Monitor=PENDING` | 已触发 warning，仍在允许恢复窗口内 |
| `Monitor=OVERDUE` | 已错过 deadline，等待 late recovery |
| `Remaining` | 当前 pending obligation 剩余 environment steps |
| `WARNING TRIGGER` | 新的 warning episode 开始 |
| `RECOVERY` | deadline 内达到 `d_safe` |
| `DEADLINE VIOLATION` | deadline sample 仍未恢复 |
| `TERMINAL UNRESOLVED` | environment 提前结束且 obligation 尚未完成 |
| `Native cost` | Safety-Gymnasium 原生累计 cost |
| `STL cost` | 当前规则产生的累计 binary event cost |

## 6. 当前结果能够证明什么

已经能够确认：

1. 选定 benchmark 和锁定软件环境可以运行；
2. public observation 足以定义 Stage I 距离信号；
3. distance extractor 不需要 privileged simulator state；
4. 固定 STL 语义可以被 online monitor 因果执行；
5. custom monitor、direct oracle 和 RTAMT 在声明范围内一致；
6. reward、native cost 和 STL cost 可以独立产生和记录；
7. simulator state、monitor state、日志和视频可以在同一 rollout 中对齐；
8. 实时和 headless 两种运行方式都可复现；
9. 三种条件具有相同的 augmented observation shape/dtype；
10. terminal final observation 会先完成 monitor 结算，再独立 reset 对应 vector slot；
11. 真实 positive-cost 路径能把 `stl_cost=1` 路由为 learner cost 1；
12. PPO-Lagrangian 能在该接口上完成一次最小 rollout/update 并写出 checkpoint。

## 7. 当前结果不能证明什么

当前结果不能用于声称：

- agent 已经通过训练学会 recovery；
- STL-cost condition 降低了 violation rate；
- goal success 或 episode return 得到保持；
- STL cost 优于 native cost；
- 训练或部署期间不会发生 violation；
- 当前方法提供 formal safety guarantee；
- 自然语言能够正确生成或 grounding 到 STL；
- 方法适用于动态 hazards、视觉输入、多 agent、UAV 或真实机器人。

## 8. 未完成的步骤

| 工作 | 状态 | 主要缺失内容 |
|---|---|---|
| STL safety-cost wrapper | 已完成 | 三种 cost selection、diagnostics、temporal state 已测试 |
| Vectorized monitor integration | 已完成 | final observation、独立 reset/state/terminal 已测试 |
| OmniSafe registration | 已完成 | 三个 condition ID，统一 `(63,)` float32 observation |
| PPO-Lagrangian integration smoke | 已完成 | 64 transitions、1 epoch、至少 1 update、checkpoint |
| PPOLag on-policy positive-cost sanity | 已完成 | 完整 episode rollout 中出现一次 deadline-event cost |
| Common checkpoint evaluator | 已完成 | direct oracle 与 RTAMT 检查、episode/aggregate 输出 |
| Quantitative pilot criteria | 已确认并冻结 | 仅限 Stage I pilot，不是最终 main-study 标准 |
| Condition-specific cost budgets | 已确认并冻结 | task/native/STL=`0/25/0.1`，单位不同 |
| Three-condition interface config | 已完成 | cost source 和共享 observation contract 已冻结 |
| Pilot matched configs | 已完成 | protocol 加三个 condition overlays 已冻结 |
| Three-condition small-budget sanity | 已完成 | 10k/condition，cost routing/checkpoint/gold evaluator gate 通过 |
| Resumable full-pilot runner | 已完成 | 15-job matrix、immutable attempts、hash、resume、immediate evaluation |
| Frozen pilot analysis | 已完成 | hierarchical bootstrap、zero-baseline、goal non-inferiority、curve review |
| Exact-scale throughput preflight | 已完成 | excluded 100k，335.68 transitions/s，90 MiB reserved VRAM |
| Full pilot RL training | 已完成 | 5 seeds × 3 conditions × 1M transitions；15/15 success |
| Evaluation and statistical report | 已完成 | 1,500 episodes、10,000 bootstrap、WP1 report 和四组图表 |
| Post-pilot code diagnosis | 已完成 | metric/objective、delayed credit、budget/optimizer、旧 checkpoint per-step replay 和机制图已分级记录 |
| P0 adapter/runtime audit | 已完成当前无训练范围 | executable timeout-bootstrap、advantage scaling、rolling window、discount、LR/lambda source/hash tests；未来 run 的 gradient/value logging 尚未执行 |
| GPU training environment | 已完成 | RTX 4090、Torch cu124、wrapper/PPOLag/full-horizon cost path 已验证 |
| Checkpoint visualization | 已完成诊断图 | 两组预先选定 case × 三条件的 per-step distance/event 图；未额外生成 MuJoCo rollout video |
| O8 final standard | 由 D38 的 bounded diagnostic 取代 | 不重跑旧 sparse-cost pilot；按新 C0/C1 learner-cost gate 执行 |
| Stage II benchmark | O7 设计已冻结、实现与人工 gate 待完成 | D37 固定 40 specifications、5 families、splits、models 和 admission gates；独立人工复核仍是 held-out release gate |

### 8.1 D36 无训练诊断与离线 benchmark 状态

15 个 final checkpoints 的 1,500 条 deterministic CPU replay 已完成，全部复现冻结
episode 表且 Gold/RTAMT checks 通过。Gold 相对 task-only 的 trigger frequency 只下降
1.16%，on-time recovery rate 下降 0.18 percentage point；positive event cost 只占
0.1724% action steps。当前失败符合 sparse/delayed credit、budget/objective mismatch 和
optimizer/runtime risk，但不能归因于单一 bug。完整表、两张图和 supported/rejected
explanations 见 [`stage1_trajectory_diagnosis_report.md`](stage1_trajectory_diagnosis_report.md)。

Stage II v0 历史机器基础包含 61 条统一 schema trajectories（55
synthetic、6 existing-policy real），9,208 samples，monitor/oracle/RTAMT 最大差异
0。D37 现已确认 final family、split、model 和 numerical gates，下一步是将该
5-item foundation 扩展为 40-specification benchmark。现有 5 条已由 Yuhang 人工复核
通过；未来 35 条尚未生成和审核，因此 held-out Gold labels 仍不得向 model
code 开放。详细执行要求见
[`STAGE2_CONTINUOUS_WORK_ORDER.md`](STAGE2_CONTINUOUS_WORK_ORDER.md)。

## 9. 已完成里程碑：OmniSafe wrapper 与 integration smoke test

该小而可诊断的集成里程碑已在 2026-08-10 完成；完整证据见
[`omnisafe_integration_report.md`](omnisafe_integration_report.md)。

### 9.1 Wrapper 已提供的接口

概念上，每一步需要同时保留：

```text
augmented_observation
native_reward
native_cost
stl_cost
selected_algorithm_cost
terminated
truncated
monitor diagnostics
```

其中：

- task reward 必须与原 benchmark 完全一致；
- `native_cost` 和 `stl_cost` 必须同时保存在日志中；
- 送入 learner 的 `selected_algorithm_cost` 根据实验条件选择；
- task-only condition 的 learner cost 为 0；
- native-cost condition 使用 native cost；
- STL-cost condition 使用 STL cost；
- 不允许覆盖或丢弃另一个 cost 的诊断值。

### 9.2 所有实验条件使用相同 temporal observation

原 observation 后必须追加：

```text
active_obligation
overdue_indicator
normalized_remaining_deadline
```

task-only、native-cost 和 STL-cost 三个条件都必须收到相同 augmented observation，
避免只有 STL condition 获得额外时间状态信息。

### 9.3 Vectorized 环境实现

每个 parallel environment 必须拥有独立的：

- monitor instance；
- sample index；
- warning episode id；
- trigger/deadline；
- violation/recovery counters；
- reset 和 terminal state。

一个 environment reset 或结束不能改变其他 environment 的 monitor。

### 9.4 新增测试

现已覆盖：

1. wrapper reset 后 temporal state 正确；
2. warning trigger 后 observation augmentation 正确；
3. recovery 后 active state 清零；
4. deadline violation 只产生一次 STL cost；
5. terminal unresolved 产生一次 conservative STL cost；
6. native reward 与 unwrapped environment 完全一致；
7. native cost 和 STL cost 不互相覆盖；
8. 三个 condition 的 observation shape/dtype 完全一致；
9. vectorized env 的 monitor state 相互独立；
10. OmniSafe reset/step API、device 和 tensor conversion 正确。

### 9.5 Integration smoke test 验收结果

短时 smoke test 已确认：

- OmniSafe 可以构造 wrapped `SafetyPointGoal1-v0`；
- PPO-Lagrangian 可以完成短 rollout 和至少一次 update；
- observation shape 和 dtype 在 reset/step/vectorization 中稳定；
- reward 与原环境逐步一致；
- learner 接收到的 cost 与选择的 condition 一致；
- 日志同时包含 native cost、STL cost 和 selected algorithm cost；
- terminal/truncated reset 不产生跨 episode monitor 污染；
- 无 NaN、shape mismatch、device mismatch 或 silent cost replacement；
- 保存最小 machine-readable smoke summary 和失败记录。

真实 positive-cost probe 产生 `stl_cost=1` 且 selected learner cost 同为 1。
PPO-Lagrangian 使用两个 vector env 完成 64 transitions、一个 epoch 和至少一次
update，记录均为有限值并写出 checkpoint。该 policy rollout 自身没有触发 warning，
所以其中三个 episode cost 指标均为 0；它只证明接口可运行，不用于报告 safety
improvement。

## 10. Full pilot 之后的顺序

以下八项现在均已完成：

1. 按 `docs/CURRENT_EXECUTION_DIRECTIVE.md` 实现可恢复的 15-job matrix runner；
2. 实现冻结的 paired hierarchical analysis 和自动测试；
3. 运行一个排除于 inference 的 100k exact-scale throughput preflight；
4. 生成包含 wall time、VRAM、disk、resume 和完整命令的 readiness report；
5. 在一次 full-pilot compute authorization 后连续运行 15 个训练 jobs；
6. 每个 fixed final checkpoint 立即执行 100 个 paired gold evaluations；
7. 完成 10,000 次 bootstrap、goal non-inferiority、learning-curve 检查和 WP1 report；
8. 准备 O8，并同步开始不需要 GPU 的 WP2/O7 benchmark-design proposal。

preflight 的 100k training 用时 297.90 秒，吞吐 335.68 transitions/s；10 条
evaluation 用时 17.21 秒；PyTorch peak reserved VRAM 为 90 MiB。完整 15 jobs 加
1,500 evaluations 线性估计约 13.13 小时、14.24 MB。54 项测试全部通过，所有 routing、
gold oracle 和 RTAMT checks 通过。pre-launch 详细证据见
[`stage1_pilot_launch_readiness.md`](stage1_pilot_launch_readiness.md)。

当前 CPU 历史路径和 RTX 4090 CUDA 路径都已验证；frozen pilot training device 为
`cuda:0`。完整 pilot 实际用时 8.97 小时。该段原有 O8/O7 等待状态已被
D37/D38 取代：现在按 continuous work order 执行 spatial replay、Stage II-A、
bounded Gold learner-cost diagnostic 和 gated Stage II-B，不重跑 D31 pilot。

pilot 后的代码级证据、已排除根因、P0 无 GPU 修复顺序和 O8-C 候选诊断设计见
[`stage1_code_failure_analysis_and_repair_recommendations.md`](stage1_code_failure_analysis_and_repair_recommendations.md)。
该文档是建议，不修改 D31，也不构成新增训练授权。

## 11. 当前可直接运行的命令

实时窗口：

```bash
./scripts/visualize_stage1.sh
```

生成 annotated video：

```bash
./scripts/visualize_stage1.sh --render video
```

无渲染运行：

```bash
./scripts/visualize_stage1.sh --render none
```

运行完整测试：

```bash
env PYTHONNOUSERSITE=1 PYTHONPATH=src MUJOCO_GL=egl \
  /home/jerry/anaconda3/envs/stl-stage1/bin/python \
  -m unittest discover -s tests -v
```

验证隔离环境依赖：

```bash
env PYTHONNOUSERSITE=1 PYTHONPATH= \
  /home/jerry/anaconda3/envs/stl-stage1/bin/python -m pip check
```

复现 OmniSafe integration smoke：

```bash
./scripts/run_omnisafe_smoke.sh
```

复现真实 on-policy positive-cost sanity：

```bash
./scripts/run_on_policy_sanity.sh
```

复现三条件 pilot sanity：

```bash
./scripts/run_stage1_pilot_sanity.sh
```

复现 CUDA gate：

```bash
./scripts/validate_cuda_stage1.sh
```

查看完整 15-job dry run：

```bash
./scripts/run_stage1_pilot.sh --dry-run
```

已完成 pilot 的历史启动/恢复入口（不要在 O8 前重新启动）：

```bash
./scripts/run_stage1_pilot.sh --authorized-full-pilot
./scripts/run_stage1_pilot.sh --authorized-full-pilot --resume
```

复现冻结分析和图表：

```bash
env PYTHONNOUSERSITE=1 PYTHONPATH=src MUJOCO_GL=egl \
  /home/jerry/anaconda3/envs/stl-stage1/bin/python scripts/analyze_stage1_pilot.py
env PYTHONNOUSERSITE=1 PYTHONPATH=src MUJOCO_GL=egl \
  /home/jerry/anaconda3/envs/stl-stage1/bin/python scripts/plot_stage1_pilot.py
```

统一评估 checkpoint：

```bash
./scripts/evaluate_stage1_checkpoint.sh \
  --run-dir PATH_TO_RUN --checkpoint epoch-N.pt \
  --episodes 100 --seed-start 10000 --max-episode-steps 1000 \
  --output-dir PATH_TO_OUTPUT
```

## 12. Git 状态和上传说明

当前 wrapper/integration milestone 的代码、文档和 tracked summary 位于工作树中。
上传前应先运行测试、检查 diff，并由仓库所有者提交。提交后，在已配置 GitHub
凭据的终端中执行：

```bash
cd /home/jerry/Desktop/STL
git push origin main
```

即可上传本地尚未同步的提交和 tracked MP4。上传前可用以下命令再次检查：

```bash
git status --short --branch
git log --oneline --decorate -10
```
