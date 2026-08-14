# Safety STL Project Handoff

## 项目用途

该文件夹是 Language-Grounded STL for Safe RL 项目的可迁移研究记录。

它用于解决一个实际问题：当项目被移动到另一台 Ubuntu 电脑、由另一个 Codex 账号继续时，不依赖原聊天记录或账号 memory，也能准确理解当前研究目标、已经做出的决定、Stage I 的实验计划和下一步工作。

长期研究路线、对照方法、每个阶段的输入输出、通过标准和预设结果分支统一见
`docs/END_TO_END_RESEARCH_PIPELINE.md`。新电脑不能只读取“下一步”；完成当前 gate
后，应按该文档继续进入下一个未完成 work package。

当前被授权连续完成的工程范围、唯一需要暂停的 compute gate 和 gate 之后的自动
续接顺序见 `docs/CURRENT_EXECUTION_DIRECTIVE.md`。长期 pipeline 说明“去哪里”，
current directive 说明“本轮连续做到哪里”。

该文件夹包含研究规划、参考资料、可复现环境记录、参数校准证据、已经验证的
STL monitor/oracle、OmniSafe wrapper、integration smoke、冻结的 Stage I pilot
protocol、三条件 sanity、可恢复 15-job runner、完整 15M-transition pilot、冻结
统计分析、四组结果图表和 WP1 正式报告，以及一条命令启动的实时/录像可视化入口。

## 长期研究目标

长期目标是建立如下链路：

```text
Natural-language task
        ->
separate task objective and safety requirement
        ->
ground language to measurable signals and values
        ->
generate an STL specification
        ->
monitor trajectories and generate a safety cost
        ->
train and evaluate a Safe RL agent
```

这里的 STL 公式不会作为字符串直接输入 RL。STL monitor 对环境轨迹进行判断，并将 violation、satisfaction 或 robustness 转换为 Safe RL 可使用的 cost。

## 当前研究阶段

完整研究被拆分为三个阶段：

1. **Stage I: Gold-STL experiment**  
   暂时移除自然语言层，人工提供一条正确 STL 规则，验证 environment signal、monitor、safety cost 和 Safe RL 能否正确连接。

2. **Stage II: Controlled language**  
   在 Stage I 链路通过验证后，加入对象、距离和时间参数明确的受控自然语言。使用同一 Safe RL 后端，比较显式 `NL -> STL -> verified cost` 与直接 `NL -> predicted cost`，并分别评估公式、轨迹 cost label 和最终策略行为。

3. **Stage III: Broader setting**  
   进一步研究模糊语言、缺失参数、更多 STL 结构、感知噪声、动态障碍、其他 benchmark 和真实系统。

Stage I pilot 已完成。D37 的 40 条 Stage II v0 specifications、五个公式族、typed
AST、train/validation 数据和三条 baseline 已实现并通过 machine checks；5 条历史
记录由 Yuhang 复核，另外 35 条当前版本记录已由 `jiahui` 独立复核。15 个旧
checkpoint 的完整二维空间复放、三张图和固定 60-episode real corpus 也已完成。

Stage II-A 独立 CUDA 环境和三方法最小真实 update 均通过；但 full formal cell 的
首次运行出现 MCE 后 native-thread segfault，干净重试在完成两个 finite epochs 后又
记录新 MCE。D41 已暂停所有新训练，partial checkpoints 不算结果。held-out evaluation
还独立受到人工复核 gate 限制。

2026-08-13 新增 D42 fixed-route controlled variant：保持
`SafetyPointGoal1-v0` 的动力学与任务，固定起点、hazard 布局和四个顺序目标，并将
候选 center-distance 阈值改为 `d_warn=0.25`、`d_safe=0.28`。该版本固定的是任务路线
输入，不是 agent 的实际轨迹。旧 `K=79` 不得沿用；完成新 deadline 校准前以及 D41
硬件 gate 解除前，不启动训练。详见 `docs/FIXED_ROUTE_V1_WORK_ORDER.md`。

