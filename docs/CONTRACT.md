# CONTRACT.md — 接口与数据契约（唯一事实源）

> **版本**：**v1.4**（2026-09-19 · 新增 §3.5 显示列名映射表，表格列名收归契约）
> **负责人**：吕浩（起草与维护）
> **确认人**：吕浩 / 汤瑾睿 / 吴和庆 —— v1.0 已逐条确认并签字，v1.1–v1.4 为增量变更
> **适用范围**：第 1 周最小闭环。任何结构变动 → 先改本文件 → @全员 + 升版本号，**禁止私自改自己那侧**。

---

## 1. 项目范围与 MVP

- **一句话**：用"计算机视觉 + 充电桩状态"融合，自动识别燃油车占位 / 新能源充满未移车，并主动提醒车主，形成"识别—判断—提醒"闭环。
- **形态**：演示系统原型（校园场景），完整跑通业务闭环，不做生产部署。
- **MVP 边界**：
  - 充电状态用**模拟数据**，预留 OCPP 适配层，不接真实运营商接口。
  - 第 1 周 CV 用**识别桩 stub**（读标注 JSON），短信用**沙箱**（写库 + 日志），后续替换为 YOLOv8 + HyperLPR / 真实短信 API。
  - 第 1 周**不卡准确率与响应时间指标**，闭环优先。

### 1.1 后台页面清单（6 页）

来源：开发大纲 M7「后台管理平台（Web）」。**吴和庆据此出设计基线与线框，吕浩据此实现前端路由**。

| # | 页面 | 数据来源 / 对应接口 | 第 1 周范围 | 完整实现 |
|---|---|---|---|---|
| 1 | 车辆信息管理 | `vehicle` 表（见 §6.6 CRUD） | **做** | 第 1 周 |
| 2 | 违规记录查询 | `GET /api/records` → `occupation_record` | **做**（Demo 验收项，见 §11） | 第 1 周 |
| 3 | 充电状态展示 | `charging_pile` 表（模拟数据） | **占位路由**（见下方口径） | 第 2 周 |
| 4 | 报警统计 | `occupation_record` 按 `rule_hit` / 时间聚合 | **占位路由** | 第 2 周 |
| 5 | 系统参数配置 | `system_config` 表（`full_timeout_min` / `abnormal_park_min`） | **占位路由** | 第 2 周 |
| 6 | 实时识别预览 | 预留端点 `GET /api/frame/latest`（见 §6.5） | **不做，仅预留导航占位** | 第 3 周 |

**「第 1 周范围」列的口径（v1.3 对齐 `PLAN_4WEEKS.md` §2.1 任务 1.8，2026-09-19 明确）**：

- **做** = 页面功能可用，纳入第 1 周末 Demo 验收。仅第 1、2 页属此列。
- **占位路由** = 路由与导航项就位、可点进、有标题与空态、**明确列出缺口与计划周次**，但**不实现业务功能**。
  第 3/4/5 页均属此列：这三页各自依赖一个**尚未定义的接口**（桩列表 / 统计聚合 / 参数读写），
  第 1 周全做等于「改 3 次契约 + 后端补 3 组接口 + 前端 3 页」，超出本周工期，故统一推迟至第 2 周。
- **不做** = 第 6 页，导航项 `disabled` 置灰，不纳入任何验收。

> **v1.3 修正说明**：v1.1–v1.2 曾将第 3/4/5 页标为第 1 周「做」，与 `PLAN_4WEEKS.md` §2.1
> 「3/4/5 页占位路由」的口径冲突。本版以 PLAN 为准统一表述，**消除两份文档打架**。

**约定**：
- 表格列以对应表的字段为准（如"车辆信息管理"的表格列 = `vehicle` 全部字段），吴出线框时直接照抄字段，不另发明。
- 第 6 页"实时识别预览"依赖预留端点，第 1 周 Demo **不验收**，前端可先留导航占位。
- 页面清单的任何增删 → 先改本节 → @全员 + 升版本号。

## 2. 开发基线（三人统一）

