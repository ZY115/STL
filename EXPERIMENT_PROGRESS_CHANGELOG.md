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

截至 2026-08-12，Stage I 已经完成：

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
12. 最小 PPO-Lagrangian integration smoke；
13. 完整 episode 对齐的 PPOLag on-policy positive-cost sanity；
14. 统一 checkpoint evaluator、independent oracle 与 RTAMT gate；
15. O6 Stage I pilot protocol 确认与冻结；
16. 三条件 10k transitions/condition matched engineering sanity；
17. 可恢复 15-job matrix runner 和冻结 paired hierarchical analysis；
18. 54 项完整测试；
19. excluded 100k exact-scale CUDA preflight 与 launch-readiness report；
20. 15-job、15M-transition full pilot 和 1,500 条 paired evaluations；
21. 10,000 次 frozen hierarchical bootstrap、learning-curve review 和 WP1 report；
22. 四组 PNG/SVG 图表、O8 final-standard proposal 和 O7 benchmark proposal。

当前结论是：gold-STL cost 在冻结 pilot 下没有改善 primary missed-per-trigger
metric；goal-success non-inferiority 通过；约束 cost/multiplier 未稳定，因此不能声称
收敛。更多 GPU 工作等待 O8。

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
| 2026-08-11 | Pre-main engineering gate | 完成 | on-policy event cost、checkpoint evaluator、oracle/RTAMT evidence |
| 2026-08-11 | Stage I pilot protocol | 已确认 | D31；仅限 pilot，不是最终 main-study 标准 |
| 2026-08-11 | Three-condition pilot sanity | 完成 | frozen composition、cost routing、final checkpoints、paired gold evaluation |
| 2026-08-11 | Full-pilot launch preparation | 完成 | runner、analysis、tests、100k preflight、readiness report |
| 2026-08-12 | Full matched pilot and WP1 report | 完成 | 15M transitions、1,500 evaluations、bootstrap、figures、negative result |

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

### 9.1 Pilot 后仍需决定

O6 已由 D31 确认为 pilot protocol。O8 仍需在 pilot learning curves 和 feasibility
证据之后决定最终 main-study training budget、seed 数、evaluation 数、uncertainty
方案和是否需要预声明 budget sweep。不能把 pilot 设置自动称为最终标准。

### 9.2 尚未实施

- O8 final-main-study standard 决定及其可能的 bounded diagnostic；
- 训练后 policy 可视化；
- Stage II controlled-language layer。

## 10. 下一步

full pilot、analysis 和 report 已完成。下一 compute gate 是负责人审阅
`docs/stage1_o8_main_study_decision_proposal.md` 并选择 close、longer same-method 或
bounded diagnostic。下一 non-compute gate 是审阅
`docs/stage2_o7_benchmark_design_proposal.md`；在 O7 冻结前不实现语言模型。

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

## 13. 2026-08-11 Pre-main engineering gate

### 13.1 修改目的

根据更新后的 handoff，先补齐 O6 预声明提案、真实 PPOLag rollout 内的 nonzero STL
event cost 和统一 gold-oracle checkpoint evaluator；不启动 matched main training。

### 13.2 研究决定状态

新增 `docs/stage1_pre_main_study_proposal.md` 和
`configs/stage1_pre_main_proposal.yaml`。其中 30% safety reduction、10 percentage-
point goal margin、5 个 training seeds、每 seed 100 个 evaluation episodes、paired
hierarchical bootstrap、condition-specific budgets 和 1M-transition budget 均明确标为
`proposed_not_confirmed`。O6 仍为 blocking open decision。

### 13.3 工程修改

- PPOLag runner 现在强制显式提供 `lagrange_cfgs.cost_limit`；
- 新增 `configs/on_policy_positive_cost_sanity.yaml` 和一键运行脚本；
- 新增 `src/safety_stl/evaluation.py` 和 checkpoint evaluator；
- evaluator 保存 return、goal、native cost、gold STL events，并逐轨迹调用 independent
  oracle，对 completed windows 调用 RTAMT；
- 新增两项 evaluation tests；
- 新增 pre-main engineering report 和两个 tracked result summaries。

### 13.4 验证结果