D43 将第一次 fixed-route 训练限制为 30 分钟 quick-turn：一个 matched seed，三组
目标各 150k transitions，按预检吞吐量可等量下调但不得低于 50k。训练后立即生成
三栏真实轨迹图和短报告并停止。该结果只用于检查运行和早期行为差异，不作为收敛、
显著性或方法优越性证据。

在负责人以 D45 明确接受本次 bounded D43 风险后，quick-turn 已完成。修正 preflight
与正式 epoch 优化负载不一致的问题后，吞吐公式前瞻性选择每条件 70k transitions；
三条件 checkpoint、20 条 paired stochastic evaluations、单条 deterministic 轨迹及
三张图均已生成。Gold missed/trigger 为 task-only `27/29=0.931`、Native
`27/40=0.675`、STL-dense `31/55=0.564`；STL-dense 相对 task-only 的描述性下降为
39.5%，三组 goal success 均为 100%。这是单 seed/20 episodes 的探索性 screening
signal，不是显著性、收敛或方法优越性结论。详见
`docs/fixed_route_v1_quick_turn_report.md`。

负责人随后以 D47 授权一次新的 long fixed-route matched round：新 seed `12647`，
task-only / Native / STL-dense 三条件均从零训练 1M transitions。STL 条件明确使用
C1 causal dense surrogate；启动预检不仅检查 selected-cost 路由，还要求 C1 累积量
严格大于 binary missed-event 累积量，从执行证据上排除“只有违反后 +1”的旧稀疏
接口。最终安全真值仍是独立 Gold binary evaluator。该单-seed round 是探索性长程
复现，不是五种子 confirmatory study，也不表示 D41 已通过。

D47 启动门已经实际通过：三组 10k preflight 均完成真实 40-update CUDA epoch，
STL 条件观测到 binary cost `1.10`、C1 dense/selected cost `103.72075`、positive-cost
step fraction `11.28%`。后台 service 已进入 task-only 的正式 1M cell，并在人工监控
交接前写出 20k transitions 和首个 checkpoint。按负责人要求，此后不再持续轮询且
没有终止健康训练；完整启动记录见
`docs/fixed_route_v1_full_dense_launch_report.md`。

D47 三组训练后来均实际到达 1M final checkpoint。post-run runner 因一行 logger
float 聚合产生 `3.81e-6` 差值而误判 STL routing；D48 保留原 failed manifest，用
尺度相关容差验证完成 artifact 后补齐相同 100 seeds 的 Gold evaluation 和图表。
最终 missed/trigger 为 Task `0/268`、Native `0/345`、STL-dense `31/139=0.223`；
return 为 35.674/31.694/17.477，native cost 为 2.420/0.020/8.730。C1 确实非稀疏，
但本轮 STL 结果更差且仍未满足自身 cost budget，因此是单-seed negative exploratory
result，不支持方法优越性或收敛。详见
`docs/fixed_route_v1_full_dense_result_report.md`。

2026-08-14，负责人在未发现可操作硬件修复后以 D49 授权 guarded Stage II compute
continuation：新异常先由工作电脑保留证据、自行诊断并做一次受控 clean retry，只有
无法本地解决时才寻求人工帮助。该授权不把历史 MCE 改写成硬件已证明正常。

D50 已登记 `jiahui` 对 35 条当前版本规格的独立审核。D51 决定不接受 6 个 logical
aliases，而是前瞻性修改参数并要求 `missing_witness_count=0`；任何被修改的规格必须
重新进入 delta human review，因此 held-out labels 仍未开放。

D52 要求先用 D47/D48 既有数据完成 C1 mechanism analysis，再执行原预注册的 bounded
C0/C1 matrix，不增加 C2 或新的自由参数搜索；若没有 cell 通过，在线分支结束。D53
将在线研究拆为 B1 `br-v0-001` 和条件式 B2 `rp-v0-001` + `or-v0-001`。预计总训练
时间超过 20 小时的 B1/B2 package 只有在 D53 strict upstream-perfect 条件全部通过时
才能自动启动，否则必须先提交 runtime/evidence 决策包。

