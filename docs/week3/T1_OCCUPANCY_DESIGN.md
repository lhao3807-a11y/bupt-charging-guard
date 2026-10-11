# T1 · 占用标识与提醒行为设计（第 3 周 · 汤瑾睿）

> 状态：**汤瑾睿起草，待吕浩（L1）回签后并入 `docs/CONTRACT.md` 正式版**。
> 日期：2026-10-11。依据：`WEEK3_PLAN.md` §2 第 1/3/4/6 项口径、现行 `CONTRACT.md` v1.8。
> 本文只做设计与迁移草案，**不改业务代码**；实现落在 T2（提醒服务）与 T4（判重）。

---

## 1. 现状问题（为什么必须引入占用标识）

现行 `rule_engine.save_violation()` 的判重键是「同 `pile_id` + 同 `rule_hit` + `notify_status='未提醒'`」。
在「人工点击 → judge → notify」的第 1 周链路里够用，但第三周一旦**自动轮询**，会立刻暴露四个缺陷：

| # | 缺陷 | 触发场景 | 后果 |
|---|---|---|---|
| D1 | 已提醒后不再复用 | 自动轮询每 3 秒判定一次 | 同一次占用每轮新增一条记录 + 一次发送 → 记录爆炸、反复骚扰车主 |
| D2 | 换车被误合并 | A 车开走、B 车停入同一桩，命中同一规则 | B 车的违规被记到 A 车那条记录上，且因为「已提醒」不再提醒 B |
| D3 | 判重键依赖会被重置的时间 | 想用 `start_time` 做占用身份 | 模拟器在「空闲 → 充电中」时把 `start_time` 重置为当前时刻，身份当场丢失 |
| D4 | 发送次数不持久化 | 进程重启 / 并发重试 | 重启后次数清零，可无限重试；并发请求各发一次短信 |

**结论**：需要一个**与业务阈值、与桩状态流转都无关**的稳定占用标识（下称 `occupancy_id`）。

---

## 2. 占用标识设计

### 2.1 字段（两表各加一列）

| 表 | 新列 | 类型 | 说明 |
|---|---|---|---|
| `charging_pile` | `occupancy_id` | `VARCHAR(40) NULL` | **本次占用**的标识；无车占用时为 `NULL` |
| `occupation_record` | `occupancy_id` | `VARCHAR(40) NULL` | 落库时从桩上**快照**下来，之后**永不改写** |

两处都可为 `NULL`：历史数据与「直接手写桩状态、未经绑定」的场景（如部分现有测试与 MySQL 直灌数据）不受影响。

### 2.2 生成规则

```
occupancy_id = f"{pile_id}@{arrival:%Y%m%d%H%M%S%f}"
# 例：PILE-003@20260908100000123456
```

- **确定性**：只由「桩 + 绑定时刻」决定，不掷随机数、不依赖进程状态 —— 同一输入必然同一输出（T5「同样输入和时刻得到同样结果」的前提）。
- **微秒精度**：保证「离车 → 立刻重入」不会被算成同一次占用。
- 长度上限 40：`PILE-003` 这类 8 字符桩号 + 21 位时间戳 = 30 字符，留有余量。

### 2.3 生命周期（唯一入口 `app/occupancy.py`）

| 事件 | 处理 | `occupancy_id` |
|---|---|---|
| **到车绑定** `begin_occupancy(pile, plate, at)` | 写 `bound_plate` / `start_time=at` / `status=空闲` | 新生成 |
| 同车仍在（`bound_plate` 未变） | 只更新 `start_time` 等时间字段 | **保持不变** |
| **换车**（`bound_plate` 变成另一块牌） | 视为一次新占用 | 新生成 |
| **离车释放** `end_occupancy(pile)` | 清 `bound_plate` / `start_time` / `end_time`，`status=空闲` | 置 `NULL` |

> **为什么「到车」不改桩状态为充电中**：能否充电由充电桩（模拟适配器）决定，不是「停上去了」就等于充电；
> 规则②「停着不充电」正是靠 `status=空闲` 才判得出来。

---

## 3. 判重与提醒行为真值表

### 3.1 判重键（T4 实现）

```
去重键 = (pile_id, occupancy_id, rule_hit)
```

- **不再看 `notify_status`**：已提醒 / 发送失败都属于「同一次占用的同一条规则」，必须复用同一条记录。
- `occupancy_id` 为 `NULL` 的历史行只与 `NULL` 行相互匹配（SQL `IS NULL` 语义），不会与新数据串。
- 复用时 **保留首次 `occur_time`**，不刷新 —— `occur_time` 是「违规首次发生时刻」，被反复刷新会让
  第 2/4 页的时间维度失真（对应验收 A08「历史不被重写」）。

### 3.2 行为真值表

