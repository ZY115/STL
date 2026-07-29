# Safety STL Project Handoff

## 项目用途

该文件夹是 Language-Grounded STL for Safe RL 项目的可迁移研究记录。

它用于解决一个实际问题：当项目被移动到另一台 Ubuntu 电脑、由另一个 Codex 账号继续时，不依赖原聊天记录或账号 memory，也能准确理解当前研究目标、已经做出的决定、Stage I 的实验计划和下一步工作。

该文件夹目前只包含研究规划、参考资料和交接说明。实验代码目录将在环境和接口确认后再建立。

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
- safety rule：进入 warning zone 后，在 `K` 个 environment steps 内恢复到 safe distance；
- initial Safe RL algorithm：OmniSafe 中的 PPO-Lagrangian；
- reference STL monitor：RTAMT。

STL 规则为：

```text
G(d_t < d_warn -> F_[0,K](d_t >= d_safe))
```

当前研究问题是：

> 在一个已知静态障碍的简单导航环境中，一条人工确认正确的 bounded-recovery STL 规则能否被正确监测并转换成 Safe RL cost，从而减少超时恢复失败，同时不造成不可接受的目标完成能力下降？

## 当前进度

截至 2026-07-29：

- 已完成原始问题定义；
- 已完成核心文献梳理；
- 已明确完整链路中的独立不确定性；
- 已完成三阶段拆分；
- 已选择 application 和 benchmark；
- 已确定 Stage I 只测试一条 bounded-recovery STL 规则；
- 已形成 Stage I research plan slides；
- 已形成 Stage I engineering plan；
- 尚未安装实验环境；
- 尚未确定 `d_t` 的最终计算方式；
- 尚未选择 `d_warn`、`d_safe` 和 `K`；
- 尚未编写 monitor、wrapper 或训练代码；
- 尚未开始 RL training。

## 当前唯一的下一步

先进行 environment-only smoke test：

1. 在 Ubuntu 上建立兼容的 Python 环境；
2. 安装并运行 Safety-Gymnasium；
3. 执行 `SafetyPointGoal1-v0` 的随机或简单策略；
4. 检查 public API 能否提供定义 `d_t` 所需的 agent/hazard 信息；
5. 分别记录 native reward、native cost、termination 和 trajectory；
6. 形成一份简短的 environment inspection report。

在该步骤完成前，不应开始 RL training，也不应加入自然语言层。

## 推荐阅读顺序

新成员或新的 Codex session 应按以下顺序阅读：

1. `AGENTS.md`
2. `README.md`
3. `PROJECT_CONTEXT.md`
4. `DECISIONS.md`
5. `docs/stage1_plan.md`
6. `docs/slides/stage1_experiment_plan_slides.pdf`
7. `references/REFERENCES.md`

## 文件夹说明

```text
safety-stl-stage1-handoff/
├── AGENTS.md
├── README.md
├── PROJECT_CONTEXT.md
├── DECISIONS.md
├── HANDOFF_PROMPT.md
├── MANIFEST.md
├── docs/
│   ├── PROJECT_INTRODUCTION.md
│   ├── stage1_plan.md
│   ├── problem-definition/
│   └── slides/
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