## 2026-08-10 研究定位更新

最新文献核查确认，`STL monitor/state -> cost -> Lagrangian Safe RL` 已被多项
工作覆盖，不能作为本项目的独立新方法。Stage I 的准确定位是：建立经过验证的
gold-STL 语义参考和下游可行性基线，并为后续语言层提供错误隔离点；它不是策略
性能的数学上界。

当前暂定的项目级研究问题是：

> 在相同 online Safe RL 后端和环境中，显式 NL-to-STL 中间表示是否比直接
> NL-to-cost predictor 提供更高的语义忠实度、轨迹级可诊断性和时序安全表现？

该精确受控比较在截至 2026-08-10 的定向检索中未发现直接对应工作，但这只是
provisional novelty，不是“绝对无人做过”的证明。详细证据、相邻论文、理论可行性
和修订后的实验路线见 `docs/research_direction_novelty_feasibility.md`。

2026-08-10（8.10）新增的中文理论与实验说明见
`docs/theory_and_revised_experiment_8.10.md`。该文档进一步明确：当前研究以受控
实验为主体，但可以包含 temporal-memory necessity、formal-path conditional
correctness 和 cost-error-to-policy-risk transfer 等理论分析；同时记录 Stage II
不能向 direct learned-cost baseline 泄漏 gold monitor state 的公平性要求。

当前预期的首要研究产出是一个小型受控 benchmark 和评估协议，而不是预先声称
新的 translator、monitor 或 Safe RL 算法。只有比较暴露出可复现且现有方法无法
处理的缺陷后，才据此设计新方法。

## Stage I 的具体问题

Stage I 使用 `SafetyPointGoal1-v0`：

- application：二维静态障碍导航；
- task：Point agent 到达目标；
- safety signal：agent 到最近 hazard 的距离；
- safety rule：一个新的 warning episode 开始后，在 `K` 个 environment steps
  内恢复到 safe distance；
- initial Safe RL algorithm：OmniSafe 中的 PPO-Lagrangian；
- reference STL monitor：RTAMT。

精确的事件触发规则为：

```text
G(e_t -> F_[0,K](d_t >= d_safe))
```

其中 `e_t` 表示 monitor 当前没有未完成义务、且 `d_t < d_warn` 时开始的
warning episode。旧版 slides 中直接以 `d_t < d_warn` 作为前件的公式只作为
直观简写；`docs/stage1_rule_monitor_spec.md` 给出规范语义。

Stage I pilot 的历史问题是：

> 在一个已知静态障碍的简单导航环境中，一条人工确认正确的 bounded-recovery STL 规则能否被正确监测并转换成 Safe RL cost，从而减少超时恢复失败，同时不造成不可接受的目标完成能力下降？

## 当前进度

截至 2026-08-12：

- 已完成原始问题定义；
- 已完成核心文献梳理；
- 已明确完整链路中的独立不确定性；
- 已完成三阶段拆分；
- 已选择 application 和 benchmark；
- 已确定 Stage I 只测试一条 bounded-recovery STL 规则；
- 已形成 Stage I research plan slides；
- 已形成 Stage I engineering plan；
- 已建立并验证独立 Conda 环境 `stl-stage1`；
- 已运行 `SafetyPointGoal1-v0`、RTAMT 和 OmniSafe PPO-Lagrangian 构造测试；
- 已验证 EGL 无头渲染和轨迹保存；
- 已确定 `d_t` 为由公开 `hazards_lidar` 重建的最近中心距离，并截断到 lidar range 3；
- 已保存随机策略和 scripted hazard-approach 样例轨迹；
- 已冻结 equality、inclusive deadline、重复触发、episode 结束和
  binary STL cost 语义；
