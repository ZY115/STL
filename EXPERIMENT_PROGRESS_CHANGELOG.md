# Stage I 实验进度与修改记录

## 1. 文件用途

本文档独立记录 Language-Grounded STL for Safe RL 项目 Stage I 的工程进度和修改
历史，用于回答：

- 当前已经完成到哪一步；
- 每个里程碑新增或修改了什么；
- 为什么进行这些修改；
- 哪些接口和工程约束已经冻结；
- 当前还缺什么；
- 下一次工作应该从哪里继续。

本文档不是实验数据仓库，不保存或复制：

- raw trajectory CSV；
- 视频帧或模型 checkpoint；
- 正式训练曲线；
- per-seed performance 数据；
- 用于论文结论的统计结果。

实验配置、数据摘要和机器可读证据仍分别保存在 `configs/`、`results/` 和专项报告
中。本文只记录进度、工程变化和验证状态。

## 2. 当前总体状态

截至 2026-08-10，Stage I 已经完成：

1. 研究问题定义与三阶段拆分；
2. Ubuntu/Conda 软件环境建立和复核；
3. `SafetyPointGoal1-v0` 环境与公开 observation 接口检查；
4. hazard distance signal 定义；
5. 单条 bounded-recovery STL 规则语义冻结；
6. 参数校准流程；
7. online monitor、offline oracle 和 RTAMT agreement；
8. 实时窗口、headless 和录像可视化；
9. OmniSafe-compatible wrapper；
10. task-only、native-cost、STL-cost 三种 cost-routing 条件；
11. vectorized monitor 生命周期与 terminal/final-observation 处理；
12. 最小 PPO-Lagrangian integration smoke。

当前尚未开始 matched-seed 主训练，也没有形成 STL-cost condition 能改善安全行为的
实验结论。

## 3. 里程碑时间线

| 日期 | 里程碑 | 状态 | 主要工程产物 |
|---|---|---|---|
| 2026-07-29 | 环境建立与 inspection | 完成 | 环境锁文件、setup/inspection 文档、样例生成流程 |
| 2026-08-05 | 规则语义与参数校准 | 完成 | normative rule specification、固定配置、校准脚本 |
| 2026-08-05 | Monitor completion gate | 完成 | signal extractor、online monitor、offline oracle、fixtures、agreement checks |
| 2026-08-05 | 可视化入口 | 完成 | 一键实时/视频 launcher、overlay、CSV/JSON 日志 |
| 2026-08-10 | 仓库更新审计 | 完成 | 新增进度 slides 已读取；固定 Stage I 研究范围未改变 |
| 2026-08-10 | OmniSafe wrapper | 完成 | 三个注册环境、统一 temporal observation、独立 cost routing |
| 2026-08-10 | Integration smoke gate | 完成 | 一键 smoke runner、wrapper tests、机器可读 completion summary |
| 待定 | 主实验预声明 | 未完成 | 成功门槛、seeds、evaluation episodes、uncertainty 方法 |
| 待定 | Matched sanity/main training | 未开始 | 三条件训练配置、checkpoint、统一 evaluation |

## 4. 已冻结且未被本次修改改变的研究定义

- Application：二维 Point agent 绕静态 hazards 导航；
- Benchmark：`SafetyPointGoal1-v0`；
- Task objective：保留 benchmark 原生 goal-reaching reward；
- Safety signal：由公开 `hazards_lidar` 重建最近 hazard 中心距离；
- Rule family：单条 hysteretic bounded-recovery STL rule；
- Safe RL framework：OmniSafe；
- Initial constrained algorithm：PPO-Lagrangian；
- Reference monitor：RTAMT；
- native hazard cost 和 STL-derived cost 始终独立；
- Stage I 不加入自然语言模型、视觉感知、动态障碍、shielding 或多规则族。

规则的数值和完整边界语义只以 `configs/stage1_rule.yaml` 和
`docs/stage1_rule_monitor_spec.md` 为准。

## 5. 2026-08-10 仓库更新审计

更新提交主要增加了可编辑和发布版 Stage I 当前进度 slides，并同步 README、
MANIFEST 和校验和。审计结论：