| 项 | 版本 | 说明 |
|---|---|---|
| Python | 3.11.x | 本机 3.11.9。**不要用 3.13** —— Ultralytics/PaddleOCR  wheels 支持滞后，第 2 周装模型会踩坑 |
| Node.js | 22 LTS | 本机 v22.22.2，npm 10.9.7 |
| 数据库（目标） | MySQL 8.0 | `backend/sql/schema.sql` 以 MySQL 8 语法为准，是交付物 |
| 数据库（开发期） | SQLite 3 | 本机未装 MySQL 8（验证方案见下方"第 0 天决策"）。开发期连 SQLite 文件库，数据访问走 SQLAlchemy，**第 2 周换 MySQL 只改连接串** |
| Git | 2.55+ | 主分支 `main`（已于第 0 天由 `master` 重命名） |

**开发期 SQLite 约束**：`vtype` / `status` / `notify_status` 在 MySQL DDL 里保留 `ENUM`，在 SQLAlchemy 模型中统一映射为 `String` + Pydantic 层 `Enum` 校验。禁止在业务代码里依赖数据库原生 ENUM 行为，否则换库必炸。

> **第 0 天决策 · MySQL 8 验证方案（三选一，已定方案 b，2026-09-08）**
>
> 本机未装 MySQL 8，汤瑾睿的分工任务 5.2.3"本地 MySQL 8 跑通 `schema.sql`"**调整为方案 b**：
> 1. `backend/sql/schema.sql` 仍以 **MySQL 8 语法**交付，是正式交付物；
> 2. 本地改用 **SQLite + SQLAlchemy 做等价验证**——建表、插种子、查询、规则引擎读取全部跑通，pytest 全过；
> 3. **MySQL 8 真机验证延至第 2 周**接入真实库时执行。若届时语法有差异，**以 `schema.sql` 为准修正代码，不改契约**。
>
> 风险已知：SQLite 不校验 MySQL 特有语法（如 `ENGINE=InnoDB`、部分 `ENUM` 行为），第 2 周真机接入时需补一轮验证。

## 3. 数据模型（核心四表）

### 3.1 vehicle（车辆信息）

| 字段 | 类型 | 说明 |
|---|---|---|
| plate | VARCHAR(15) PK | 车牌号 |
| vtype | ENUM('新能源','燃油') | 车型（由绿牌/蓝牌判定） |
| owner | VARCHAR(50) | 车主 |
| phone | VARCHAR(20) | 手机号 |
| created_at | DATETIME | 录入时间 |

### 3.2 charging_pile（充电桩状态，模拟）

| 字段 | 类型 | 说明 |
|---|---|---|
| pile_id | VARCHAR(20) PK | 桩 ID |
| status | ENUM('空闲','充电中','已充满') | 状态 |
| bound_plate | VARCHAR(15) | 绑定车牌（FK vehicle.plate） |
| start_time | DATETIME | 开始充电时间 |
| end_time | DATETIME | 充满时间 |

### 3.3 occupation_record（违规记录）

| 字段 | 类型 | 说明 |
|---|---|---|
| id | BIGINT PK AUTO_INCREMENT | ID |
| plate | VARCHAR(15) | 车牌 |
| vtype | ENUM('新能源','燃油') | 车型 |
| **pile_id** | VARCHAR(20) NULL | **桩 ID（v0.1 新增）**——违规记录需能关联到具体桩，否则后台统计缺维度 |
| rule_hit | TINYINT | 命中规则：1 燃油占位 / 2 异常占位 / 3 充满未移车 / 0 正常 |
| occur_time | DATETIME | 命中时间 |
| notify_status | ENUM('未提醒','已提醒','失败') | 提醒状态 |
| notify_time | DATETIME | 提醒时间 |

### 3.4 system_config（系统参数）

| 字段 | 类型 | 说明 |
|---|---|---|
| key | VARCHAR(30) PK | 参数键 |
| value | VARCHAR(50) | 参数值 |
| note | VARCHAR(100) | 说明 |

默认值：`full_timeout_min=30`（充满超时阈值）、`abnormal_park_min=30`（异常占位久停阈值）。

> 阈值一律从 `system_config` 读取，**严禁硬编码**。

### 3.5 显示列名映射表（**表格列名的唯一事实源**）

