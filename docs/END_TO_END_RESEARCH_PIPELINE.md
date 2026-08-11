# End-to-End Research Pipeline and Independent Handoff

- **Version:** 2026-08-10
- **Purpose:** 让没有原聊天记录的新成员能够理解研究目标、已有依据、完整实验路线、
  当前状态、后续阶段和所有阻塞信息，并能按预先定义的 gate 独立推进。
- **Authority:** 本文定义长期研究路线；`DECISIONS.md` 定义已确认与待确认决定；
  各专项 report 定义已经完成的工程事实。

## 1. 一句话研究目标

在同一个现有 Safe RL benchmark 和同一个训练后端中，比较两种将自然语言时序
安全要求转换成 RL safety cost 的路线：

```text
Formal path:  NL -> STL -> verified monitor -> temporal event cost -> Safe RL
Direct path:  NL + causal trajectory history -> learned cost predictor -> Safe RL
```

核心问题不是“STL 能否接入 RL”，而是：

> 显式形式化中间表示是否能比直接 learned cost 更忠实地保留时序语义、更容易
> 诊断错误，并在相同训练条件下产生更好的安全行为与可接受的任务表现？

“更有优势”是待验证假设，不是预设结论。

## 2. 为什么原始目标被修改

### 2.1 原始目标

最初计划直接实现完整链路：用户给出自然语言任务，系统抽取安全要求，生成 STL，
monitor 轨迹、产生 cost，再使用 Safe RL 学习策略。

### 2.2 第一次简化：分离错误来源

完整链路同时包含五种相互独立的不确定性：

1. language translation 是否正确；
2. language grounding 到环境 signal 和参数是否正确；
3. STL monitor 是否符合公式语义；
4. monitor output 是否正确转换并传入 Safe RL cost；
5. Safe RL 是否能在任务 reward 与 safety cost 之间学到有效策略。

如果一次性实现，失败时无法确定是哪一层造成。因此 Stage I 使用人工确认的 gold
STL，先移除 translation 和 grounding error。

### 2.3 第二次修改：纠正 novelty

2026-08-10 的文献核查发现，以下内容已有直接先例：

- STL history/state augmentation for RL；
- STL constraint with Lagrangian DRL；
- temporal-logic monitor violation converted to PPO-Lagrangian cost；
- STL monitoring and RL-framework integration。

因此，`STL monitor -> cost -> Safe RL` 不能作为新方法。Stage I 被重新定位为
**gold-STL control and downstream feasibility baseline**。

### 2.4 修订后的项目级目标

修订后的项目不再只问“链路能否运行”，而是比较两类 safety representation，并在
formula、trajectory label 和 learned policy 三层分析差异。第一项可能的贡献是受控
benchmark 与 evaluation protocol；只有当比较暴露出可复现缺陷时，才进一步提出
有明确机制的新方法。

## 3. 应用与 benchmark

### 3.1 固定应用

二维 Point robot 在静态 hazards 周围导航并到达目标。

### 3.2 固定 benchmark

`SafetyPointGoal1-v0` from Safety-Gymnasium。

选择它不是因为环境本身新，而是因为它提供：

- 标准 goal-reaching reward；
- 标准 native hazard cost；
- 可复现的连续控制动力学；
- OmniSafe 兼容接口；
- 足够简单的 signal，使 representation error 与 perception error 可以分开。

### 3.3 benchmark 在论文中的角色

benchmark 是控制变量和测试平台，不是贡献。第一版只支持：

- 已知、静态 hazards；
- state-based public observations；
- 已定义的对象、distance signal 和数值参数；
- bounded temporal safety requirements；
- empirical Safe RL，而不是零违反形式化保证。

动态障碍、视觉感知、未知地图和真实机器人属于后续 external-validity 扩展。

## 4. 当前候选方法与对照方法

必须区分“环境控制条件”和“真正的语言方法 baseline”。

### 4.1 环境与下游控制条件

| Condition | Learner cost | 研究作用 | 是否是语言方法对手 |
|---|---|---|---|
| Task only | 0 | 检查任务本身是否可学 | 否 |
| Native safety | benchmark per-step hazard cost | 比较即时几何 cost | 否 |
| Gold STL | human-verified STL monitor event cost | 下游 oracle/control reference | 否 |

