# 批次占用 + 热异构：能否在自热下造出 C1？

日期：2026-11-03（Asia/Shanghai）。相对 `docs/notes/dynamic_thermal_cost_claims.md`（纯 dynamic 失败：free ≲ place_once，四星同步节流）。

假设（用户）：(a) 优先成批占用 / 允许部分空闲，使升温不同步（相位错开）；(b) 轻度 per-node 热曲线异构，避免全员同时节流后动作空间为空。

## 改了什么（可配置，无硬编码魔法）

| 旋钮 | 位置 | 作用 |
|---|---|---|
| `placement.mode: pack` | base | 初次放置优先填已占用节点 |
| `placement.max_busy_nodes: 2` | base | 未满 KV 前最多开 2 个忙节点，强制留空闲冷却星 |
| `R_th_by_node` / `tau_s_by_node` / `T0_C_by_node` / `sun_bias_C_by_node` | thermal | 轻度异构；`sun_bias_C` 加到 Teq |

实现：`_placement.py`、`DynamicThermal`、`schema` 准入。实验：

- `exp_ring_s1_dynamic_batch_hetero_v1`（pack+hetero，主假设）
- `exp_ring_s1_dynamic_batch_v1`（仅 pack）
- `exp_ring_s1_dynamic_hetero_v1`（仅异构、balance）

seeds 1–3；工作负载对齐 s1 v3。

## 结论（诚实）

**是：在 pack / max_busy 下，free ≫ place_once 的 C1 向差距出现。**  
**针是批次化占用（pack + max_busy_nodes），不是异构 alone。**

- **仅异构**：仍失败（free −44% good_long），四星均节流（n_thr=4）。
- **仅 pack**：C1 出现（free good_long 6.67 vs 首次 1，+567%）；place_once 侧 n_thr≈1.3（凉快星存在但迁不走）。
- **pack+异构**：C1 更干净（free 10 vs 1，+900%）；相对仅 pack，free 再抬一截；且 random 掉回 free 之下（C2 方向恢复）。

但请注意：

1. **差距主要来自 place_once 塌到 ~1**（热堆在 1–2 星），不是 free 追上显式基线的 19.2。
2. 绝对 free good_long≈10、goodput_slo≈193，仍低于显式 `t_swap` 表（19.2 / 356）。
3. raw req/s·tok/s 仍全臂持平（请求都在 drain 内完成）。
4. 仅 pack 时 random 反超 free（C2 叙事脏）；加上轻度异构后 random < free。

## 表（seeds 1–3 均值；基线 place_once；% 相对基线）

### 对照：纯 dynamic（`exp_ring_s1_dynamic_thermal_v1`）

| 臂 | good_long ↑ | goodput_slo ↑ | tok/s | peakT °C | thr_s Σ | n_thr |
|---|---|---|---|---|---|---|
| place_once | 12.0 | 228.4 | 254.9 | 86.7 | 1599 | 4.0 |
| free | 8.67 (−28%) | 169.1 (−26%) | 254.9 | 86.7 | 1583 | 4.0 |
| random | 3.0 (−75%) | 68.4 (−70%) | 254.9 | 86.7 | 1533 | 4.0 |

### 仅异构（`exp_ring_s1_dynamic_hetero_v1`）

| 臂 | good_long ↑ | goodput_slo ↑ | tok/s | peakT °C | thr_s Σ | n_thr |
|---|---|---|---|---|---|---|
| place_once | 12.0 | 228.4 | 254.9 | 86.8 | 1600 | 4.0 |
| free | 6.67 (−44%) | 133.6 (−42%) | 254.9 | 86.9 | 1589 | 4.0 |
| random | 5.0 (−58%) | 103.9 (−54%) | 254.9 | 86.8 | 1526 | 4.0 |

### 仅 pack（`exp_ring_s1_dynamic_batch_v1`）

