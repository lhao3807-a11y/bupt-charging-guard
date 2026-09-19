# 后端改动任务书 · 契约 v1.3（交汤瑾睿）

> **发起** 吕浩　**日期** 2026-09-19　**契约** 已升至 **v1.3**（`docs/CONTRACT.md`）
> **背景** 第 1 周前端落地时发现契约有两处缺口，导致前端只能降级实现。按「先改契约 → 再动代码」的流程，
> 契约已先行更新，请据此改后端。
> **红线** 阈值一律从 `system_config` 读，严禁硬编码（契约 §7）；每个改动配测试，交付前 `pytest` + `ruff` 全绿。

---

## ⚠️ 状态更新（2026-09-19 审查后）

**任务 A / B 是第 1 周遗留未完成项，已重排为第 2 周必达。**

第 1 周审查实测：本任务书的 A、B 两项**后端均未实现**——
`GET /api/records?rule_hit=3` 仍返回 `rule_hit=1` 的记录，`GET/POST /api/vehicles` 均返回 **404**。
契约 §11 因此停在 **8/10**。

**根因不是"没人做"，而是"活没派到位"**：契约 v1.3 给 §11 加了这两条验收，
但 `PLAN_4WEEKS.md` §2.1/§2.2 的任务清单当时没同步（v1.0 写的），
你的第 1 周计划（任务 2.1–2.7）里看不到这两条。**已修订 PLAN v1.1**，补入任务 **2.8**（=本文任务 A）与 **2.9**（=本文任务 B）。

另请注意：PLAN §2.2 的 **2.1–2.4（CV 环境 / 数据集 / 检测 / 车牌识别）实测也未开工**
（`algo/dataset`、`algo/train`、`algo/recognize` 均不存在），而 CV 是第 2 周的关键路径。
请优先同步这两条线的阻塞情况。

---

## 任务 A · `GET /api/records` 增加筛选参数（契约 §6.4）

### 现状
`backend/app/routers/records.py` 只接受 `page` / `size`，全表分页。

### 要做的事

新增 **7 个可选**查询参数，**多参数之间为 AND**：

| 参数 | 类型 | 匹配方式 |
|---|---|---|
| `plate` | str | **模糊** `LIKE %..%`，忽略大小写 |
| `vtype` | `新能源` \| `燃油` | 精确 |
| `pile_id` | str | **模糊**，忽略大小写 |
| `rule_hit` | int 0–3 | 精确 |
| `notify_status` | `未提醒` \| `已提醒` \| `失败` | 精确 |
| `start_time` | ISO8601 或 `YYYY-MM-DD` | `occur_time >= start_time`（含） |
| `end_time` | ISO8601 或 `YYYY-MM-DD` | `occur_time <= end_time`（含） |

### 关键口径（容易做错，务必对照）

1. **`total` 必须是筛选后的总数**，不是全表总数 —— 前端分页条直接用它。先 `filter` 再 `count`。
2. **`end_time` 只给日期时按当日 23:59:59.999999 解释**。
   否则用户选「9-19 到 9-19」会查不到当天的数据，这是最常见的一个 bug。
   建议实现：若字符串长度为 10（`YYYY-MM-DD`），拼 ` 23:59:59.999999`。
3. **不传的参数不参与过滤**（`None` 即跳过），保证 v1.2 行为向后兼容。
4. 排序仍**按 `occur_time` 倒序**（可加 `id` 倒序做稳定次序）。
5. `start_time > end_time` 时返回空列表即可，不必报错。

### 验收

```bash
# 造几条不同规则的记录后
curl "http://127.0.0.1:8000/api/records?rule_hit=1"        # 只返回燃油占位，total 随之变化
curl "http://127.0.0.1:8000/api/records?plate=京A"          # 模糊匹配
curl "http://127.0.0.1:8000/api/records?start_time=2026-09-19&end_time=2026-09-19"  # 能查到当天
curl "http://127.0.0.1:8000/api/records"                    # 与 v1.2 行为一致
```

测试建议覆盖：单参数、多参数 AND、`total` 随筛选变化、`end_time` 同日包含、空结果。

---

## 任务 B · 新增车辆信息 CRUD 四端点（契约 §6.6）

### 为什么必须做
契约 §1.1 把「车辆信息管理」列为**第 1 周范围**，要求表格列 = `vehicle` 全字段且可增删改，
但 §6 从未定义 `vehicle` 的读接口 —— 前端只能退化为 `localStorage`（现已是这个状态）。
要真正达标必须补这组端点。

### 要做的事

| 方法 | 路径 | 入参 | 出参 |
|---|---|---|---|
| GET | `/api/vehicles` | `?page=&size=&plate=&vtype=&owner=` | `{items, total, page, size}`（`201` 无） |
| POST | `/api/vehicles` | `Vehicle`（不含 `created_at`） | `Vehicle`，状态码 **`201`** |
| PUT | `/api/vehicles/{plate}` | `VehicleUpdate` | `Vehicle` |
| DELETE | `/api/vehicles/{plate}` | — | **`204`**，无 body |