这三个条件只回答：在语言错误被移除时，下游行为如何变化。它们不能单独回答
NL-to-STL 是否优于已有自然语言方法。

### 4.2 真正的 representation comparison

| Method | Input | Intermediate | Cost source | 当前状态 |
|---|---|---|---|---|
| Gold reference | gold STL + trajectory | verified STL | RTAMT/direct oracle | monitor 已完成 |
| Explicit formal path | NL + grounded signal schema | predicted STL | verified monitor | translator 未选择 |
| Published direct-cost baseline | NL + current observation text | none | learned/prompted binary cost | 论文已选，未复现 |
| Strong direct-cost baseline | NL + causal trajectory prefix | latent history | history-aware predicted cost | 架构未确认 |

主要 published direct-cost reference 是 Lou et al. 2024 的 free-form natural-language
cost prediction。TTCT 2024 提供另一种 text-to-trajectory learned safety signal。

只比较 current-observation direct baseline 不公平，因为 bounded-recovery cost 依赖
历史。主要对手必须是 history-aware direct predictor；current-observation 方法只能
作为 published-style baseline 或结构性 ablation。

### 4.3 目前能否称为“我们的方法”

目前可以称为 **our candidate formal pipeline**，但不能称为已证明的新算法。它是：

```text
NL requirement
  -> explicit STL candidate
  -> explicit signal/parameter grounding
  -> syntax and semantic checks
  -> verified causal monitor
  -> temporally meaningful violation-event cost
  -> fixed Safe RL backend
```

它的候选优势具有可解释机制：

1. deadline、negation、persistence 和 temporal scope 被显式表示；
2. 一旦 formula 与 grounding 正确，monitor output 是机械可检查结果；
3. error 可以定位为 translation、grounding、monitoring 或 RL optimization；
4. cost 在完整 temporal violation event 被识别后再累积，而不是先把不同语义压成
   任意 scalar。

它的候选劣势同样必须测试：

- 需要 formula supervision 或人工确认；
- grounding 和数值参数仍可能错误；
- 翻译模型可能生成语法正确但语义错误的 STL；
- binary event cost 可能稀疏、延迟且难以优化；
- direct predictor 可能更灵活并在开放语言上表现更好。

如果最终只复用现有 translator、monitor 和 Safe RL optimizer，则贡献应表述为
benchmark、controlled comparison 和 error analysis，而不是新算法。

## 5. 三个研究 Stage 与七个执行 Work Package

Research Stage 表示问题范围；Work Package 表示可以依次执行的工程和实验任务。

```text
Stage I: Gold-STL downstream control
  WP1 Gold-STL training/evaluation completion

Stage II: Controlled-language representation comparison
  WP2 Controlled benchmark construction
  WP3 Baseline implementation and offline evaluation
  WP4 Matched online Safe RL comparison
  WP5 Error analysis and contribution decision

Stage III: Broader validity and method extension
  WP6 Method refinement or benchmark expansion
  WP7 New environments, uncertainty, and real systems
```

## 6. WP1: 完成 Gold-STL 下游控制实验

### 目标

证明在 translation 和 grounding error 被移除时，STL cost 可以真正出现在 policy
rollout 中，并测量它是否改变 temporal violation 与 goal-reaching behavior。

### 已完成输入

- benchmark 和环境锁文件；
- `d_warn=0.45`、`d_safe=0.55`、`K=79`；
- online monitor、offline oracle、RTAMT agreement；
- task-only/native/STL wrapper；
- 43 tests、一次 minimal PPO-Lagrangian update、一次 full-horizon on-policy
  positive-cost sanity、统一 checkpoint evaluator、D31 frozen pilot protocol 和
  三条件 small-budget sanity。

### 决定状态

O6 已由 D31 确认为 Stage I pilot protocol，但不是最终 main-study 标准。primary
metric、pilot target、goal tolerance、matched seeds、evaluation episodes、bootstrap、
cost-limit 语义和 full-horizon alignment 已冻结在 `configs/stage1_pilot/`。O8 保留
pilot 后的最终标准决定。

### 实施内容

