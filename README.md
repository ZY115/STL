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

Stage I pilot 已完成。D37 已冻结 Stage II v0 benchmark 和三条 baseline 的设计。
当前连续工作是：真实二维轨迹复现、40 条规格实现与人工复核、Stage II-A 离线比较、
Gold learner-cost 诊断、公平 online interface 冻结和 bounded Stage II-B pilot。

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
- 已建立 Stage II v0 单一已验证公式族的机器可验证基础：5 条草案已由 Yuhang 人工复核通过、55 条
  synthetic boundary/history trajectories、真实轨迹统一导入、Gold 三方一致性、
  schema/leakage/coverage 检查和统一离线指标；
- 已准备 formal、published-style current-observation direct 和 history-aware direct
  的 access/supervision 公平性评审包；没有选择、调用或训练语言模型。
- 完整自动测试现为 68 项，`pip check`、Python compile、shell syntax、JSON/YAML、
  generated-artifact hashes 和 deterministic Stage II rebuild 全部通过。

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

1. 用原 checkpoint/seed 补采 agent、goal 和 hazard 坐标，画真实二维轨迹；
2. 将五条草稿扩展为 D37 的 40 条受控规格并准备独立人工复核；
3. 实现 T5-base formal、MiniLM current-observation direct 和 MiniLM+GRU history
   direct baseline；
4. 通过复核后运行 Stage II-A held-out 离线比较；
5. 并行修复 terminal cost bootstrap，并比较 binary 与 causal dense Gold learner
   cost；
6. gate 通过后冻结统一 online cost interface，运行 bounded Stage II-B pilot。

完整参数、split、模型、公式、成功门槛、输出和训练监控规则见
`docs/STAGE2_CONTINUOUS_WORK_ORDER.md`。训练启动后只监测到真实 update、checkpoint
和 ETA；若预计剩余时间超过 20 分钟，保留 resumable job 运行并停止持续轮询。

- 正式结果：`docs/stage1_pilot_result_report.md`
- 代码失败分析与修复建议：
  `docs/stage1_code_failure_analysis_and_repair_recommendations.md`
- O8 决策包：`docs/stage1_o8_main_study_decision_proposal.md`
- O7 benchmark 提案：`docs/stage2_o7_benchmark_design_proposal.md`
- Stage I 轨迹/运行时诊断：`docs/stage1_trajectory_diagnosis_report.md`
- Stage II v0 foundation：`docs/stage2_v0_benchmark_report.md`
- 三方法公平性与待决项：`docs/stage2_v0_baseline_review_package.md`
- 图表与机器可读结果：`results/stage1_pilot/analysis/`

复现 post-pilot CPU 诊断和 Stage II 数据构建：

```bash
env PYTHONNOUSERSITE=1 PYTHONPATH=src MUJOCO_GL=egl \
  /home/jerry/anaconda3/envs/stl-stage1/bin/python scripts/diagnose_stage1_trajectories.py
env PYTHONNOUSERSITE=1 PYTHONPATH=src MUJOCO_GL=egl \
  /home/jerry/anaconda3/envs/stl-stage1/bin/python scripts/build_stage2_v0_benchmark.py
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
11. `docs/stage2_v0_benchmark_report.md`
12. `docs/stage2_v0_baseline_review_package.md`
13. `DECISIONS.md`
14. `EXPERIMENT_PROGRESS_CHANGELOG.md`
15. `PROJECT_CONTEXT.md`
16. `docs/research_direction_novelty_feasibility.md`
17. `docs/theory_and_revised_experiment_8.10.md`
18. `docs/minimum_research_delivery_8.10.md`
19. `docs/CURRENT_STAGE1_STATUS.md`
20. `docs/stage1_rule_monitor_spec.md`
21. `docs/stage1_plan.md`
22. `docs/omnisafe_integration_report.md`
23. `references/REFERENCES.md`

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

Stage I 的成功只表示下游 STL-to-Safe-RL 链路在一个受控 benchmark 中成立。它不表示：

- 自然语言可以被准确翻译成 STL；
- 模糊安全要求可以被自动补全；
- agent 在训练或部署时绝不会违反安全条件；
- 方法已经适用于动态环境、视觉输入或真实机器人；
- 当前方案优于 shielding、formal synthesis 或所有 hand-coded alternatives。

这些问题属于后续阶段。
