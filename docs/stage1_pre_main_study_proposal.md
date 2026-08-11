# Stage I pilot 预声明协议（O6 / D31）

- **状态：** 已批准为 Stage I pilot protocol；不是最终 main-study 标准
- **日期：** 2026-08-11
- **机器可读版本：** `configs/stage1_pre_main_proposal.yaml`
- **冻结配置：** `configs/stage1_pilot/`
- **约束：**必须先通过三条件 small-budget sanity gate；通过后也不得自动启动完整
  1M runs，必须先报告 gate 结果。

## 1. 提案要解决的问题

Stage I 的接口、monitor 和一次最小 PPOLag update 已验证，但尚未规定“怎样的行为变化
算成功”。如果先看训练结果再选择门槛、seed 或评估方法，会引入明显的选择偏差。
本协议为 O6 固定一组 pilot 值；这些数值由项目负责人在 2026-08-11 明确批准，不是
由当前 RL 结果反推得到，但也不能被描述为最终 main-study 标准。

## 2. 候选主要判据

主要安全指标定义为所有评估 episode 上 pooled 的 missed-recovery rate：

```text
(deadline violations + terminal unresolved) / warning triggers
```

`deadline_violation` 和 `terminal_unresolved` 同时进入 numerator，是因为当前训练 cost
对二者都计一次 binary event；报告时仍必须分开列出。无 trigger 时该比率为 N/A，
不能把 vacuous satisfaction 描述为“学会恢复”。同时报告 trigger rate 和每 episode
adverse outcome，防止只看条件比率遗漏完全避开 warning zone 的策略变化。

Stage I pilot 的主要比较是 gold-STL condition 相对 task-only。pilot target 是上述
比率至少相对降低 30%，并同时报告绝对差。如果 task-only baseline rate 为 0，相对
降低量无定义，只使用绝对差。matched-seed 95% paired bootstrap interval 用于报告
绝对差的不确定性；30% 是 pilot 判据，不表示现有样本量必然具有足够 power，也不是
最终 main-study 标准。

差值的符号固定为：

```text
absolute reduction = task-only rate - gold-STL rate
relative reduction = absolute reduction / task-only rate
```

因此正值表示 gold-STL 改善；baseline 为 0 时第二式不计算。

任务能力建议用 `episode_goal_success` 作为主要 non-inferiority 指标：1000-step
episode 内至少出现一次 `goal_met`。允许的绝对下降上限为 10 percentage points，且
paired 95% interval 下界必须高于 `-0.10`。episode return 和每 episode goal events
全部报告，但不在第一版中另设一个容易受尺度影响的相对 return cutoff。

## 3. Seeds、评估次数和不确定性

pilot 固定：

- 5 个训练 seeds：`1101, 2202, 3303, 4404, 5505`；
- 每个训练 seed 的 final checkpoint 使用相同的 100 个 evaluation seeds：
  `10000--10099`；
- deterministic evaluation；
- 完整 1000-step horizon；
- primary uncertainty：10,000 次 paired hierarchical percentile bootstrap，先重采样
  training seed，再在 seed 内重采样 matched evaluation episode；
- 始终公开 per-training-seed 和 raw episode records，不只给 pooled 均值。

100 个 evaluation episodes 使单个二元比例最坏情况下的普通 binomial standard error
约为 0.05；5 个训练 seeds 仍只属于资源受限的首轮研究设计，因此必须保留完整 seed
离散性，不能把 500 个 episode 当成 500 个独立训练重复。

## 4. 候选 cost budget

三个条件都使用 PPOLag，以保持优化后端一致；每个条件显式声明
`lagrange_cfgs.cost_limit`：

| Condition | Candidate limit | 语义 |
|---|---:|---|
| Task only | `0.0` | selected learner cost 恒为 0 |
| Native cost | `25.0` | 每 1000-step episode 的期望 native hazard-cost steps |
| Gold STL cost | `0.1` | 每 1000-step episode 的期望 missed recovery obligations |

`25.0` 保留 OmniSafe/Safety-Gymnasium 常用 native-cost 参考预算，但现在是显式选择，
不再是静默继承默认值。`0.1` 表示每个 episode 平均 0.1 次 missed-obligation event；
它不能自动换算成 10% violation rate，因为每个 episode 的 triggered obligations 数量
不固定。两种 cost 的单位不同，因此这些数值不代表“数值相等的公平预算”；native
condition 是即时几何 control，gold-STL condition 是 temporal-event control。若后续
需要比较 Pareto frontier，应预先增加小范围预算 sweep，而不能看完结果后任意调参。

主要风险是 STL event 稀疏，`0.1` 可能造成 multiplier 更新方差大或使约束难以学习；
这正是 Stage I 需要测量的下游问题。不能在训练中静默换成 active/pending cost 或
robustness shaping。

## 5. 候选 matched training 尺度

pilot 训练预算固定为每个 condition/seed 1,000,000 transitions，10 个 vector env，
`steps_per_epoch=10,000`。这样每个 vector slot 每个 epoch 恰好运行一个完整 1000-step
episode，满足 OmniSafe epoch reset 不得清除 pending obligation 的约束。网络使用
OmniSafe PPOLag 的 64x64 actor/critic 基本设置；reward/cost 不归一化，observation
归一化。

这个预算仅是 pilot budget，而不是保证 policy 已收敛的理论值。训练曲线和最终
checkpoint 都保存；primary comparison 固定使用 final checkpoint，避免事后挑选最好
checkpoint。所有 condition 都用相同 deterministic policy mode 和相同 gold-STL
evaluator。若 1M steps 明显未进入稳定区，必须把“训练不足”作为 pilot 结果记录，再
通过新的 decision 修改预算。

## 6. 完整 pilot 前的工程 gate

以下工作不改变科学门槛，因此可以先完成：

1. PPOLag rollout 内产生至少一个真实 STL event cost；
2. cost 到 selected learner tensor 的一致性检查；
3. 显式 `cost_limit` 和 rollout/horizon alignment 校验；
4. checkpoint evaluation runner；
5. 每条评估轨迹由 independent direct oracle 重新计算；
6. completed windows 与 RTAMT robustness 在 `1e-9` 内一致；
7. 保存 episode-level machine-readable metrics。

## 7. 批准边界

负责人已经批准：30% safety reduction、10 percentage-point goal margin、5 个
training seeds、每 seed 100 个 paired evaluation episodes、10,000 次 hierarchical
bootstrap、三个 cost limit 和 1M-transition pilot budget。批准范围仅限 pilot。

现在应冻结 matched pilot configs 并运行 small-budget sanity。sanity 通过后必须停在
gate 汇报，不自动运行完整 1M。若任一冻结值被修改，应同时记录理由、算力影响、
统计解释和对 Stage II 公平比较的影响。