- 长期研究目标未改变；
- Stage I scope 未扩大；
- 固定 benchmark、signal、rule、monitor 和 cost 语义未改变；
- 文档明确把 OmniSafe wrapper 与 integration smoke 指定为下一工程里程碑；
- 主 RL study 仍需等待定量成功标准预声明。

新 slides 记录的是 wrapper 开始前的进度快照。wrapper 完成后的最新状态以 README、
`docs/CURRENT_STAGE1_STATUS.md`、本文件和 integration report 为准。

## 6. 2026-08-10 OmniSafe wrapper 修改记录

### 6.1 新增三种注册环境

新增三个 OmniSafe environment ID：

```text
Stage1SafetyPointGoal1TaskOnly-v0
Stage1SafetyPointGoal1NativeCost-v0
Stage1SafetyPointGoal1STLCost-v0
```

它们复用相同 benchmark、reward、monitor 和 observation contract，只改变送入 learner
的 selected algorithm cost。

### 6.2 Cost routing

wrapper 在每一步同时保留：

```text
native_reward
native_cost
stl_cost
selected_algorithm_cost
```

路由规则为：

- task-only：selected cost 为零；
- native-cost：selected cost 等于 native cost；
- STL-cost：selected cost 等于 STL cost。

任何条件都不能覆盖或丢弃另外两个 cost diagnostic。

### 6.3 Policy observation

所有条件在原始 public observation 后追加完全相同的 temporal state：

```text
active_obligation
overdue_indicator
normalized_remaining_deadline
```

这样既避免 temporal cost 对 policy 构成隐藏状态，也避免只给 STL 条件额外信息。

### 6.4 Terminal 与 vectorized reset

Safety-Gymnasium vector env 在 episode 结束时会返回下一 episode 的 reset observation，
真正的最后一个 sample 位于 `info["final_observation"]`。wrapper 现在按以下顺序处理：

1. 先用 final observation 结算当前 monitor；
2. 处理 deadline violation 或 terminal unresolved；
3. 保存 augmented final observation；
4. 产生当前 transition 的 STL/selected cost；
5. 再从 auto-reset observation 重置对应 vector slot 的 monitor；
6. 其他 vector slot 不受影响。

该顺序避免把新 episode 的 reset observation 错当成旧 episode 的终止 sample。

### 6.5 OmniSafe rollout 对齐约束

OmniSafe 0.5.0 会在每个 on-policy rollout epoch 开始时 reset adapter。为了避免 epoch
边界清除未完成 obligation，训练配置必须满足：

```text
steps_per_epoch / vector_env_nums
```

是完整 episode horizon 的整数倍。smoke runner 已显式检查这一约束；未来 main
configuration 也必须保留。

## 7. 新增和修改的工程文件

### 新增代码与配置

| 文件 | 修改目的 |
|---|---|
| `src/safety_stl/omnisafe_env.py` | OmniSafe 注册、三种 cost mode、temporal observation、vector monitor lifecycle |
| `configs/omnisafe_integration_smoke.yaml` | 三条件接口定义与 bounded smoke 配置 |
| `scripts/run_omnisafe_integration_smoke.py` | 运行真实 cost-routing probe 和最小 PPO-Lagrangian update |
| `scripts/run_omnisafe_smoke.sh` | 自动选择 `stl-stage1` Conda 环境的一键入口 |
| `tests/test_omnisafe_wrapper.py` | wrapper reset/step/cost/terminal/vector/logging contract tests |

### 新增进度与证据文档

| 文件 | 修改目的 |
|---|---|
| `docs/omnisafe_integration_report.md` | wrapper 架构、验证范围、限制和复现命令 |
| `results/integration_smoke/README.md` | 说明 tracked summary 与 ignored bulk outputs 的边界 |
| `results/integration_smoke/summary.json` | machine-readable completion record，不替代正式实验数据 |
| `EXPERIMENT_PROGRESS_CHANGELOG.md` | 独立进度与修改记录，即本文档 |

### 同步更新的既有文件

