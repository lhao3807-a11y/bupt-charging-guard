# CONTRACT.md — 接口与数据契约（唯一事实源）

> **版本**：v0.1（待三人确认，确认后升 v1.0）
> **负责人**：吕浩（起草与维护）
> **确认人**：吕浩 / 汤瑾睿 / 吴和庆
> **适用范围**：第 1 周最小闭环。任何结构变动 → 先改本文件 → @全员 + 升版本号，**禁止私自改自己那侧**。

---

## 1. 项目范围与 MVP

- **一句话**：用"计算机视觉 + 充电桩状态"融合，自动识别燃油车占位 / 新能源充满未移车，并主动提醒车主，形成"识别—判断—提醒"闭环。
- **形态**：演示系统原型（校园场景），完整跑通业务闭环，不做生产部署。
- **MVP 边界**：
  - 充电状态用**模拟数据**，预留 OCPP 适配层，不接真实运营商接口。
  - 第 1 周 CV 用**识别桩 stub**（读标注 JSON），短信用**沙箱**（写库 + 日志），后续替换为 YOLOv8 + HyperLPR / 真实短信 API。
  - 第 1 周**不卡准确率与响应时间指标**，闭环优先。

## 2. 开发基线（三人统一）

| 项 | 版本 | 说明 |
|---|---|---|
| Python | 3.11.x | 本机 3.11.9。**不要用 3.13** —— Ultralytics/PaddleOCR  wheels 支持滞后，第 2 周装模型会踩坑 |
| Node.js | 22 LTS | 本机 v22.22.2，npm 10.9.7 |
| 数据库（目标） | MySQL 8.0 | `backend/sql/schema.sql` 以 MySQL 8 语法为准，是交付物 |
| 数据库（开发期） | SQLite 3 | 本机未装 MySQL 8。开发期连 SQLite 文件库，数据访问走 SQLAlchemy，**第 2 周换 MySQL 只改连接串** |
| Git | 2.55+ | 主分支 `main`（已于第 0 天由 `master` 重命名） |

**开发期 SQLite 约束**：`vtype` / `status` / `notify_status` 在 MySQL DDL 里保留 `ENUM`，在 SQLAlchemy 模型中统一映射为 `String` + Pydantic 层 `Enum` 校验。禁止在业务代码里依赖数据库原生 ENUM 行为，否则换库必炸。

## 3. 数据模型（核心四表）

### 3.1 vehicle（车辆信息）

| 字段 | 类型 | 说明 |
|---|---|---|
| plate | VARCHAR(15) PK | 车牌号 |
| vtype | ENUM('新能源','燃油') | 车型（由绿牌/蓝牌判定） |
| owner | VARCHAR(50) | 车主 |
| phone | VARCHAR(20) | 绑定手机号 |
| created_at | DATETIME | 录入时间 |

### 3.2 charging_pile（充电桩状态，模拟）

| 字段 | 类型 | 说明 |
|---|---|---|
| pile_id | VARCHAR(20) PK | 桩 ID |
| status | ENUM('空闲','充电中','已充满') | 运行状态 |
| bound_plate | VARCHAR(15) | 绑定车牌（FK vehicle.plate） |
| start_time | DATETIME | 开始充电时间 |
| end_time | DATETIME | 充满时间 |

### 3.3 occupation_record（违规记录）

| 字段 | 类型 | 说明 |
|---|---|---|
| id | BIGINT PK AUTO_INCREMENT | 记录 ID |
| plate | VARCHAR(15) | 车牌 |
| vtype | ENUM('新能源','燃油') | 车型 |
| **pile_id** | VARCHAR(20) NULL | **桩 ID（v0.1 新增）**——违规记录需能关联到具体桩，否则后台统计缺维度 |
| rule_hit | TINYINT | 1 燃油占位 / 2 异常占位 / 3 充满未移车 / 0 正常 |
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

| 方法 | 路径 | 说明 | 请求 → 响应 |
|---|---|---|---|
| POST | `/api/recognize` | 输入帧 → 识别结果（stub 读标注） | `FrameRef` → `RecognitionResult` |
| POST | `/api/judge` | 识别结果 → 违规判定（引擎内部查桩状态） | `RecognitionResult` → `ViolationRecord` \| `null` |
| POST | `/api/notify` | 违规 → 短信沙箱（写库+日志） | `ViolationRecord` → `NotifyResp` |
| GET | `/api/records` | 后台查询违规记录 | `?page=&size=` → `RecordPage` |
| GET | `/api/health` | 冒烟/健康检查 | → `{"status": "ok"}` |

### 6.1 `POST /api/recognize`

请求体（`frame_ref` 为**相对 `algo/samples/frames/` 的文件名**，v0.1 明确）：

```json
{ "frame_ref": "001.jpg" }
```

stub 行为：读取 `algo/samples/labels/001.json`（同名字、`.json` 后缀），原样返回为 `RecognitionResult`。**不读图片本身**，只按 `frame_ref` 拼路径。

### 6.2 `POST /api/judge`

- 入参即 `RecognitionResult`。
- 引擎内部按 `plate` 查 `charging_pile` 与 `system_config`，命中四条规则之一则返回 `ViolationRecord`，**规则 ④（正常充电）返回 `null`**。

### 6.3 `POST /api/notify`

```json
{ "notify_status": "已提醒" }
```

沙箱实现：更新 `occupation_record.notify_status` / `notify_time`，并写日志，不调真实短信 API。

### 6.4 `GET /api/records`

响应结构（v0.1 明确，前端分页条需要 `total`）：

```json
{
  "items": [ { "ViolationRecord" } ],
  "total": 42,
  "page": 1,
  "size": 20
}
```

### 6.5 预留端点（第 1 周不实现）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/frame/latest` | 实时识别预览：返回最近一帧截图，前端轮询刷新。开发大纲有此需求，第 0 天 4 端点未覆盖，先占位登记 |

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
- [ ] 后台"违规记录查询"页面能看到该条记录
- [ ] `GET /api/health` = 200，冒烟测试 `tests/test_health.py` 通过
- [ ] 汤：pytest 覆盖四规则全过；吕：TestClient 测端点与沙箱全过
- [ ] 本周不卡准确率 / 响应时间指标

## 12. 变更记录

| 版本 | 日期 | 变更 | 发起人 |
|---|---|---|---|
| v0.1 | 2026-09-08 | 首版。相对第 0 天文档第 6 节草案的 4 处补齐：`occupation_record` 增 `pile_id`；`ViolationRecord` 增 `id`；明确 `frame_ref` 为相对 `algo/samples/frames/` 的文件名；`GET /api/records` 返回 `items+total+page+size`。另登记预留端点 `/api/frame/latest`，并确定开发期 SQLite / 目标 MySQL 8 | 吕浩 |