- 已冻结 monitor 状态机、输出字段、policy temporal state 和测试标准；
- 已给出 Ubuntu 参数校准协议及一次性实现工作单；
- 已用 30 条受控轨迹和 30 条随机轨迹完成参数校准；
- 已固定 `d_warn=0.45`、`d_safe=0.55`、`K=79` environment steps；
- 已实现公开距离提取、在线 monitor 和独立 offline oracle；
- 已生成 on-time、deadline violation 和 terminal-unresolved 稳定 fixtures；
- 27 个测试全部通过，online/direct oracle event-step mismatch 为 0；
- RTAMT 在 13 个完整义务窗口上 Boolean 与 robustness 全部一致，最大差异为 0；
- rule-and-monitor completion gate 已通过；
- 已实现 `./scripts/visualize_stage1.sh` 一键实时启动，画面显示距离、monitor
  状态、deadline、reward、native cost 和 STL cost；
- 已验证 native GLFW 窗口、EGL annotated MP4、独立 CSV 和 JSON 输出；
- 已实现 task-only、native-cost、STL-cost 三个 OmniSafe 环境入口；
- 三个条件共享相同的 60+3 维 policy observation，且 native reward、native
  cost、STL cost 和 selected algorithm cost 保持独立；
- 已验证 terminal/final-observation 顺序和每个 vector slot 的独立 monitor reset；
- wrapper 新增 11 项测试；pre-main evaluator 和 pilot protocol 新增 5 项测试，当前
  完整 43 项测试；
- 真实 positive-cost probe 产生 1 次 terminal-unresolved，`stl_cost=1` 且送入
  learner 的 selected cost 为 1；
- PPO-Lagrangian 已在 CPU 上完成 64-transition、单 epoch、至少一次 update 的
  integration smoke，并写出独立 cost 指标和 checkpoint；
- O6 已由负责人批准为 Stage I pilot protocol，但不是最终 main-study 标准；
- 已完成 2000-transition、完整 episode 对齐的 PPOLag on-policy sanity，真实 actor
  rollout 中产生 deadline violation，STL/selected mean episode cost 均为 `0.5`；
- 已实现统一 checkpoint evaluator；3 条 smoke 轨迹的 online monitor、independent
  oracle 和 RTAMT 完全一致；
- 已冻结 pilot protocol 和 task-only/native-cost/gold-STL 三个 condition overlays；
- 已完成每条件 10,000 transitions 的三条件 matched engineering sanity；三个 cost
  routing contract、final checkpoint、paired deterministic evaluation 和 gold
  oracle/RTAMT gate 全部通过；
- sanity 使用非 pilot seed 和每条件 3 条评估轨迹，不构成行为比较或收敛证据；
- 已在 RTX 4090 上启用 `torch 2.4.1+cu124`；Stage I wrapper tensor、完整 horizon
  positive-cost PPOLag update 和三条件 sanity 均在 `cuda:0` 通过；
- 已实现可恢复的 15-job matrix runner；成功 job 只有在 commit/config/checkpoint/
  progress/evaluation hashes 全部匹配时才会被 `--resume` 跳过；
- 已实现冻结的 paired hierarchical analysis、zero-baseline、goal non-inferiority、
  10,000-replicate bootstrap 和 learning-curve review；
- 完整自动测试增至 54 项，runner/analysis 的 11 项聚焦测试全部通过；
- 已完成 excluded 100k exact-scale CUDA preflight：335.68 transitions/s，PyTorch
  peak reserved VRAM 90 MiB，gold oracle/RTAMT agreement 全部通过；
- 已在明确授权后完成 15 jobs、15M transitions 和 1,500 条 paired deterministic
  final-checkpoint evaluations；全部 manifest/hash/oracle/RTAMT gate 通过；
- 冻结统计分析已完成：task-only/gold-STL missed-per-trigger 为 25.85%/26.03%，
  relative reduction 为 -0.71%（95% CI -24.92% 到 +21.88%），未达到 30% target；
