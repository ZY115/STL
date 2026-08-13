# Stage I 固定策略空间轨迹诊断报告

- **日期：** 2026-08-12
- **范围：** 已完成的 15 个 Stage I final checkpoint；仅复放和诊断，不训练、不选 checkpoint
- **输入：** 3 conditions × 5 training seeds × 100 paired evaluation seeds
- **输出：** 1,500 episodes、1,501,500 reset/action samples、3 张固定图

## 1. 验证结论

空间复放完整通过。15 个 checkpoint 的 SHA-256 与成功 manifest 一致；每个回合的
长度、return、native cost、Gold trigger/recovery/deadline/terminal 事件与冻结评估表
一致。online monitor、独立 oracle 与 RTAMT 的既有一致性结果没有改变。

为取得真实二维坐标，代码用同一 seed 和同一 policy action 同步运行一个只供诊断的
raw Safety-Gymnasium twin。policy 始终只接收原公开 observation；agent、hazard 和
goal 坐标不进入 policy、cost 或语言模型。两个 simulator 的公开 observation 最大差
`9.54e-7`，在 float32 twin 容差内；公开 lidar 距离与
`min(3.0, privileged nearest-center distance)` 最大差 `1.78e-15`。

完整 `full_geometry.csv.gz` 有 1,501,500 行、140,953,788 bytes，SHA-256 为
`7e0fe9c2c7f5c7f227812dbd15895051767762f817124fda0958c2744e62fb30`。它保持本机
并被 Git 忽略；schema、命令、行数、hash 和 compact summaries 已留存。

## 2. 图表与代表性案例

规定的三组案例在画图前由冻结 episode table 决定：

| 行 | training/evaluation seed | 选择规则 |
|---|---|---|
| Gold worse | `4404 / 10066` | Gold-minus-task missed 最大 |
| Gold better | `2202 / 10031` | task-minus-Gold missed 最大 |
| Median | `1101 / 10001` | 绝对差最小，再按 seed 固定 tie-break |

图表位于 `results/post_pilot_spatial_diagnosis/`：

- `paired_top_down_trajectories.png`：真实 agent 路径、8 个 hazard、goal resampling、
  warning/recovery/violation/terminal 事件；每次 goal 更新单独分段；
- `event_spatial_density.png`：三个条件的 occupancy、warning、recovery 和 violation
  空间计数；
- `layout_feasibility.png`：100 个固定 layout 中，地图落在所有 hazard-centered
  disks 之外的比例。

三张图已人工检查：边界、hazard 半径、warning/safe 圆、goal 分段和事件 marker
可辨认，没有坐标错位或空 panel。极端行只用于解释差异形态，不作为总体因果证据。

## 3. 主要空间结果

### 3.1 Gold policy 是否采取明显不同的路线

个别固定案例中，三个独立训练策略的具体路径明显不同；但 aggregate 和 median
证据不支持“Gold 学会了一个稳定的新绕行模式”。task-only 与 Gold 的平均路径长度
几乎相同（`18.592` 与 `18.613`/episode），distance-band crossings 也几乎相同
（`32.436` 与 `32.236`/episode）。两者的 occupancy/event maps 都覆盖地图内部的
相似宽区域。

相反，native-cost policy 的路径较短（`14.347`/episode）、band crossings 较少
（`22.754`/episode），warning-zone sample fraction 也较低（`25.65%`，task/Gold
分别为 `32.36%/31.77%`）。这是已训练策略的描述性差异；它不能单独证明 native
cost 导致了该空间行为。

### 3.2 是否 oscillate 或停留在重叠 warning/safe 区域

task-only/Gold 每回合约有 `32.44/32.24` 次 warning、hysteresis、safe 三个距离带
之间的切换；Gold 没有比 task-only 明显减少这种往返。其 hysteresis-band sample
fraction 也接近（`15.46%` vs `15.40%`）。代表性图中可见多段进入、离开并再次进入
多个相互重叠的 `d_warn/d_safe` 圆；aggregate warning/recovery density 不是单一障碍
或单一区域热点。