本节是「数据库字段 → 页面表格列名」的**唯一人工维护点**。线框表头、前端 `el-table-column` 的显示文案、以及 `check_tokens.py` 的列名白名单**全部由本表派生**，任何一方都不得自行定义列名。

**为什么需要它**：此前列名散落在契约 §3.x 说明档、`component-inventory.md`、线框表头、校验脚本白名单四处，且互为主从。2026-09-19 就出现过「第 2 页写『车牌号』、第 4 页写『车牌』」的三方分叉——因为脚本白名单与线框出自同一手，两边一起错时自动校验抓不到。**把判定权收回契约，是唯一能根治的做法。**

本表机器可读，`check_tokens.py` 按 `| 字段 | 列名 | 页面 |` 三列解析（页面列用 `P1`–`P6` 表示第几页）。

| 字段 | 列名 | 页面 |
|---|---|---|
| plate | 车牌号 | P1 |
| vtype | 车型 | P1 |
| owner | 车主 | P1 |
| phone | 手机号 | P1 |
| created_at | 录入时间 | P1 |
| id | ID | P2 |
| plate | 车牌 | P2 |
| vtype | 车型 | P2 |
| pile_id | 桩 ID | P2 |
| rule_hit | 命中规则 | P2 |
| occur_time | 命中时间 | P2 |
| notify_status | 提醒状态 | P2 |
| notify_time | 提醒时间 | P2 |
| plate | 车牌 | P4 |
| vtype | 车型 | P4 |
| pile_id | 桩 ID | P4 |
| rule_hit | 命中规则 | P4 |
| occur_time | 命中时间 | P4 |
| pile_id | 桩 ID | P3 |
| status | 状态 | P3 |
| bound_plate | 绑定车牌 | P3 |
| start_time | 开始充电时间 | P3 |
| end_time | 充满时间 | P3 |
| key | 参数键 | P5 |
| value | 参数值 | P5 |
| note | 说明 | P5 |

**三条约定（`check_tokens.py` 会断言）**：

1. **同表同字段必须同列名，跨表允许不同。** 例如 `plate` 在 `vehicle`（P1，台账语境）显示「车牌号」，在 `occupation_record`（P2/P4，事件语境）显示「车牌」——这是**有意为之**，不是分叉。判定粒度是「表 + 字段」。
2. **页面表格的每个表头都必须能在本表查到。** 「操作」列为跨页通用交互列，不在本表内，由脚本单独放行。查不到 = 自造字段或漏登记，直接失败。
3. **§3.1–§3.4 说明档的中文名必须与本表一致。** 防的是「契约自己两处漂移」：上表改了而 §3.x 没改（或反之）会被断言拦下。

> 改列名 → 先改本节 → @全员 + 升版本号 → 线框与前端随后对齐。**不允许只改线框不改本节。**

## 4. 识别结果 `RecognitionResult`

```json
{
  "plate": "京AD12345",
  "vtype": "新能源",
  "confidence": 0.97,
  "bbox": [120, 80, 200, 120],
  "frame_time": "2026-09-08T10:00:00"
}
```

- 真实 CV 与识别桩 stub **返回同一结构**，汤后续换模型时吕浩前端零改动。
- `bbox` 为 `[x, y, w, h]`。
- `frame_time` 为 ISO 8601 字符串。

## 5. 违规记录 `ViolationRecord`（API 返回 / 对应 occupation_record）

```json
{
  "id": 1,
  "plate": "京A12345",
  "vtype": "燃油",
  "pile_id": "PILE-001",
  "rule_hit": 1,
  "occur_time": "2026-09-08T10:00:05",
  "notify_status": "未提醒"
}
```

> `id` 为 v0.1 新增：前端需要它来定位记录、轮询/更新提醒状态。

## 6. API 端点

**闭环端点（识别—判断—提醒）**

| 方法 | 路径 | 说明 | 请求 → 响应 |
|---|---|---|---|
| POST | `/api/recognize` | 输入帧 → 识别结果（stub 读标注） | `FrameRef` → `RecognitionResult` |
| POST | `/api/judge` | 识别结果 → 违规判定（引擎内部查桩状态） | `RecognitionResult` → `ViolationRecord` \| `null` |
| POST | `/api/notify` | 违规 → 短信沙箱（写库+日志） | `ViolationRecord` → `NotifyResp` |
| GET | `/api/records` | 后台查询违规记录（分页 + 筛选，见 §6.4） | `?page=&size=&plate=&vtype=&pile_id=&rule_hit=&notify_status=&start_time=&end_time=` → `RecordPage` |