1. 统一 checkpoint evaluation runner（已完成）；
2. positive-cost on-policy sanity（已完成）；
3. 冻结 matched pilot configs（已完成）；
4. 三条件 small-budget sanity（已完成）；
5. 按 `docs/CURRENT_EXECUTION_DIRECTIVE.md` 实现可恢复的 15-job runner、冻结统计
   analysis、自动测试和 100k exact-scale preflight；
6. readiness gate 获得一次 compute authorization 后，运行 task-only、native-cost、
   gold-STL-cost full pilot comparison；
7. 每个 final checkpoint 立即使用相同 gold STL oracle 评价；
8. 汇总 1,500 条 paired evaluations，完成 WP1 report 和 O8 proposal；
9. 同时开始不需要 GPU 的 WP2/O7 benchmark-design proposal。

### 输出

- fixed configs；
- per-seed training/evaluation results；
- task success/return and gold temporal-violation table；
- failure cases and checkpoint visualization；
- Stage I report。

### Gate

WP1 只需要证明 gold-STL downstream baseline 可用并量化其 trade-off。Gold STL 不
需要优于 native cost 才能进入 WP2；但如果它完全不能改变 behavior，必须先分析
cost sparsity、budget、policy memory 或 optimization，而不能把失败归因于语言层。

## 7. WP2: 构建受控语言与轨迹 benchmark

### 目标

建立同一批数据，使 formal path 和 direct path 可以公平比较安全语义。

### 必须确认的信息

`DECISIONS.md` 中 O7 必须确认：

- 支持的 STL fragment 和 formula templates；
- controlled-language grammar；
- predicates、signals、thresholds 和 deadlines；
- semantic minimal-pair taxonomy；
- train/validation/test split，尤其是 unseen formula structure split；
- human formula-confirmation protocol。

### 第一版建议范围

- 30--50 个 controlled NL/gold-STL specifications 作为 pilot，不是最终规模承诺；
- meaning-preserving paraphrases；
- threshold 和 deadline 变化；
- `within` vs `after`；
- eventual recovery vs sustained safety；
- conjunction vs disjunction；
- polarity/negation cases；
- no-trigger、on-time、deadline-boundary、late、terminal-unresolved trajectories；
- 相同当前 observation、不同 temporal history 的成对 trajectories。

### 输出

每个 specification record 至少包含：

```text
spec_id
natural_language
gold_stl
grounding_schema
parameter_values
formula_family
semantic_pair_id
split
source_or_annotation_record
```

每条 trajectory 至少包含 signals、gold events、gold costs、boundary metadata 和来源
policy。数据格式和 schema 必须进入版本控制；bulk trajectory data 可以外部存储，
但 hash 和生成命令必须记录。

### Gate

人工检查 gold formula/grounding，RTAMT 与 direct oracle 在支持 fragment 上一致；
每一种 semantic contrast 都必须有能区分其语义的 trajectory，而不是只改文本。

## 8. WP3: 复现方法并先做离线比较

### 目标

在花费大量 RL 训练之前，先判断不同 cost generator 是否真正表达了目标语义。

### 方法

1. gold STL oracle；
2. 一个当前 NL-to-STL 方法，例如 RESTL 或 ReasonSTL，最终选择需记录理由；
3. Lou et al. 2024 published-style direct cost baseline；
4. 一个具有 causal history 的强 direct-cost baseline；
5. 可选 TTCT-style learned trajectory safety signal。

“复现”必须说明是 strict reproduction、adaptation 还是 idea-level reimplementation。
不能把论文原设置和本项目适配设置混写。

### 公平性

- 相同 language split 和 trajectory corpus；
- 相同可见 environment signals；
- direct baseline 不得获得 gold STL 或 gold monitor state；
- formal path 不得额外看到 test gold formulas；
- 报告 annotation count、pretrained model、parameter count、compute 和 API use；
- direct predictor 必须使用 causal prefix，不能看到未来 trajectory；
- final common truth 始终是 human-verified gold STL oracle。

### 指标

Formula level：syntax validity、operator/predicate/parameter accuracy、semantic
equivalence、minimal-pair formula flip。

Trace level：precision、recall、F1、false-negative rate、false-positive rate、event
timing error、deadline-boundary accuracy、terminal-unresolved accuracy、minimal-pair
consistency 和 paraphrase consistency。