| 文件 | 修改内容 |
|---|---|
| `README.md` | 当前状态、下一 gate、目录结构和 smoke 启动命令 |
| `PROJECT_CONTEXT.md` | 当前 implementation status |
| `DECISIONS.md` | 新增 wrapper/integration completion decision |
| `AGENTS.md` | immediate task 改为主实验预声明 |
| `HANDOFF_PROMPT.md` | 新 session 从 pre-main-study gate 继续 |
| `MANIFEST.md` | 新代码、文档和结果摘要登记 |
| `docs/CURRENT_STAGE1_STATUS.md` | 完成/未完成状态和下一步 |
| `docs/PROJECT_INTRODUCTION.md` | 中英文项目进度 |
| `docs/environment_setup.md` | wrapper smoke 的复现环境说明 |
| `docs/stage1_plan.md` | Work Package 4/5 状态 |
| `pyproject.toml` | 声明 OmniSafe 和 PyTorch runtime dependencies |
| `results/.gitignore` | 只追踪 smoke summary/README，忽略 bulk logs/checkpoints |
| `CHECKSUMS.sha256` | 登记当前 packaged files 的完整性 hash |

## 8. 验证状态

已完成的工程验证包括：

- 完整自动测试 suite 通过；
- wrapper-specific reset、recovery、deadline、terminal 和 vector tests 通过；
- 三种 condition 的 observation shape/dtype 一致；
- real environment reward/native-cost passthrough 检查通过；
- real positive STL-cost routing path 通过；
- PPO-Lagrangian 完成 bounded rollout 和至少一次 update；
- 独立 cost metrics 和 checkpoint 写出；
- editable package metadata 已刷新；
- `pip check` 无 broken requirement；
- repository checksum verification 通过。

具体数值、运行 hash 和 machine-readable evidence 不在本文重复，见：

```text
docs/omnisafe_integration_report.md
results/integration_smoke/summary.json
```

## 9. 当前未完成事项

### 9.1 必须在主训练前决定

Open decision O6 仍未关闭：

- temporal violation reduction 的成功门槛；
- goal success 或 episode return 的允许下降范围；
- matched training seeds；
- 每个 checkpoint/condition 的 evaluation episode 数；
- uncertainty interval 和统计汇报方法；
- native step cost 与 STL event cost 各自的 `cost_limit` 和预算语义；
- PPO-Lagrangian rollout 内的 positive-cost sanity；
- 所有 policy 共用的 gold-STL offline evaluation oracle。

这些选择会直接改变正式实验的规模和结论，不应由实现过程静默决定。

### 9.2 尚未实施

- main-study task-only/native-cost/STL-cost matched configs；
- 小预算 sanity training；
- 正式 matched-seed training；
- 统一 checkpoint evaluation runner；
- 训练后 policy 可视化；
- GPU/CUDA 训练环境恢复；
- Stage II controlled-language layer。

## 10. 下一步

下一里程碑是主实验预声明，而不是直接启动长时间训练：

1. 提出 O6 的明确候选值；
2. 将“建议值”和“已确认值”分开记录；
3. 获得确认后更新 `DECISIONS.md`；
4. 冻结三个 matched configs；
5. 检查 rollout/horizon alignment；
6. 先运行小预算 sanity training；
7. sanity gate 通过后，再决定 CPU 或修复后的 GPU 主训练路径。

## 11. 维护规则

以后每次完成里程碑，应在本文末尾追加一条记录，至少包含：

- 日期；
- 里程碑名称；
- 修改目的；
- 新增/修改文件；
- 验证状态；
- 已知限制；
- 下一 gate。

不要在本文粘贴 raw data、完整训练表格或大段终端输出。实验数据和统计结论应继续
保存在 `results/` 及对应专项报告中。

## 12. 2026-08-10 长期 pipeline 与独立 handoff 补全

新增 `docs/END_TO_END_RESEARCH_PIPELINE.md`，用于解决原 handoff 只强调当前
milestone、完成后仍需重新询问研究方向的问题。新文档现已统一记录：

- 原始目标和两次研究定位修改；
- benchmark 的控制变量角色；
- Stage I controls 与真正 language-method baselines 的区别；
- candidate formal pipeline 的可解释假设和当前 novelty 边界；
- WP1--WP7 的 inputs、outputs、gates 和预设 failure branches；
- 参考论文、本地路径、当前状态和后续维护规则。

同时更新 `AGENTS.md`、`README.md`、`HANDOFF_PROMPT.md`、`DECISIONS.md`、
`PROJECT_CONTEXT.md` 和 `MANIFEST.md`，使新的 Codex session 必须先读取长期路线，
并在完成当前 gate 后继续下一个未完成 work package。