**后台数据端点（v1.3 新增，供第 1 页）**

| 方法 | 路径 | 说明 | 请求 → 响应 |
|---|---|---|---|
| GET | `/api/vehicles` | 车辆列表（分页 + 筛选） | `?page=&size=&plate=&vtype=&owner=` → `VehiclePage` |
| POST | `/api/vehicles` | 新增车辆 | `Vehicle` → `Vehicle`（`201`） |
| PUT | `/api/vehicles/{plate}` | 更新车辆（`plate` 主键不可改） | `VehicleUpdate` → `Vehicle` |
| DELETE | `/api/vehicles/{plate}` | 删除车辆（不级联删违规记录） | → `204` |

**预留 / 健康**

| 方法 | 路径 | 说明 | 请求 → 响应 |
|---|---|---|---|
| GET | `/api/health` | 冒烟/健康检查 | → `{"status": "ok"}` |
| GET | `/api/frame/latest` | **预留，第 1 周不实现**（见 §6.5） | → 帧截图 |

### 6.1 `POST /api/recognize`

请求体（`frame_ref` 为**相对 `algo/samples/frames/` 的文件名**，v0.1 明确）：

```json
{ "frame_ref": "001.jpg" }
```

stub 行为：读取 `algo/samples/labels/001.json`（同名字、`.json` 后缀），原样返回为 `RecognitionResult`。**不读图片本身**，只按 `frame_ref` 拼路径。

### 6.2 `POST /api/judge`

- 入参即 `RecognitionResult`。
- 引擎内部按 `plate` 查 `charging_pile` 与 `system_config`，命中四条规则之一则返回 `ViolationRecord`，**规则 ④（正常充电）返回 `null`**。
- **落库口径（v1.2 明确）**：命中即**落库**并返回带 `id` 的记录（非等 `/api/notify`），前端拿到 `id` 后可直接调 `/api/notify` 或查 `/api/records`。
- **去重口径（v1.2 明确）**：若已存在 **同 `pile_id` + 同 `rule_hit` 且 `notify_status='未提醒'`** 的记录，视为「同一违规持续中」，更新其 `occur_time` 并返回原记录，**不新增行**。避免轮询场景下记录爆炸、保证「报警统计」页数字真实。已提醒过（或 `rule_hit` 已变）再次命中则视为新违规，新增一条。

### 6.3 `POST /api/notify`

请求体（v1.2 起**入参含 `id`**，用于定位要更新的记录 —— v1.1 及以前仅 `notify_status`，沙箱无法确定更新哪条）：

```json
{ "id": 1, "notify_status": "已提醒" }
```

- `id` 取自 `/api/judge` 返回的记录。
- 沙箱实现：按 `id` 更新 `occupation_record.notify_status` / `notify_time`，并写日志，不调真实短信 API。
- 记录不存在 → `404`。

### 6.4 `GET /api/records`

**查询参数（v1.3 新增筛选，全部可选，不传即不参与过滤）**：

| 参数 | 类型 | 说明 |
|---|---|---|
| `page` | int ≥1，默认 `1` | 页码 |
| `size` | int 1–200，默认 `20` | 每页条数 |
| `plate` | string | 车牌号，**模糊匹配**（`LIKE %..%`，忽略大小写） |
| `vtype` | `新能源` \| `燃油` | 车型，精确匹配 |
| `pile_id` | string | 桩 ID，**模糊匹配**（忽略大小写） |
| `rule_hit` | int 0–3 | 命中规则，精确匹配 |
| `notify_status` | `未提醒` \| `已提醒` \| `失败` | 提醒状态，精确匹配 |
| `start_time` | ISO 8601 / `YYYY-MM-DD` | 命中时间**下界**（含） |
| `end_time` | ISO 8601 / `YYYY-MM-DD` | 命中时间**上界**（含） |