### Gate

只有达到预声明 trace-level gate 的方法进入 WP4。若所有方法均失败，先修复 dataset、
grounding 或 baseline；不能通过 RL training 隐藏错误 cost。

## 9. WP4: Matched Online Safe RL Comparison

### 目标

回答 cost-label 差异是否会传递为 learned policy behavior 差异。

### 固定内容

- SafetyPointGoal1-v0 task reward；
- OmniSafe backend 和 policy architecture；
- training budget、seeds 和 evaluation episodes；
- specification split；
- policy 可用的通用 observation/history；
- gold STL offline evaluation oracle。

### 主要比较

```text
Task-only control
Native hazard-cost control
Gold-STL oracle control
NL-to-STL formal path
Published direct-cost baseline
History-aware direct-cost baseline
```

由于不同 cost 的单位不同，不应假设相同 numeric `cost_limit` 就公平。应预声明每种
cost 的语义预算，或报告小范围 budget sweep 与 task-safety Pareto curve。

### Policy-level 指标

- gold violation per trigger；
- missed recovery obligations；
- terminal unresolved rate；
- trigger and recovery distributions；
- goal success and episode return；
- training stability and multiplier behavior；
- matched-seed uncertainty；
- cost predictor error on policy-induced distribution shift。

### Gate

所有方法必须由 gold oracle 统一评价。方法自己的 predicted cost 只能作为训练输入和
diagnostic，不能作为最终安全结论。

## 10. WP5: 解释结果并决定贡献类型

完成 WP3 和 WP4 后，不需要重新从零思考方向，按以下预设分支处理。

### Branch A: Formal path 在语义与策略层都更好

检查优势是否来自显式 semantics，而不是更强模型、更多标注、monitor-state leakage
或更保守 cost。通过 ablation 分离 translator、verification、event cost 和 policy
memory。若成立，贡献可定位为 formal-intermediate representation 的实证优势及
mechanistic error analysis。

### Branch B: Formal path 语义更准，但策略没有更安全

研究 delayed/sparse event cost、cost budget、exploration 和 optimization。可能的
新方法应针对 semantic cost 到 policy learning 的接口，而不是继续提高翻译准确率。

### Branch C: Direct path 同样准确或更好

不应强行声称 STL 优势。贡献可以转为 negative result、适用边界和 benchmark；也可
分析 formal path 的 translation/grounding burden，并寻找 human verification、repair
或 lower-data generalization 是否仍有价值。

### Branch D: 两条路线在不同语义结构上各有优势

形成 hybrid method 的依据，例如 direct model 提议、formal checker 验证，或对高风险
specification 使用 human confirmation。必须由已观察到的错误类型驱动设计。

### Branch E: benchmark 太简单，无法区分方法

先扩展 formula/trajectory coverage 或加入第二个同类 benchmark，再讨论算法。不能把
“没有差异”直接解释成所有方法等价。

## 11. WP6: 方法贡献或 benchmark 扩展

只有 WP5 提供明确失败模式后，才选择新方法模块。可能方向包括：

- semantic minimal-pair consistency training；
- formula/grounding verification；
- trace counterexample-based translation repair；
- temporally dense but semantics-preserving cost shaping；
- uncertainty-aware human confirmation；
- formal/direct hybrid cost construction。

任何候选模块都必须有：对应失败证据、明确输入输出、最接近 prior work、ablation 和
可证伪假设。UAV 2026 的 MILP repair 已覆盖部分数值可行性修复，因此不能把一般
“repair”直接作为 novelty。

## 12. WP7: Stage III 外部有效性

按证据逐步增加：

1. 更多 STL structures 和 simultaneous requirements；
2. second comparable Safe RL benchmark；
3. moving hazards and partial observability；
4. perception/grounding uncertainty；
5. free-form or underspecified language；
6. runtime shield/intervention；
7. UAV or real-robot deployment。

每次只放开一个主要不确定性，并保留上一阶段 gold reference，避免重新失去错误归因。

## 13. 理论解释与实验的关系

本项目不是纯经验比较。当前理论依据包括：

1. 相同 current observation 可以对应不同 temporal history 和不同正确 cost，因此
   memoryless direct predictor 一般不足；