- task-only 与 gold-STL goal success 均为 100%，10 percentage-point
  non-inferiority 通过；
- gold-STL final-20-epoch cost 仍为 1.650 events/episode，高于 0.1 limit，multiplier
  继续上升，因此 1M pilot 不作 convergence claim；
- 已生成正式 result report、10,000-replicate machine-readable analysis、四组
  PNG/SVG 图表、O8 final-standard proposal 和 O7 Stage II benchmark proposal。
- 已完成 pilot 后代码级失败分析：确认 metric/learner-objective、稀疏延迟 credit、
  budget/optimizer 时序及 OmniSafe runtime contract 风险，并形成分层修复建议；该
  文档不修改 D31，也不授权追加 GPU training。
- 已实现 installed OmniSafe runtime contract 和项目自有 regression tests，确认
  terminal-unresolved timeout cost bootstrap、cost-advantage scaling、实际 EpCost
  window 和 effective cost discount；未修改 Conda `site-packages`；
- 已实现旧 final-checkpoint 的 CPU-only per-step replay/export、机制分解和图表入口，
  不训练、不选择 checkpoint；
- 已实现 D37 完整 40 条、5 formula families 和 120 language records；全量 machine
  review 为 791 synthetic + 6 historical real traces，online/direct/RTAMT 一致，
  model-visible artifacts 不包含 held-out labels；
- 已生成 10,000 formal pairs、2,000 direct train traces、400 validation traces，
  test/OR leakage 为零；35 条新增 current-revision records 已由 `jiahui` 独立审核，
  alias amendment 变化项仍需生成 delta review packet；
- 已实现 T5 typed-AST formal、MiniLM current-observation direct、MiniLM+GRU-128
  history direct 和 deterministic grammar sanity；独立 `stl-stage2-offline` 环境可用
  RTX 4090 完成三方法 forward/backward/checkpoint；
- 已实现项目自有 terminal-cost bootstrap repair、C0/C1 learner-cost adapter、LR floor
  和 mechanism diagnostics；预算必须来自 3 个新 task-only controls × 50 个相同 paired
  evaluation seeds，并已实现可保留失败 attempt 的 matrix launcher；
- 已完成 15 checkpoints × 100 evaluations 的真实二维 replay：1,500 episodes、
  1,501,500 samples 与冻结结果一致，三张图已检查；
- 已固定 60 条 real-policy traces；2,400 spec/trace 组合 machine review 全通过，
  只释放 1,680 条 train/validation labels；
- 自动测试已扩展到 101 项并全部通过；
- 当前没有训练进程；Stage II-A 和 Gold diagnostic 等待 D41 hardware gate。

## 可视化快速启动

在仓库根目录运行：

```bash
./scripts/visualize_stage1.sh
```

默认使用 seed 44 的 scripted approach/escape 演示，在 MuJoCo 窗口右侧显示
`d_t`、monitor 状态、剩余 deadline、事件和三个相互独立的累计量。生成带相同
信息面板的 MP4：

```bash
./scripts/visualize_stage1.sh --render video
```

scripted controller 使用 privileged geometry 只是为了稳定地产生可见 warning 和
recovery，不是 RL policy，也不是安全实验结果。完整命令、输出字段和限制见
`docs/visualization.md`。

## 下一里程碑

Stage I full pilot 和无训练诊断已完成。D38 授权工作电脑按以下顺序连续推进：

1. 按 D51 修改 alias 参数，生成完整 distinguishing traces、更新 hashes，并将所有变化
   规格放入 delta human-review packet；
2. 在 guarded compute 下恢复 Stage II-A 三方法 × 三 seed train/validation matrix；
3. 使用 D47/D48 已有数据先完成 C1 mechanism report；
4. 不改变候选和搜索空间，运行三个新 seed 的预注册 300k C0/C1 screening matrix；
5. delta review 完成后运行 Stage II-A held-out 离线比较；
6. 只有 primary offline methods 与 Gold learner-cost gate 都通过，才冻结统一 online
   interface；