**筛选口径（v1.3 明确）**：
- 多个参数之间是 **AND** 关系。
- `plate` / `pile_id` 为模糊匹配；其余为精确匹配。
- `start_time` / `end_time` 均**含边界**。若 `end_time` 只给日期（`2026-09-19`），
  按**当日 23:59:59.999999** 解释，避免"选同一天查不到数据"。
- **`total` 必须反映筛选后的总数**（不是全表总数）——前端分页条依赖它。
- 无任何筛选参数时行为与 v1.2 一致（全表分页，按 `occur_time` 倒序）。

响应结构（v0.1 明确，前端分页条需要 `total`）：

```json
{
  "items": [ { "ViolationRecord" } ],
  "total": 42,
  "page": 1,
  "size": 20
}
```

> `total` = **应用筛选条件后**的总条数；`page` / `size` 回显请求值。

### 6.5 预留端点（第 1 周不实现）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/frame/latest` | 实时识别预览：返回最近一帧截图，前端轮询刷新。开发大纲有此需求，第 0 天 4 端点未覆盖，先占位登记 |

### 6.6 车辆信息 CRUD（v1.3 新增）

> **背景**：§1.1 第 1 页「车辆信息管理」要求表格列 = `vehicle` 全字段并可增删改，
> 但 v1.2 及以前的 §6 只有识别闭环的 5 个端点，**未定义 vehicle 的读接口** ——
> 前端只能退化为本地存储（`localStorage`），无法与后端一致，且「车辆信息管理」既列在
> 第 1 周范围就必须有真接口。本版补齐 4 个端点。

| 方法 | 路径 | 说明 | 请求 → 响应 |
|---|---|---|---|
| GET | `/api/vehicles` | 车辆列表（分页 + 可选筛选） | `?page=&size=&plate=&vtype=&owner=` → `VehiclePage` |
| POST | `/api/vehicles` | 新增车辆 | `Vehicle` → `Vehicle`（`201`） |
| PUT | `/api/vehicles/{plate}` | 更新车辆 | `VehicleUpdate` → `Vehicle` |
| DELETE | `/api/vehicles/{plate}` | 删除车辆 | → `204` |

**查询参数（`GET /api/vehicles`）**：

| 参数 | 类型 | 说明 |
|---|---|---|
| `page` | int ≥1，默认 `1` | 页码 |
| `size` | int 1–200，默认 `20` | 每页条数 |
| `plate` | string | 车牌号，**模糊匹配**（忽略大小写） |
| `vtype` | `新能源` \| `燃油` | 车型，精确匹配 |
| `owner` | string | 车主，**模糊匹配** |

**响应结构**：

```json
{
  "items": [ { "Vehicle" } ],
  "total": 3,
  "page": 1,
  "size": 20
}
```

**口径（务必遵守）**：

- **`plate` 是主键，不可修改**：`PUT /api/vehicles/{plate}` 的路径参数是**定位用**，
  请求体里的 `plate` 会被忽略（或若与路径不符则返回 `400`）。前端编辑态下车牌只读。
- **`POST` 新增时 `plate` 已存在 → `409`**（不是 `400`），前端据此提示"车牌号已存在"。
- **`DELETE` 不级联删除违规记录**：`occupation_record` 保留（历史违规是事实记录），
  但此后该车牌不再有关联手机号，**无法自动提醒**。前端删除确认弹窗必须说明这一点
  （`component-inventory.md` §4.1 标注 6 的要求）。
  `occupation_record.plate` **不加外键约束**，否则历史记录会被连带删除。
- `created_at` 由**服务端**在 `POST` 时生成，请求体不传。
- `PUT` 请求体为 `VehicleUpdate`（仅 `vtype` / `owner` / `phone`，不含 `plate` / `created_at`）。
- `plate` 不存在 → `404`；`phone` / `plate` 格式非法 → `422`（Pydantic 校验）。

**`Vehicle` 结构**（对应 §3.1 全字段）：

```json
{
  "plate": "京AD12345",
  "vtype": "新能源",
  "owner": "张伟",
  "phone": "13800136621",
  "created_at": "2026-09-01T09:00:00"
}
```

## 7. 系统配置项

`full_timeout_min`（充满超时阈值）、`abnormal_park_min`（异常占位久停阈值），均来自 `system_config`，禁止硬编码。