因此，本诊断支持“反复跨越距离带仍普遍存在”，但不把所有 crossing 都称为控制
振荡：goal 会在 1,000-step 回合内多次重采样，合法的跨地图导航也会产生 crossing。

### 3.3 violation 是否集中在 goal change 或 episode truncation 附近

使用每个 goal event 前后各 20 steps 的预声明窗口，missed obligations 落在窗口内的
比例为 task/native/Gold `30.48%/26.09%/32.37%`；但全部 action steps 落在这些窗口
内的比例更高，分别为 `45.18%/30.50%/44.45%`。事件比例除以暴露比例为
`0.675/0.855/0.728`，均未显示 goal-change 邻域富集。空间 density 也呈分散分布。
这只是邻近性诊断，不是独立样本的显著性检验或因果估计。

episode truncation 会按 Gold terminal semantics 结算 active obligation；terminal
unresolved 占全部 missed obligations 的 task/native/Gold
`19.86%/16.09%/20.65%`。所以约五分之一的 missed cost 明确发生在回合边界，其余
主要是回合内 deadline violation，不能把整体失败归因于 timeout。

### 3.4 `d_safe=0.55` 之外还剩多少地图

在每个固定 layout 上用 `301×301` 网格估计：

| 区域定义 | 平均可用比例 | 最小--最大 |
|---|---:|---:|
| 所有 physical `r=0.20` disk 外 | `88.91%` | `88.88--88.99%` |
| 所有 warning `r=0.45` disk 外 | `54.63%` | `49.47--62.23%` |
| 所有 safe `r=0.55` disk 外 | `41.43%` | `33.01--52.32%` |

物理 hazard disks 只排除约 `11.1%` 的采样地图，而 `d_safe` disks 联合排除约
`58.6%`。这说明 `0.55` center-distance rule 在八障碍小地图中是一个覆盖范围很大的
时序要求，不等同于原生物理碰撞边界。

### 3.5 环境是感知简单、但规则几何是否不匹配

感知侧确实简单且已验证：公开 `hazards_lidar` 可确定性地重建 capped nearest-center
distance，不需要 camera、object detector 或 learned grounding。困难主要不是信号
噪声。

几何侧则存在明显 tension：八个 `d_safe=0.55` 圆只留下平均 `41.4%` 的地图，且多个
圆重叠；goal 会重采样到需要反复穿越这些区域的路线。该设计适合制造足够多的
bounded-recovery obligations，却不代表与 benchmark 原生 `r=0.20` hazard cost 或
goal navigation 天然同尺度。这是 rule/benchmark alignment 的诊断事实，不是修改
Gold rule 或宣称环境不可解的依据。

## 4. 与 Stage I 失败结果的一致解释

空间 replay 与冻结统计一致：task/native/Gold 的 missed-per-trigger 分别为
`25.85%/29.65%/26.03%`。Gold 相对 task-only 的 path length、band crossings、warning
exposure 和空间 event pattern 都没有 material 改变，这与 pilot 未达到 30% safety
reduction 的结果相符。该证据加强了“binary delayed event cost 没有塑造出明显不同
策略”的机制假设，但仍不能把单一原因形式化识别为因果根因。

## 5. Stage II real-policy corpus

从上述已验证 full table 中，按每个 condition × training seed 的四个 outcome strata
（no missed、single deadline、multiple deadline、terminal unresolved）各选最低
evaluation seed，固定得到 60 个不同回合、60,060 samples。选择在任何 Stage II
模型结果之前完成。

40 个规格 × 60 条 real traces 的 2,400 个组合均在构建器内部完成 machine review；
所有 direct/online/RTAMT checks 的最大差为 0。只把 train/validation 对应的 1,680 条
Gold label records 写入 model-visible artifact。held-out labels 没有写出或释放，因为
35 条新规格仍等待独立人工复核。

## 6. Gate 状态

Work Package A 已通过：复放、几何验证、三张图、aggregate/median 解释、provenance
和固定 60-episode real corpus 均完成。下一步本应继续 Stage II-A 与 D38 Gold-cost
GPU preflight；但同一晚 T5 训练出现重复 kernel MCE，当前所有新 GPU training 已按
技术停止条件冻结。CPU-only tests、文档与 review package 仍可继续。