7. 先执行 B1 `br-v0-001`，通过后再对 `rp-v0-001` 和 `or-v0-001` 做 B2 feasibility 与
   online pilot；
8. B1/B2 的 workload-matched 总时间若预计超过 20 小时，仅在 D53 strict
   upstream-perfect exception 通过时自动启动，否则提交 owner decision package。

完整参数、split、模型、公式、成功门槛、输出和训练监控规则见
`docs/STAGE2_CONTINUOUS_WORK_ORDER.md`。训练启动后只监测到真实 update、checkpoint
和 ETA；若已授权任务预计剩余时间超过 20 分钟，保留 resumable job 运行并停止持续
轮询。该监控规则不覆盖 D53 的 20 小时 online automatic-launch cap。

- 正式结果：`docs/stage1_pilot_result_report.md`
- 代码失败分析与修复建议：
  `docs/stage1_code_failure_analysis_and_repair_recommendations.md`
- O8 决策包：`docs/stage1_o8_main_study_decision_proposal.md`
- O7 benchmark 提案：`docs/stage2_o7_benchmark_design_proposal.md`
- Stage I 轨迹/运行时诊断：`docs/stage1_trajectory_diagnosis_report.md`
- Stage I 二维空间诊断：`docs/stage1_spatial_trajectory_report.md`
- Stage II v0 foundation：`docs/stage2_v0_benchmark_report.md`
- 三方法公平性与待决项：`docs/stage2_v0_baseline_review_package.md`
- Stage II-A 环境、preflight 与 hardware stop：
  `docs/stage2a_environment_and_preflight_report.md`
- D38 Gold learner-cost 实现：`docs/stage2_gold_diagnostic_implementation_report.md`
- Stage II compute readiness/stop：`docs/stage2_compute_launch_readiness_report.md`
- 图表与机器可读结果：`results/stage1_pilot/analysis/`

复现 post-pilot CPU 诊断和 Stage II 数据构建：

```bash
env PYTHONNOUSERSITE=1 PYTHONPATH=src MUJOCO_GL=egl \
  /home/jerry/anaconda3/envs/stl-stage1/bin/python scripts/diagnose_stage1_trajectories.py
env PYTHONNOUSERSITE=1 PYTHONPATH=src MUJOCO_GL=egl \
  /home/jerry/anaconda3/envs/stl-stage1/bin/python scripts/build_stage2_v0_benchmark.py
env PYTHONNOUSERSITE=1 PYTHONPATH=src MUJOCO_GL=egl \
  /home/jerry/anaconda3/envs/stl-stage1/bin/python scripts/replay_stage1_spatial_trajectories.py
env PYTHONNOUSERSITE=1 PYTHONPATH=src MUJOCO_GL=egl \
  /home/jerry/anaconda3/envs/stl-stage1/bin/python scripts/plot_stage1_spatial_diagnosis.py
```

wrapper 的接口、测试、真实 positive-cost probe 和 PPO-Lagrangian smoke 结果见
`docs/omnisafe_integration_report.md`。

复现已完成的 integration gate：

```bash
./scripts/run_omnisafe_smoke.sh
```

复现 on-policy positive-cost gate：

```bash
./scripts/run_on_policy_sanity.sh
```

统一 checkpoint 评估入口和完整参数见
`docs/pre_main_engineering_gate_report.md`。

复现三条件 pilot sanity：

```bash
./scripts/run_stage1_pilot_sanity.sh
```

复现 CUDA 环境与 full-horizon PPOLag gate：

```bash
./scripts/validate_cuda_stage1.sh
```

查看 15-job dry run：

```bash
./scripts/run_stage1_pilot.sh --dry-run
```

复现冻结统计分析和图表：