| 臂 | good_long ↑ | goodput_slo ↑ | tok/s | peakT °C | thr_s Σ | n_thr |
|---|---|---|---|---|---|---|
| place_once | 1.0 | 32.8 | 254.9 | 86.7 | 925 | 1.3 |
| **free** | **6.67 (+567%)** | **133.6 (+307%)** | 254.9 | 86.7 | 1564 | 4.0 |
| random | 10.67 (+967%) | 204.7 (+524%) | 254.9 | 86.7 | 1576 | 4.0 |

（random > free：C2 方向反了。）

### pack + 异构（`exp_ring_s1_dynamic_batch_hetero_v1`）★

| 臂 | good_long ↑ | goodput_slo ↑ | tok/s | peakT °C | thr_s Σ | n_thr |
|---|---|---|---|---|---|---|
| place_once | 1.0 | 32.8 | 254.9 | 86.7 | 858 | 1.3 |
| **free** | **10.0 (+900%)** | **192.8 (+488%)** | 254.9 | 86.8 | 1561 | 4.0 |
| random | 6.0 (+500%) | 121.7 (+271%) | 254.9 | 86.8 | 1563 | 4.0 |

- C1：free ≫ 首次（相对 % 大，但首次绝对分很低）。
- C2：random 相对 free goodput 约 −37%。

## 哪个旋钮动了针？

1. **`placement.pack` + `max_busy_nodes=2`**：主因。制造「暗星旁有亮/凉快星」——place_once 粘在热堆上，free 能迁走。
2. **轻度 `*_by_node` 异构**： alone 无效；叠在 pack 上抬 free（6.67→10）并理顺 C2。
3. 拧 `tau/R_th/T_throttle`  alone 仍不够（见前一篇 notes）。

## 跑

```bash
.venv/bin/satsim configs/exp_ring_s1_dynamic_batch_hetero_v1.yaml
.venv/bin/satsim configs/exp_ring_s1_dynamic_batch_v1.yaml
.venv/bin/satsim configs/exp_ring_s1_dynamic_hetero_v1.yaml
```

## 补充问题 / 开放问题

pack+hetero 已能造出相对 % 很大的 free ≫ place_once，但机制与「公平 C1」是否同构仍未闭合。记下待答：

1. **place_once 塌缩 vs 公平 C1**  
   本 run 的相对增益主要来自 place_once good_long 塌到 ~1（热堆粘在 1–2 星），而非 free 相对「健康首次」抬升。这算不算论文可用的 C1？还是必须要求 place_once 仍保持合理绝对分、free 再拉开？

2. **free 离显式 `t_swap` 还要多近**  
   显式基线 free≈19.2 / goodput≈356；本动态 pack+hetero free≈10 / ≈193。差距应归因于缺显式暗/亮不对称、二值功率、还是 pack 本身的容量上限？要把 free 推到什么绝对区间才算「追上叙事」？

3. **pack 松紧**  
   `max_busy_nodes=2`（四星环）是否过紧？试 1 vs 2 vs 3：塌缩会否消失、C1 是否仍在、空闲冷却星是否仍够？

4. **异构幅度**  
   当前轻度 `*_by_node` / `sun_bias`  alone 无效、叠 pack 才抬 free 并理顺 C2。加大异构会否 alone 奏效？或过强把随机臂也「碰巧」变好/变差？

5. **batch 语义：真连续批 vs `max_busy_nodes`**  
   现实现是放置策略上限忙节点数，不是真实 continuous-batch / 共享 KV 语义。论文若写「批次占用」，审稿人是否要求更贴近真实批调度？若要，引擎缺口在哪？

6. **C2 干净度**  
   仅 pack 时 random > free（C2 反了）；加轻度异构后 random < free。该 C2 是否稳定（更多 seeds / 扰动）？random 掉分是迁移代价还是热路径噪声？

7. **下一步实验（优先草稿）**  
   - 扫 `max_busy_nodes` ∈ {1,2,3} ×（有/无 hetero）  
   - 对照：同 pack 下显式 `t_swap` vs dynamic，拆绝对分差距  
   - 若叙事需要「非塌缩 C1」：抬 place_once（更松 pack 或负载比例功率）再看 free 是否仍领先  
   - 可选：真·连续批或负载连续功率，验证 batch 语义假设
