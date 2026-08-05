# Safety STL Project Handoff

## 项目用途

该文件夹是 Language-Grounded STL for Safe RL 项目的可迁移研究记录。

它用于解决一个实际问题：当项目被移动到另一台 Ubuntu 电脑、由另一个 Codex 账号继续时，不依赖原聊天记录或账号 memory，也能准确理解当前研究目标、已经做出的决定、Stage I 的实验计划和下一步工作。

该文件夹包含研究规划、参考资料、可复现环境记录、参数校准证据和已经验证的
STL monitor/oracle 实现。OmniSafe wrapper 和训练代码尚未建立。

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
   在 Stage I 链路通过验证后，加入对象、距离和时间参数明确的受控自然语言，并评估 NL-to-STL translation accuracy 与 downstream behavior。

3. **Stage III: Broader setting**  
   进一步研究模糊语言、缺失参数、更多 STL 结构、感知噪声、动态障碍、其他 benchmark 和真实系统。

当前只开展 **Stage I**。

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

截至 2026-08-05：

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
- 23 个测试全部通过，online/direct oracle event-step mismatch 为 0；
- RTAMT 在 13 个完整义务窗口上 Boolean 与 robustness 全部一致，最大差异为 0；
- rule-and-monitor completion gate 已通过；
- 尚未编写 OmniSafe wrapper 或训练配置；
- 尚未开始 RL training。

## 下一里程碑

rule-and-monitor milestone 已通过。下一里程碑是 OmniSafe wrapper 与小规模
integration smoke test：保持 native reward、native cost 和 `stl_cost` 分离，给所有
对照条件追加相同 temporal policy state，并验证 vectorized reset/step/logging 接口。

在主训练之前，还必须预声明 violation reduction、goal-performance tolerance、
seed 数、evaluation episode 数和不确定性报告方法。当前仍不开始主 RL training
或自然语言层。

## 推荐阅读顺序

新成员或新的 Codex session 应按以下顺序阅读：

1. `AGENTS.md`
2. `README.md`
3. `PROJECT_CONTEXT.md`
4. `DECISIONS.md`
5. `docs/stage1_rule_monitor_spec.md`
6. `docs/stage1_plan.md`
7. `docs/slides/stage1_experiment_plan_slides.pdf`
8. `references/REFERENCES.md`

## 文件夹说明

```text
safety-stl-stage1-handoff/
├── AGENTS.md
├── README.md
├── PROJECT_CONTEXT.md
├── DECISIONS.md
├── HANDOFF_PROMPT.md
├── MANIFEST.md
├── environment.stage1.yml
├── pyproject.toml
├── configs/
│   └── stage1_rule.yaml
├── scripts/
│   ├── collect_rule_calibration.py
│   ├── generate_monitor_fixtures.py
│   └── run_monitor_agreement.py
├── src/safety_stl/
│   ├── signals.py
│   ├── monitor.py
│   └── oracle.py
├── tests/
│   ├── test_distance_signal.py
│   ├── test_monitor_boundaries.py
│   ├── test_oracle_agreement.py
│   └── fixtures/
├── docs/
│   ├── PROJECT_INTRODUCTION.md
│   ├── environment_setup.md
│   ├── environment_inspection.md
│   ├── stage1_rule_monitor_spec.md
│   ├── rule_calibration_report.md
│   ├── monitor_agreement_report.md
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
│   └── monitor_agreement/
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