2000-transition PPOLag sanity 使用两个完整 1000-step episodes。至少一条真实 actor
rollout 产生 deadline violation；mean `STLCost=0.5`，mean selected cost 同为 0.5，
Lagrange multiplier 更新到约 0.036。三条 checkpoint-evaluation smoke trajectories 的
online/direct-oracle mismatch 为 0，三个 RTAMT completed windows 的最大 robustness
difference 为 0。

这些结果只完成工程 gate，不表示 policy 已学会安全恢复。随后 D31 已确认 pilot
protocol，三条件 configs 和 small-budget sanity 的完成情况见第 14 节。

## 14. 2026-08-11 Pilot protocol freeze 与三条件 sanity

### 14.1 决定与统计口径

负责人批准 O6 为 Stage I pilot protocol，但不是最终 main-study 标准。D31 固定：

- primary safety metric = missed recovery obligations / triggered obligations；
- primary comparison = gold-STL cost vs task-only；
- 至少 30% relative reduction pilot target，同时报告 absolute difference；
- task-only baseline rate 为 0 时 relative reduction 无定义，只用 absolute difference；
- 10 percentage-point goal-success non-inferiority margin；
- 5 matched training seeds、每 seed/condition 100 paired evaluation episodes；
- 10,000 paired hierarchical bootstrap replicates；
- task/native/STL cost limits = `0.0/25.0/0.1`，且 native/STL 单位不同；
- 1M transitions/condition/seed 仅是 pilot budget，必须检查 learning curves。

### 14.2 新增工程内容

- 新增 `configs/stage1_pilot/protocol.yaml` 和三个 frozen condition overlays；
- 新增 `src/safety_stl/pilot_protocol.py`，对 D31 数值和解释边界做机器校验；
- 新增 `configs/stage1_pilot_sanity.yaml` 和一键 runner；
- 新增三个 protocol tests；完整自动测试为 43 项；
- evaluator 新增 canonical `missed_recovery_obligation` rate，同时保留旧 diagnostic alias；
- 新增 `docs/stage1_pilot_sanity_report.md` 和 compact tracked evidence。

### 14.3 Sanity 验证结果

使用明确排除于 pilot inference 的 seed `20260811`，三个条件各运行 10,000
transitions。每个 epoch 的每个 vector slot 恰好 1000 steps；三个条件均生成 final
`epoch-5.pt`。task-only selected cost 恒为 0，native selected cost 与 native cost
逐 epoch 相等，STL selected cost 与 STL event cost 逐 epoch 相等。positive native
cost 和 positive STL event cost 均实际出现。

三个 final checkpoint 使用相同 deterministic mode 和 seeds `13000--13002`。所有
轨迹的 online/direct-oracle agreement 为 true，RTAMT 最大 robustness difference 为
0。gate 通过，完整 1M runs 没有启动。

该 run 只验证工程链路。10k transitions 和 3 个 evaluation episodes 不能检验 30%
target、goal non-inferiority 或收敛。下一步是冻结协议下的 full Stage I pilot，随后
检查 learning curves，并通过 O8 决定最终 main-study 标准。

## 15. 2026-08-11 CUDA enablement

### 15.1 根因与环境修改

机器的 RTX 4090 和 NVIDIA driver 560.35.03 正常；此前不能使用 GPU 的直接原因是
`stl-stage1` 安装了 `torch 2.4.1+cpu`。现已用官方 CUDA 12.4 wheel 替换为
`torch 2.4.1+cu124`，并在 lock file 中加入精确 NVIDIA runtime/cuDNN/Triton 依赖。
安装器临时选择的 `typing-extensions 4.12.2` 与 `cryptography` 冲突，已恢复原锁定的
4.13.2；最终 `pip check` 无 broken requirements。

### 15.2 新增验证与决定

- D32 固定 Stage I pilot training backend 为 `cuda:0`；
- 新增 `configs/cuda_validation.yaml`；
- 新增 `scripts/validate_cuda_stage1.py/.sh`；
- 新增 `docs/cuda_enablement_report.md`；
- 新增 `results/cuda_validation/summary.json` compact evidence；
- CUDA launcher 固定 `CUBLAS_WORKSPACE_CONFIG=:4096:8`，满足 OmniSafe/PyTorch
  deterministic algorithm 要求。

### 15.3 验证结果

