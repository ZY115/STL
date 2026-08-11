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
protocol、三条件 sanity 证据，以及一条命令启动的实时/录像可视化入口。完整 1M
pilot 对照训练尚未开始。

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

当前只开展 **Stage I**。

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

当前研究问题是：

> 在一个已知静态障碍的简单导航环境中，一条人工确认正确的 bounded-recovery STL 规则能否被正确监测并转换成 Safe RL cost，从而减少超时恢复失败，同时不造成不可接受的目标完成能力下降？

## 当前进度

截至 2026-08-11：

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
- 完整 1M×3×5 pilot training 未启动。

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

O6 pilot protocol 已确认，冻结配置、CUDA 和三条件 small-budget sanity gate 已完成。
当前先执行 `docs/CURRENT_EXECUTION_DIRECTIVE.md`：实现可恢复 15-job runner、冻结
hierarchical analysis、测试和一个排除于 inference 的 100k exact-scale preflight，
形成 launch-readiness report。Full pilot 的一次 compute authorization 通过后，15
runs、1,500 paired evaluations、统计分析和 WP1 report 连续完成，不再逐文件询问。

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

冻结协议、gate 结果和解释边界见
`docs/stage1_pilot_sanity_report.md`。

## 推荐阅读顺序

新成员或新的 Codex session 应按以下顺序阅读：

1. `AGENTS.md`
2. `README.md`
3. `docs/END_TO_END_RESEARCH_PIPELINE.md`
4. `docs/CURRENT_EXECUTION_DIRECTIVE.md`
5. `DECISIONS.md`
6. `EXPERIMENT_PROGRESS_CHANGELOG.md`
7. `PROJECT_CONTEXT.md`
8. `docs/research_direction_novelty_feasibility.md`
9. `docs/theory_and_revised_experiment_8.10.md`
10. `docs/minimum_research_delivery_8.10.md`
11. `docs/CURRENT_STAGE1_STATUS.md`
12. `docs/stage1_rule_monitor_spec.md`
13. `docs/stage1_plan.md`
14. `docs/omnisafe_integration_report.md`
15. `docs/slides/stage1_current_progress_slides.pdf`（wrapper 前的 2026-08-10 快照）
16. `docs/slides/stage1_experiment_plan_slides.pdf`（早期计划版，供追溯）
17. `references/REFERENCES.md`

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
│   └── visualization.py
├── tests/
│   ├── test_distance_signal.py
│   ├── test_monitor_boundaries.py
│   ├── test_oracle_agreement.py
│   ├── test_omnisafe_wrapper.py
│   ├── test_evaluation.py
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