```bash
env PYTHONNOUSERSITE=1 PYTHONPATH=src MUJOCO_GL=egl \
  /home/jerry/anaconda3/envs/stl-stage1/bin/python scripts/analyze_stage1_pilot.py
env PYTHONNOUSERSITE=1 PYTHONPATH=src MUJOCO_GL=egl \
  /home/jerry/anaconda3/envs/stl-stage1/bin/python scripts/plot_stage1_pilot.py
```

冻结协议、gate 结果和解释边界见
`docs/stage1_pilot_sanity_report.md`。

## 推荐阅读顺序

新成员或新的 Codex session 应按以下顺序阅读：

1. `AGENTS.md`
2. `README.md`
3. `docs/END_TO_END_RESEARCH_PIPELINE.md`
4. `docs/CURRENT_EXECUTION_DIRECTIVE.md`
5. `docs/STAGE2_CONTINUOUS_WORK_ORDER.md`
6. `docs/stage1_pilot_result_report.md`
7. `docs/stage1_code_failure_analysis_and_repair_recommendations.md`
8. `docs/stage1_o8_main_study_decision_proposal.md`
9. `docs/stage2_o7_benchmark_design_proposal.md`
10. `docs/stage1_trajectory_diagnosis_report.md`
11. `docs/stage1_spatial_trajectory_report.md`
12. `docs/stage2_v0_benchmark_report.md`
13. `docs/stage2_v0_baseline_review_package.md`
14. `docs/stage2a_environment_and_preflight_report.md`
15. `docs/stage2_gold_diagnostic_implementation_report.md`
16. `docs/stage2_compute_launch_readiness_report.md`
17. `DECISIONS.md`
18. `EXPERIMENT_PROGRESS_CHANGELOG.md`
19. `PROJECT_CONTEXT.md`
20. `docs/research_direction_novelty_feasibility.md`
21. `docs/theory_and_revised_experiment_8.10.md`
22. `docs/minimum_research_delivery_8.10.md`
23. `docs/CURRENT_STAGE1_STATUS.md`
24. `docs/stage1_rule_monitor_spec.md`
25. `docs/stage1_plan.md`
26. `docs/omnisafe_integration_report.md`
27. `references/REFERENCES.md`

## 文件夹说明