- Torch 识别 RTX 4090、24,564 MiB、compute capability 8.9；
- PyTorch CUDA runtime 12.4、cuDNN 9.1.0；
- 1024×1024 CPU/GPU matrix max absolute difference `0.0002365 < 0.001`；
- Stage I observation/reward/native/STL/selected-cost tensors 全部位于 `cuda:0`；
- 2000-transition full-horizon PPOLag CUDA update 产生 mean STL/selected cost 0.5，
  multiplier 更新并保存 checkpoint；
- 三条件 10k sanity 在 `cuda:0` 重跑，全部 gate 通过；
- full 1M pilot 未启动。

CUDA 功能已经解决。由于小网络和模拟器开销，当前 sanity 不能证明 GPU 比 CPU 更快；
完整 pilot 前应单独记录 representative throughput。

## 16. 2026-08-11 连续执行指令与 handoff 修正

审查发现，长期 pipeline 已经完整，但 `AGENTS.md` 和 D31 同时要求 sanity 之后不要
自动启动 full pilot。工作电脑按较强的 stop gate 停止是合理行为；问题在于仓库没有
把 stop gate 之前可以连续完成的工作定义成一个整体。

新增 `docs/CURRENT_EXECUTION_DIRECTIVE.md` 和 D33，现将本轮工作划分为：

1. 无需再次确认、必须连续完成：resumable 15-job runner、frozen hierarchical
   analysis、tests、一个 excluded 100k exact-scale preflight 和 readiness report；
2. 只需一次明确批准：预计约 15M transitions 的 full pilot compute gate；
3. 批准后连续完成：15 runs、1,500 paired evaluations、analysis、WP1 report、O8
   proposal 和非 GPU 的 WP2/O7 benchmark-design proposal。

该修改不改变 D31 scientific protocol、D32 CUDA backend 或 STL semantics，只修正
项目执行和 handoff 粒度。

## 17. 2026-08-11 Full-pilot execution preparation 与 exact-scale preflight

### 17.1 Runner 与 manifest contract

- 新增 `src/safety_stl/pilot_runner.py` 和 `scripts/run_stage1_pilot.py/.sh`；
- 固定 3 conditions × 5 seeds 的 condition-major 顺序；
- 支持 dry-run、condition/seed selection、resume、train-only 和 evaluate-only；
- 每个 attempt 独立保存，不覆盖成功结果；
- 只有 Git/source/config/checkpoint/progress/evaluation hashes 全部匹配时，resume 才
  跳过成功 job；
- 每个 job 使用 fixed final checkpoint 并立即完成 100 paired evaluation；
- 未提供 `--authorized-full-pilot` 时，runner 拒绝启动正式 pilot。

### 17.2 冻结统计分析

- 新增 `src/safety_stl/pilot_analysis.py` 和 `scripts/analyze_stage1_pilot.py`；
- 要求完整 15-job matrix，保留 per-seed 与 per-episode records；
- 实现 pooled missed obligations per trigger、task-zero fallback、absolute/relative
  reduction、deadline/terminal 分项和 goal non-inferiority；
- 实现固定 RNG seed 的 10,000 次 paired hierarchical percentile bootstrap；
- N/A 不替换为 0；learning curves 只做 descriptive review，不声称收敛。

### 17.3 测试与 preflight

新增 11 项 runner/analysis 聚焦测试，完整 suite 从 43 增至 54 项并全部通过。
`pip check`、YAML parsing、Python compile、shell syntax 和 dry-run 15-job count 通过。

excluded preflight 使用 seed `20260811`、`gold_stl_cost`、10 vector envs、10,000
steps/epoch、100,000 transitions 和 10 条 excluded evaluations。成功 attempt 的训练
时长为 297.90 秒，吞吐为 335.68 transitions/s，PyTorch peak reserved VRAM 为
90 MiB；gold-oracle 全部一致，RTAMT 最大 difference 为 0。线性估计完整 package
约 13.13 小时和 14.24 MB。

前两个 attempt 因 memory-stat device 参数和 custom environment 未显式注册而在
rollout 前失败，执行 transition 数为 0；问题修复后 attempt 3 完成。随后
`--resume` 返回 `skipped_verified_success`。

### 17.4 当前 gate

新增 `docs/stage1_pilot_launch_readiness.md` 和 compact
`results/pilot_preflight/` evidence。完整 15M pilot 没有启动。当前只等待一次明确的
compute authorization；本次工作不改变冻结协议，也不构成行为或收敛结论。

