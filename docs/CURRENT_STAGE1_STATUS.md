# Stage I 当前状态、可视化含义与下一步工作

## 1. 文档目的

本文档记录截至 2026-08-10 的 Stage I 完整状态，集中回答四个问题：

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

当前只实施 Stage I。其研究问题是：

> 在一个已知静态障碍的简单导航环境中，一条人工确认正确的 bounded-recovery
> STL 规则能否被正确监测并转换成 Safe RL cost，从而减少超时恢复失败，同时
> 不造成不可接受的目标完成能力下降？

目前已经完成环境、信号、规则、参数、monitor、reference agreement、可视化、
STL-cost wrapper 和一次最小 OmniSafe update；尚未完成 matched-seed 对照训练和
正式 evaluation。因此目前仍没有 RL 安全改进结论。

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
| PyTorch | 2.4.1+cpu |
| NumPy | 1.23.5 |
| Pillow | 10.4.0 |
| ImageIO | 2.35.1 |
| ImageIO-FFmpeg | 0.5.1 |

已验证：

- 隔离环境下 `pip check` 无 broken requirement；
- Safety-Gymnasium、MuJoCo、OmniSafe、RTAMT 和 PyTorch 可导入；
- `SafetyPointGoal1-v0` 可运行完整 1000-step horizon；
- PPO-Lagrangian 对象可以在 CPU 上构造；
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
| Quantitative success criteria | 未决定 | violation reduction、goal tolerance、seeds、episodes、uncertainty |
| Condition-specific cost budgets | 未决定 | native step cost 与 STL event cost 不能静默共用默认 numeric limit |
| Three-condition interface config | 已完成 | cost source 和共享 observation contract 已冻结 |
| Main-study matched configs | 未开始 | 等待 quantitative success/evaluation 决策 |
| Main RL training | 未开始 | matched seeds 的正式训练 |
| Evaluation and statistical report | 未开始 | violation、recovery、goal、return、cost、uncertainty |
| GPU training environment | 未完成 | 当前 PyTorch 为 CPU build，NVIDIA driver/CUDA 尚未验证 |
| Checkpoint visualization | 未开始 | 当前入口还不能加载训练后的 OmniSafe policy |
| Stage II language layer | 延后 | controlled NL-to-STL translation 与 grounding |

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

## 10. Integration gate 通过后的顺序

只有 wrapper/integration gate 通过后，才按以下顺序继续：

1. 在 `DECISIONS.md` 预声明 quantitative success criterion；
2. 固定 violation reduction threshold；
3. 固定允许的 goal-success/return degradation；
4. 固定训练 seeds、evaluation episodes 和 uncertainty 方法；
5. 建立 task-only、native-cost、STL-cost 三个 matched configs；
6. 先做小预算 sanity run；
7. 再决定是否重建 CUDA PyTorch/GPU 训练环境；
8. 运行正式 matched-seed training；
9. 使用统一 evaluation runner 比较 temporal violations 和 goal performance；
10. 只有 Stage I 下游链路得到可解释结果后，才进入 Stage II language layer。

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