2. 当 translation、grounding 和 monitor 都正确时，formal path 对支持 fragment 具有
   conditional correctness；
3. formal path label error 可以按 translation、grounding 和 monitoring 分解；
4. direct predictor 的 false-negative cost error 会扩大真实 violation exposure；
5. 固定 trajectory accuracy 不能推出 online policy safety，因此仍需 WP4。

完整推导位于 `docs/theory_and_revised_experiment_8.10.md`。这些命题解释“为什么可能
有优势”，但不能替代实际 representation 和 policy comparison。

## 14. 参考来源与本地位置

| 用途 | 主要来源 | 本地位置 |
|---|---|---|
| Benchmark | Safety-Gymnasium | `references/REFERENCES.md` Section 1--2 |
| Safe RL backend | OmniSafe | `references/REFERENCES.md` Section 1--2 |
| Reference monitoring | RTAMT | `references/REFERENCES.md` Section 1--2 |
| STL + Lagrangian RL prior | Ikemoto and Ushio 2022 | `references/papers/related/2022_STL_Constraints_Lagrangian_DRL_8.10.pdf` |
| Monitor cost + PPO prior | PPO-LTL 2026 | `references/papers/related/2026_PPO_LTL_8.10.pdf` |
| Published direct NL cost | Lou et al. 2024 | `references/papers/related/2024_Freeform_NL_Constraints_Safe_RL_8.10.pdf` |
| Text-to-trajectory baseline | TTCT 2024 | `references/papers/related/2024_Text_to_Trajectory_Safe_RL_8.10.pdf` |
| NL-to-STL candidates | RESTL and ReasonSTL | `references/papers/related/2026_RESTL_8.10.pdf`, `references/papers/related/2026_ReasonSTL_8.10.pdf` |
| Repair boundary | UAV NL-to-STL + MILP 2026 | `references/papers/2026_UAV_NL_STL_MILP_Repair_8.10.pdf` |
| Novelty audit | closest prior work index | `references/papers/related/CLOSEST_PRIOR_WORK_8.10.md` |

所有链接、论文作用和 overlap/boundary 统一记录在 `references/REFERENCES.md`。PDF 是
authoritative source；`references/extracted-text/` 仅用于搜索。

## 15. 当前状态与下一动作

截至 2026-08-11：

| Work package | 状态 | 下一动作 |
|---|---|---|
| WP1 Gold-STL control | D31/D32 and three-condition sanity passed; full runner/analysis and behavior pilot incomplete | 执行 `CURRENT_EXECUTION_DIRECTIVE.md`：runner + analysis + tests + 100k preflight；readiness 审核后一次性完成 15 runs、1,500 evaluations 和 report |
| WP2 Controlled benchmark | not started | O7 后定义 schema 和 pilot set |
| WP3 Offline methods | not started | 选择 translator、published direct 和 history-aware direct baselines |
| WP4 Online comparison | not started | 等 WP3 trace gate |
| WP5 Contribution decision | not started | 按预定义 Branch A--E 处理 |
| WP6 Method/benchmark extension | deferred | 由 WP5 failure mode 决定 |
| WP7 External validity | deferred | 由前述内部有效性决定 |

新成员完成当前 gate 后，不应停下来问“然后做什么”。应回到本表，进入下一个未完成
WP；只有遇到 `DECISIONS.md` 明确标记的 blocking decision 才暂停实施，并提交包含
候选值、依据、风险和影响的 decision proposal。

## 16. 文档维护规则

- `END_TO_END_RESEARCH_PIPELINE.md`：长期路线、比较结构和预设分支；
- `DECISIONS.md`：confirmed/open/deferred decisions；
- `EXPERIMENT_PROGRESS_CHANGELOG.md`：完成了什么和为什么修改；
- `README.md`：当前摘要与入口；
- `docs/*_report.md`：每个 gate 的证据、命令和限制；
- `results/`：machine-readable summaries 和实验结果；
- `references/REFERENCES.md`：论文、仓库和用途；
- `MANIFEST.md`：文件清单。

完成每个 WP 后必须更新状态表、decision log、changelog、对应 report 和 checksum。
不能只更新“下一步”而丢失后续 WP，也不能把 proposed parameter 写成 confirmed fact。