## 18. 2026-08-12 Full pilot、冻结分析与 WP1 报告

### 18.1 执行完成

负责人明确批准后，可恢复 runner 顺序完成 task-only、native-cost 和 gold-STL-cost
各五个 seed。15/15 jobs 成功、failure manifest 为 0；总计 15M training transitions
和 1,500 条 deterministic paired final-checkpoint evaluations。所有 checkpoint、
progress、evaluation artifact hash 通过，online/direct oracle 全部一致，RTAMT 最大
difference 为 0。

### 18.2 冻结统计结果

D31 的 10,000 次 paired hierarchical bootstrap 使用固定 RNG seed `20260811`。
task-only/gold-STL missed-per-trigger 为 `25.85%/26.03%`；relative reduction 为
`-0.71%`，95% interval `[-24.92%, +21.88%]`，因此 30% target 未达到。两者 goal
success 都是 100%，10 percentage-point non-inferiority 通过。

### 18.3 Learning-curve 结论

gold-STL final-20 selected cost 为 `1.650` missed events/episode，对应 limit 为
`0.1`；multiplier 均值为 `3.217` 且四个 seed 有 tail drift。native cost 同样保持在
自己的不同单位预算之上。1M budget 不作收敛声明，也不选择 post-hoc best checkpoint。

### 18.4 新增产物

- `docs/stage1_pilot_result_report.md`：正式 WP1 结果、限制和解释；
- `scripts/plot_stage1_pilot.py`：可复现 PNG/SVG 图表入口；
- `results/stage1_pilot/analysis/`：analysis JSON/CSV、bootstrap、图和 hash manifest；
- `docs/stage1_o8_main_study_decision_proposal.md`：close/longer/diagnostic 三选项；
- `docs/stage2_o7_benchmark_design_proposal.md`：Stage II non-compute schema proposal。

### 18.5 当前 gate

O8 尚未决议，当前不启动更多 GPU training。O7 proposal 已准备，但 formula fragment、
dataset composition、split、baseline 和 numerical offline gate 仍需负责人确认。

## 19. 2026-08-12 Pilot 后代码失败分析与修复建议

### 19.1 分析结论

新增 `docs/stage1_code_failure_analysis_and_repair_recommendations.md`。该文档把
monitor/oracle 的语义正确性与 learner 的策略学习有效性分开，并记录：

- 当前 PPOLag 优化 missed events/episode，而 frozen primary metric 是
  missed/trigger；trigger 分母随 policy 改变，因此两者不等价；
- binary STL event 只在 `K=79` deadline 或 terminal unresolved 时出现，训练后段
  正 cost 约占 0.165% steps，存在显著 delayed-credit 问题；
- `cost_limit=0.1 event/episode` 与 30% primary relative-reduction target 处于明显
  不同尺度，不能把二者视为等价标准；
- multiplier 在训练后段才达到明显量级，而 linear actor LR 同时衰减至零，且多数
  epochs 受到 KL early stop；
- OmniSafe 0.5.0 的实际 on-policy 行为包括：cost advantage 只去均值、EpCost
  window 硬编码为 50、该 buffer 路径未读取 `cost_gamma`；
- terminal unresolved 已在 monitor 中结算，但 timeout path 仍从 active final state
  bootstrap cost value，构成本项目 episode-cost 语义风险，实际影响仍需隔离测试。

### 19.2 建议顺序

1. P0 无 GPU：补 truncation/bootstrap regression、effective-runtime contract 和
   advantage/gradient/value diagnostics；
2. O8-C 获批后：依次运行 bounded optimization、event-budget 和一个
   mass-conserving post-rollout credit-redistribution diagnostic；
3. 通过预声明 gate 后：使用新的五个 matched seeds 从头运行确认性实验。

建议不修改 gold monitor 和 evaluator，不 patch Conda `site-packages`，不续跑 LR 已到
零的 pilot checkpoint。raw gold event 与 learner shaping 必须分列保存，最终仍用
unchanged gold oracle 评价。

### 19.3 决策与权限状态

本次只新增诊断文档和索引记录，没有修改 D31、没有冻结任何 O8 参数、没有运行新的
GPU training。O8-A/B/C 仍等待负责人明确决定。