## 8. 仓库结构与文件归属

```
充电桩/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI 入口 + /api/health
│   │   ├── schemas.py         # Pydantic：RecognitionResult / ViolationRecord / FrameRef / NotifyResp
│   │   ├── routers/           # API 路由
│   │   ├── rule_engine.py     # 规则引擎
│   │   └── db.py              # SQLAlchemy 连接（开发期 SQLite / 目标 MySQL 8）
│   ├── sql/
│   │   └── schema.sql         # 四表建表（MySQL 8 语法）+ 种子数据
│   └── tests/                 # pytest / TestClient 用例
├── frontend/                  # Vue3 + Vite + Element Plus
├── algo/
│   ├── samples/frames/        # 测试帧（汤提供）
│   └── samples/labels/        # 同名字标注 JSON，字段 = RecognitionResult（汤提供）
├── docs/
│   ├── design/                # 设计系统、线框、切图（吴）
│   └── CONTRACT.md            # 本文件
├── .gitignore
└── AGENTS.md
```

**归属**：`backend/app/**`、`backend/sql/**` → 汤/吕；`frontend/**` → 吕（实现）+ 吴（设计）；`algo/**` → 汤；`docs/design/**` → 吴。

## 9. 协作规范

- **分支**：`main` 为保护分支（已由 `master` 重命名）；功能开 `feature/<name>`（如 `feature/rule-engine`），吕浩统一合入。一两天一合，避免各合各的弄乱 `main`。
- **commit 规范**：每完成一步即提交，信息用 `模块: 简述`（如 `db: 新增四表 schema 与种子`）。
- **lint/format**：Python `ruff` + `black`；前端 `eslint` + `prettier`，提交前自动格式化，减少无意义 diff。
- **测试**：每次改动必须编写/更新对应测试，交付前全部通过（见 `AGENTS.md`）。
- **改契约**：先改本文件 → @全员 + 升版本号。

## 10. 识别桩数据格式约定

- 测试帧：`algo/samples/frames/<name>.jpg`（1–2 张即可）
- 标注文件：`algo/samples/labels/<name>.json`，字段与 `RecognitionResult` **完全一致**
- 汤负责提供样例，吕浩 stub 按 `frame_ref` 拼路径读取；双方只依赖本文件第 4 节，不口头约定

## 11. 第 1 周末 Demo 验收清单

端到端跑通一条可演示的最小闭环：
**输入一张测试帧 → 识别桩返回车牌+类型 → 规则引擎判定违规 → 短信沙箱写库+日志 → 后台页面能看到这条违规记录。**

- [ ] `POST /api/recognize` 传入 `frame_ref`，返回合规 `RecognitionResult`
- [ ] `POST /api/judge` 四条规则正确：燃油占位 / 异常占位 / 充满未移车 各命中，正常充电返回 `null`
- [ ] `POST /api/notify` 沙箱写库成功（`notify_status` 更新）+ 有日志落盘
- [ ] `GET /api/records` 能查到刚产生的那条记录，分页 `total` 正确
- [ ] `GET /api/records` **筛选参数（§6.4）生效**：`rule_hit=1` 只返回燃油占位，`total` 随筛选变化
- [ ] 后台"违规记录查询"页面能看到该条记录
- [ ] 后台"车辆信息管理"页面可用（`/api/vehicles` CRUD 见 §6.6）：能增、能改、能删，车牌编辑态只读
- [ ] `GET /api/health` = 200，冒烟测试 `tests/test_health.py` 通过
- [ ] 汤：pytest 覆盖四规则全过；吕：TestClient 测端点与沙箱全过
- [ ] 本周不卡准确率 / 响应时间指标

> **第 1 周不验收**（见 §1.1）：第 3 页充电状态展示、第 4 页报警统计、第 5 页系统参数配置为**占位路由**；
> 第 6 页实时识别预览不做。此 4 页不进第 1 周 Demo 验收清单。

## 12. 变更记录