```text
safety-stl-stage1-handoff/
├── AGENTS.md
├── README.md
├── PROJECT_CONTEXT.md
├── DECISIONS.md
├── EXPERIMENT_PROGRESS_CHANGELOG.md
├── HANDOFF_PROMPT.md
├── MANIFEST.md
├── environment.stage1.yml
├── pyproject.toml
├── configs/
│   ├── stage1_rule.yaml
│   ├── omnisafe_integration_smoke.yaml
│   ├── on_policy_positive_cost_sanity.yaml
│   ├── stage1_pre_main_proposal.yaml
│   ├── cuda_validation.yaml
│   ├── stage1_pilot_sanity.yaml
│   ├── stage1_pilot_preflight.yaml
│   └── stage1_pilot/
├── scripts/
│   ├── collect_rule_calibration.py
│   ├── generate_monitor_fixtures.py
│   ├── run_monitor_agreement.py
│   ├── run_stage1_demo.py
│   ├── run_omnisafe_integration_smoke.py
│   ├── run_omnisafe_smoke.sh
│   ├── run_on_policy_positive_cost_sanity.py
│   ├── run_on_policy_sanity.sh
│   ├── evaluate_stage1_checkpoint.py
│   ├── evaluate_stage1_checkpoint.sh
│   ├── run_stage1_pilot_sanity.py
│   ├── run_stage1_pilot_sanity.sh
│   ├── run_stage1_pilot.py
│   ├── run_stage1_pilot.sh
│   ├── analyze_stage1_pilot.py
│   ├── plot_stage1_pilot.py
│   ├── validate_cuda_stage1.py
│   ├── validate_cuda_stage1.sh
│   └── visualize_stage1.sh
├── src/safety_stl/
│   ├── signals.py
│   ├── monitor.py
│   ├── oracle.py
│   ├── omnisafe_env.py
│   ├── evaluation.py
│   ├── pilot_protocol.py
│   ├── pilot_runner.py
│   ├── pilot_analysis.py
│   └── visualization.py
├── tests/
│   ├── test_distance_signal.py
│   ├── test_monitor_boundaries.py
│   ├── test_oracle_agreement.py
│   ├── test_omnisafe_wrapper.py
│   ├── test_evaluation.py
│   ├── test_pilot_runner.py
│   ├── test_pilot_analysis.py
│   ├── test_visualization.py
│   └── fixtures/
├── docs/
│   ├── END_TO_END_RESEARCH_PIPELINE.md
│   ├── CURRENT_EXECUTION_DIRECTIVE.md
│   ├── PROJECT_INTRODUCTION.md
│   ├── CURRENT_STAGE1_STATUS.md
│   ├── research_direction_novelty_feasibility.md
│   ├── theory_and_revised_experiment_8.10.md
│   ├── environment_setup.md
│   ├── environment_inspection.md
│   ├── stage1_rule_monitor_spec.md
│   ├── rule_calibration_report.md
│   ├── monitor_agreement_report.md
│   ├── omnisafe_integration_report.md
│   ├── stage1_pre_main_study_proposal.md
│   ├── pre_main_engineering_gate_report.md
│   ├── stage1_pilot_launch_readiness.md
│   ├── visualization.md
│   ├── stage1_plan.md
│   ├── problem-definition/
│   └── slides/
├── results/
│   ├── .gitignore
│   ├── environment_inspection/
│   │   ├── README.md
│   │   ├── summary.json
│   │   ├── random_seed_11_first_120_steps.mp4
│   │   └── scripted_hazard_approach_seed_44.mp4
│   ├── rule_calibration/
│   │   ├── README.md
│   │   └── summary.json
│   ├── monitor_agreement/
│   │   └── summary.json
│   ├── visualization/
│   │   ├── README.md
│   │   ├── summary.json
│   │   └── stage1_demo.mp4
│   ├── integration_smoke/
│   │   ├── README.md
│   │   └── summary.json
│   ├── on_policy_sanity/
│   │   ├── README.md
│   │   └── summary.json
│   └── evaluation_smoke/
│       ├── README.md
│       ├── episodes.csv
│       └── summary.json
└── references/
    ├── REFERENCES.md
    ├── papers/
    ├── extracted-text/
    └── code-notes/
```

## 重要边界

### 2026-08-13 fixed-route v1 pre-training status

固定布局、双 reset、四目标循环、EGL 渲染和新规则校准已经通过。30/30 个受控恢复
trial 的恢复时间为 20 steps，按冻结 Q95×1.25 规则得到独立的
`d_warn=0.25, d_safe=0.28, K=25`；online/oracle/RTAMT 零差异。三种同步 vector
environment 均可加载该 scenario/rule。详细证据见
`docs/fixed_route_v1_calibration_and_lifecycle_report.md`。

D41 硬件恢复证据仍缺失，所以本次没有启动 GPU preflight 或 quick-turn training。
这不是 CUDA 不可用，而是重复 MCE 后的研究完整性 stop gate 尚未完成。
runner、replay、预算冻结、fixed-checkpoint evaluator 和绘图入口已经完成 dry-run；
launch 状态见 `docs/fixed_route_v1_launch_readiness_report.md`。

Stage I 的成功只表示下游 STL-to-Safe-RL 链路在一个受控 benchmark 中成立。它不表示：

- 自然语言可以被准确翻译成 STL；
- 模糊安全要求可以被自动补全；
- agent 在训练或部署时绝不会违反安全条件；
- 方法已经适用于动态环境、视觉输入或真实机器人；
- 当前方案优于 shielding、formal synthesis 或所有 hand-coded alternatives。

这些问题属于后续阶段。