新增 Pydantic 模型（放 `backend/app/schemas.py`）：
- `Vehicle` —— 对应契约 §3.1 全字段：`plate` / `vtype` / `owner` / `phone` / `created_at`
- `VehicleCreate` —— `plate` / `vtype` / `owner` / `phone`（**无 `created_at`**，服务端生成）
- `VehicleUpdate` —— 仅 `vtype` / `owner` / `phone`（**无 `plate` / `created_at`**）
- `VehiclePage` —— `items` / `total` / `page` / `size`

### 关键口径（**三条都是坑**）

1. **`plate` 是主键，不可改**。
   `PUT /api/vehicles/{plate}` 的路径参数仅用于**定位**；
   请求体 `VehicleUpdate` 里**根本不含** `plate`，从类型上就杜绝改主键。
   前端编辑态车牌也是只读的。
2. **`POST` 时 `plate` 已存在 → 返回 `409`**（不要用 `400`）。
   前端靠状态码区分「车牌已存在」与其他校验错误。
3. **`DELETE` 不级联删违规记录，且 `occupation_record.plate` 不加外键约束**。
   —— 这条最重要。历史违规是**事实记录**，删车不该抹掉它；但删车后该车牌不再有手机号，
   **无法自动提醒**。前端删除确认弹窗已写明这一点。
   > ⚠️ 若给 `occupation_record.plate` 加 FK，删车要么失败、要么连带删除历史记录，**两种都错**。
   > 请确认 `models.py` 里该列**没有** FK 约束。

4. `created_at` 由**服务端**在 `POST` 时生成（`datetime.now()`），请求体不传。
5. 列表筛选：`plate` / `owner` 模糊，`vtype` 精确，`total` 为筛选后总数（同任务 A 的规则）。
6. 列表排序建议：`created_at` 倒序（新录入在前），与前端展示直觉一致。

### 验收

```bash
# 新增
curl -X POST http://127.0.0.1:8000/api/vehicles -H "Content-Type: application/json" \
  -d '{"plate":"京AD12345","vtype":"新能源","owner":"张伟","phone":"13800136621"}'   # → 201

# 重复车牌
# 同上再发一次 → 409

# 更新（只改车主/手机号，改不了车牌）
curl -X PUT http://127.0.0.1:8000/api/vehicles/京AD12345 -H "Content-Type: application/json" \
  -d '{"vtype":"新能源","owner":"张伟2","phone":"13900139000"}'                      # → 200

# 不存在 → 404
curl -X PUT http://127.0.0.1:8000/api/vehicles/京X00000 -H "Content-Type: application/json" \
  -d '{"vtype":"燃油","owner":"x","phone":"13800138000"}'                            # → 404

# 删除 → 204
curl -i -X DELETE http://127.0.0.1:8000/api/vehicles/京A12345

# 列表 + 筛选
curl "http://127.0.0.1:8000/api/vehicles?vtype=新能源&owner=张"
```

**删除不级联**要专门写一条测试：先给某车牌造一条 `occupation_record`，再删该车，
断言违规记录**仍在**。

---

## 任务 C · 数据库与种子

- `vehicle` 表结构**不变**（契约 §3.1），无需改 `schema.sql` 的 DDL。
- 种子数据（`seed_db`）建议补 2–3 辆，覆盖新能源/燃油两类，便于前端演示车型标签取色。
- 若种子里已有车辆，保持 `plate` 唯一即可。

---

## 交付检查表

```bash
./.venv/Scripts/python.exe -m pytest backend/tests -q      # 目标 ≥ 70（现 57）
./.venv/Scripts/python.exe -m ruff check backend scripts   # All checks passed
./.venv/Scripts/python.exe -m ruff format --check backend  # 已格式化
```

- [ ] 任务 A：7 个筛选参数 + `total` 随筛选变化 + `end_time` 同日包含
- [ ] 任务 B：4 端点；`409` / `404` / `204` / `201` 状态码正确
- [ ] `occupation_record.plate` **无 FK 约束**；删车不删违规记录（有测试）
- [ ] `PUT` 请求体不含 `plate`（类型层面就改不了主键）
- [ ] 新增测试覆盖以上全部口径，`pytest` ≥ 70 全绿
- [ ] `ruff` check + format 全绿
- [ ] commit（格式 `api: 记录筛选参数 + 车辆 CRUD 端点（契约 v1.3）`）并 push

---

## 完成后通知吕浩，前端会同步做两件事

1. **第 2 页筛选取代前端过滤** → 改为把筛选条件传给 `GET /api/records`（这样跨页筛选才正确）。
2. **第 1 页从 localStorage 切到 `/api/vehicles`** → 去掉页面顶部的「本地演示数据」警示条。

两处我已在代码里留好替换点（`frontend/src/stores/{records,vehicle}.ts` 顶部注释有说明）。
