# T6 · 规则终版真值表与评审记录（第 3 周 · 汤瑾睿）

> 日期：2026-10-11。依据：`CONTRACT.md` v1.9 §3.6 / §6.2 / §6.3、`docs/week3/T1_OCCUPANCY_DESIGN.md`、
> `WEEK3_PLAN.md` §5 的 A01–A13。
> 状态：**汤瑾睿已自评并给出全部行为测试**；吕浩（L1 契约 / L5 统计）、吴和庆（W1 文案）**待回签**。
> 回签未完成前，本表不作为「三人确认」的证据，只作为评审材料。

---

## 1. 四条规则判定真值表

输入：`RecognitionResult{plate, vtype}` + 库里的 `charging_pile` 状态 + `system_config` 阈值。
判定时刻取 `RecognitionResult.frame_time`（引擎不读系统时钟）。

| # | 车型 | 桩 `status` | 时间条件 | `rule_hit` | 说明 |
|---|---|---|---|---|---|
| 1 | 燃油 | 任意（空闲/充电中/已充满） | 无 | **1 燃油占位** | 只看车型，与桩是否在充电无关 |
| 2 | — | 桩为空（`bound_plate` 查不到） | 无 | **None（不判定）** | 车不在充电位上，不在本系统范围 |
| 3 | 新能源 | 空闲 | `now − start_time > abnormal_park_min` | **2 异常占位** | 严格大于 |
| 4 | 新能源 | 空闲 | `≤ abnormal_park_min`（含相等） | None | 阈值前/相等都不提醒 |
| 5 | 新能源 | 空闲 | `start_time` 为空 | None | 无到达时间，无法判久停 |
| 6 | 新能源 | 已充满 | `now − end_time > full_timeout_min` | **3 充满未移车** | 严格大于 |
| 7 | 新能源 | 已充满 | `≤ full_timeout_min`（含相等） | None | 同上 |
| 8 | 新能源 | 已充满 | `end_time` 为空 | None | 无充满时间，无法判超时 |
| 9 | 新能源 | 充电中 | 无 | None | **规则④ 正常**：不落库、不提醒 |
| 10 | — | `frame_time` 早于基准时间 | 时长按 0 | None | 时钟回拨不误判、不抛错 |

**不可判定的情况一律返回 `None`，不猜、不兜底**：

| 情况 | 处理 | 为什么 |
|---|---|---|
| 车牌未绑定任何桩 | `None` | 不在本系统范围，不是错误 |
| 同一车牌绑了两个桩 | `MultipleResultsFound` **抛错** | 静默挑一个 = 替运维做决定，第 2 页的桩 ID 可能与另一半数据对不上 |
| 车未录入 `vehicle` 表 | 编排侧**不落库** | 车型决定命中①还是③，猜一个就是往库里写假数据 |
| `system_config` 缺阈值 | `ConfigMissingError`（接口 500） | 契约 §7：严禁硬编码兜底 |
| 阈值非整数 | `ConfigMissingError` | 同上，且要说出是哪个键 |

---

## 2. 配置变更语义（A08）

| 场景 | 行为 | 依据 |
|---|---|---|
| 改 `abnormal_park_min` / `full_timeout_min` | **只影响后续判定** | 历史是「当时按当时阈值判出的证据」 |
| 已落库的记录 | `rule_hit` / `occur_time` / `notify_status` / `notify_attempts` / `pile_id` **一律不变** | 回溯重算等于把证据改没了，第 2/4 页数字会随配置漂移 |
| 已成功提醒的记录 | 改阈值后重新判定也**不再发送**（`already_sent`） | 历史结果不被新一轮判定推翻 |
| 仍在占用的车 | 下一次判定**立刻用新阈值**（放宽→不再命中；收紧→命中） | A08 的另一半 |
| 收紧阈值后命中同规则 | **复用**已有记录，不新增 | 判重键 `(pile_id, occupancy_id, rule_hit)` 没变 |

---

## 3. 提醒语义（与 T2/T4 同源，此处只做汇总）

| 场景 | 记录 | 发送 |
|---|---|---|
| 同次占用连续判定 N 次 | 1 条（首次 `occur_time` 不刷新） | 至多 1 次成功 |
| 已成功 | 复用 | 不重发，`already_sent=true` |
| 发送失败 | 复用 | 重试并累加 `notify_attempts` |
| 达 `NOTIFY_MAX_ATTEMPTS`（默认 3） | 保持 `失败` | `exhausted=true`，不再自动发 |
| 缺手机号 / 车主已删除 | 保持原记录 | 记 `失败` + 原因，**不消耗次数**，补绑定后仍可重试 |
| 两个请求并发 | — | 乐观锁，只有一个真正发送，另一个 `conflict` |
| 进程重启 | — | 次数与结果持久化，不清零、不重发已成功的 |
| 正常（规则④） | 不落库 | **不调用发送器** |

---

## 4. 行为测试索引（本节全部为**实测通过**，见 CI 输出）

| 语义 | 测试 |
|---|---|
| 真值表第 1/3/6/9 行 | `backend/tests/test_rule_engine.py` |
| 第 2/4/5/7/8/10 行（边界） | `backend/tests/test_rule_engine_edge.py` |
| 判重与占用标识（S1–S7） | `backend/tests/test_occupancy.py`、`test_rule_engine_edge.py` |
| 提醒语义（成功/失败/上限/并发/重启） | `backend/tests/test_notification.py` |
| 配置变更语义 | `backend/tests/test_rule_review.py` |
| 自动闭环与「无新帧仍重判时间」 | `backend/tests/test_pipeline.py` |
| 四场景与适配器 | `backend/tests/test_charging_adapter.py` |

---

## 5. 评审结论与待回签项

已确认（汤瑾睿，2026-10-11）：

- [x] 四条规则的判定条件与边界（第 1 节真值表 10 行 + 5 类不可判定）
- [x] 配置变更「不回溯历史 + 新判定用新阈值」
- [x] 缺参数不静默兜底（引擎抛错、接口 500 并带键名）
- [x] 提醒语义（第 3 节 8 行，含重复保护与失败恢复）

待回签（**未回签前本表不作为三人确认证据**）：

- [ ] 吕浩：契约 v1.9 §3.6 / §6.2 / §6.3 / §6.11 与前端文案（`frontend/src/types/contract.ts` 需同步
      `occupancy_id` / `notify_attempts` / `notify_error` 三个新字段与 `already_sent` 等四个标志）
- [ ] 吴和庆：第 2 页「失败原因 / 已达上限 / 处理中」文案是否与 `notify_error` 的取值一致
      （当前取值：`车主未绑定手机号` / `车主信息不存在（车辆已删除）` / `沙箱发送失败` / `已达发送尝试上限`）
- [ ] 三人：第 1 节第 2 行「桩为空 → None」是否需要在第六页显示「未绑定桩」而非「正常」