| # | 场景 | 记录 | 发送 |
|---|---|---|---|
| S1 | 同车持续占用，连续判定 10 次 | 1 条（首次 `occur_time` 不变） | **至多 1 次成功** |
| S2 | 已提醒后再判定 | 复用原记录 | **不再发送**（`already_sent`） |
| S3 | 发送失败后再判定 | 复用原记录 | 再尝试，累计 `notify_attempts` |
| S4 | 尝试达上限（3 次）后 | 记录保持 `失败` | 不再自动发送，返回 `exhausted` |
| S5 | 同桩换车（另一块牌） | **新 1 条** | 新记录走一次完整发送 |
| S6 | 离车后重入（同车/异车） | **新 1 条** | 新记录走一次完整发送 |
| S7 | 规则变化（如久停 → 充满超时） | **新 1 条**（`rule_hit` 变了） | 新记录走一次完整发送 |
| S8 | 两个请求并发点同一条 | 1 条 | **至多 1 次成功**，另一个返回 `conflict` |
| S9 | 进程重启后重新判定 | 1 条 | 已成功的不重发；失败次数**不清零** |

---

## 4. 提醒发送与恢复（T2 实现）

### 4.1 持久化字段

| 表 | 新列 | 类型 | 说明 |
|---|---|---|---|
| `occupation_record` | `notify_attempts` | `TINYINT NOT NULL DEFAULT 0` | 已尝试次数，**重启不清零** |
| `occupation_record` | `notify_error` | `VARCHAR(120) NULL` | 最近一次失败原因（人话，可直接展示） |

### 4.2 发送流程 `notification.send_for_record()`

```
读记录 → 已成功？──是──▶ 返回 already_sent（不重发）
        ↓ 否
   尝试数 ≥ 上限？──是──▶ 返回 exhausted（不发送）
        ↓ 否
   乐观锁占位：UPDATE ... SET notify_attempts = n+1 WHERE id=? AND notify_attempts=n
        ↓ rowcount == 0 → 返回 conflict（并发请求已被另一方处理）
   取车主手机号 → 缺失/车已删？──是──▶ 记 失败（原因：车主未绑定手机号），返回
        ↓ 有号
   调沙箱发送器（确定性）──成功──▶ 已提醒 + notify_time + 清 notify_error
                          └失败──▶ 失败 + notify_error（保留 notify_status=失败）
```

- **上限来源**：环境变量 `NOTIFY_MAX_ATTEMPTS`（默认 3）。**刻意不进 `system_config`** ——
  那张表是「业务判定阈值」的唯一来源（契约 §7 红线），发送尝试上限属部署配置。
- **并发保护**：`UPDATE ... WHERE notify_attempts = n` 的 `rowcount` 判定（乐观锁），
  不依赖 SQLite 不支持的行级锁，MySQL 8 下同样成立。
- **日志字段**：`record_id` / `occupancy_id` / `rule_hit` / `phone`（脱敏 `138****0001`）/ `attempt=n/3` / `result`。

---

## 5. 迁移与兼容

### 5.1 DDL（MySQL 8，已并入 `backend/sql/schema.sql`）

```sql
ALTER TABLE charging_pile
  ADD COLUMN occupancy_id VARCHAR(40) NULL COMMENT '本次占用标识（到车生成/离车清空）' AFTER bound_plate,
  ADD KEY idx_pile_occupancy (occupancy_id);

ALTER TABLE occupation_record
  ADD COLUMN occupancy_id   VARCHAR(40)  NULL COMMENT '落库时快照的占用标识，永不改写' AFTER pile_id,
  ADD COLUMN notify_attempts TINYINT     NOT NULL DEFAULT 0 COMMENT '已尝试发送次数（重启不清零）' AFTER notify_time,
  ADD COLUMN notify_error    VARCHAR(120) NULL COMMENT '最近一次发送失败原因' AFTER notify_attempts,
  ADD KEY idx_occ_occupancy (occupancy_id);
```

### 5.2 回退

```sql
ALTER TABLE charging_pile    DROP KEY idx_pile_occupancy, DROP COLUMN occupancy_id;
ALTER TABLE occupation_record DROP KEY idx_occ_occupancy,
  DROP COLUMN occupancy_id, DROP COLUMN notify_attempts, DROP COLUMN notify_error;
```

> ⚠️ **Git 回滚 ≠ 数据库回滚**：回滚代码不会自动 `DROP COLUMN`。新增列**全部可空或有默认值**，
> 旧代码在带新列的库上仍可运行（向前兼容），可先回滚代码再择机回退 DDL。

### 5.3 历史数据

`occupancy_id` 为 `NULL` 的历史记录**保持 `NULL`**，不回填 —— 回填等于凭空编造占用身份。
它们仍可被查询与统计，只是不参与新的占用判重（判重键含 `occupancy_id`，`NULL` 只匹配 `NULL`）。

---

## 6. 验证方式（由下列用例钉死）

| 设计点 | 测试用例 |
|---|---|
| 到车/换车/离车生成与清空 | `backend/tests/test_occupancy.py` |
| S1/S2/S3/S5/S6/S7 判重 | `backend/tests/test_rule_engine_edge.py::test_*occupancy*` |
| S1 连续 10 次只 1 条 1 发 | `backend/tests/test_pipeline.py::test_ten_rounds_one_record_one_send` |
| S4 上限 / S8 并发 / S9 重启 | `backend/tests/test_notification.py` |
| 迁移 DDL 在 MySQL 8 生效 | `scripts/verify_mysql.py` 第 20–24 项（T7） |