| 版本 | 日期 | 变更 | 发起人 |
|---|---|---|---|
| **v1.4** | 2026-09-19 | 设计评审发现**列名口径没有唯一事实源**：同一字段的显示列名散落在 §3.x 说明档、`component-inventory.md`、线框表头、校验脚本白名单四处且互为主从，已实际发生「第 2 页写『车牌号』、第 4 页写『车牌』」的三方分叉（吴 `walkthrough.md` F8）。**新增 §3.5 显示列名映射表**，作为「字段 → 列名 → 页面」的唯一人工维护点，机器可读；判定粒度定为「**同表同字段必须同列名，跨表允许不同**」（故 `plate` 在 `vehicle` 显示「车牌号」、在 `occupation_record` 显示「车牌」是有意为之）。同步把 §3.1 `phone` 说明由「绑定手机号」改为「手机号」、§3.2 `status` 由「运行状态」改为「状态」，与映射表对齐。`check_tokens.py` 的列名白名单改为**解析本节生成**（删硬编码），并新增三条断言：表头必须能在本表查到、同表跨页列名一致、§3.x 说明档与本节一致 | 吕浩 |
| **v1.3** | 2026-09-19 | 第 1 周前端落地时发现三处缺口，一并补齐：① **§6.4 `GET /api/records` 新增筛选参数**（`plate`/`vtype`/`pile_id`/`rule_hit`/`notify_status`/`start_time`/`end_time`，AND 关系，`total` 随筛选变化）——此前只有 `page`/`size`，第 2 页筛选项只能前端过滤当前页；② **新增 §6.6 车辆信息 CRUD 四端点**（`GET/POST /api/vehicles`、`PUT/DELETE /api/vehicles/{plate}`）——§1.1 要求第 1 页表格含 `vehicle` 全字段并可增删改，但 §6 从未定义该表读接口，前端只能退化为 localStorage；③ **§1.1 页面清单表述对齐 `PLAN_4WEEKS.md` §2.1**：第 3/4/5 页明确为「占位路由」（原标「做」，与 PLAN 任务 1.8 冲突），并新增「完整实现」列标注周次；§11 同步补筛选与车辆 CRUD 两条验收项、明确 4 页不进第 1 周验收 | 吕浩 |
| **v1.2** | 2026-09-13 | 接口层实现落地，明确两处此前未定的口径：① **`/api/judge` 命中即落库**，并新增**去重规则**（同 `pile_id`+同 `rule_hit`+未提醒 → 复用原记录，不新增）；② **`/api/notify` 入参增加 `id`**（原仅 `notify_status`，沙箱无法定位记录）。同时实现 `/api/recognize`（stub 读 `algo/samples/labels/`，缺文件 404）、`/api/records`（分页按 `occur_time` 倒序），`main.py` 挂载全部路由并在启动时建表+种子 | 吕浩 |
| **v1.1** | 2026-09-08 | 新增 **§1.1 后台页面清单（6 页）**：车辆信息管理 / 违规记录查询 / 充电状态展示 / 报警统计 / 系统参数配置 / 实时识别预览（末项第 1 周预留，依赖 §6.5 预留端点）。来源：开发大纲 M7。**补此清单是为解封吴和庆任务 5.3.1** —— 原契约未定义页面范围，吴无从下手。另约定：表格列以对应表字段为准，页面增删须先改本节并升版本 | 吕浩 |
| **v1.0** | 2026-09-08 | **三人确认定稿**。① v0.1 的 4 处补齐（`occupation_record.pile_id`、`ViolationRecord.id`、`frame_ref` 路径规则、`/api/records` 的 `items+total+page+size`）获汤瑾睿、吴和庆确认；② 确定 MySQL 8 验证方案为**方案 b**——`schema.sql` 交 MySQL 8 语法、本地用 SQLite+SQLAlchemy 等价验证、真机验证延至第 2 周（详见第 2 节） | 吕浩（汤瑾睿、吴和庆确认） |
| v0.1 | 2026-09-08 | 首版。相对第 0 天文档第 6 节草案的 4 处补齐：`occupation_record` 增 `pile_id`；`ViolationRecord` 增 `id`；明确 `frame_ref` 为相对 `algo/samples/frames/` 的文件名；`GET /api/records` 返回 `items+total+page+size`。另登记预留端点 `/api/frame/latest`，并确定开发期 SQLite / 目标 MySQL 8 | 吕浩 |
