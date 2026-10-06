# 第 2 周 · 汤瑾睿（后端 / DB / 算法）开发进度

> 更新：2026-10-05　依据：`PLAN_4WEEKS.md` §3.0（C1–C3）与 §3.2（5.1–5.9）。
> 分支：`feature/api-week2`（基于 `main` @ `3cead88`）。

## 一、总览

| # | 任务 | 状态 | 交付 |
|---|---|---|---|
| C1–C3 | 契约三组新接口定义 | ✅ | 契约 **v1.6** §6.7–6.9（后因模拟器端点升 **v1.7**） |
| 5.7 | 三组接口实现 + 测试 | ✅ | `routers/piles.py`、`stats.py`、`config.py` + 50 条测试 |
| 5.2 | `algo/tests` skip 守卫 | ✅ | 无 CV 环境时 3 skipped，退出码 0（原为 exit 2） |
| 5.8 | 充电状态模拟器 | ✅ | `app/simulator.py` + CLI + §6.10 端点（契约 v1.7） |
| 5.1 | CV 产物补凭据 | ✅ | `docs/acceptance/algo/**`（解第 1 周 R1） |
| 5.3 | 真实数据集 | ✅ | 公开集路线：CCPD → `dataset_real` **800 张**（绿 419 / 蓝 381）；**2026-10-06 补网络实拍集 `dataset_web` 174 张**（Commons/Openverse 自由许可真实照片，绿 88 / 蓝 88，逐张人工核验，见 `algo/dataset_web/README.md`） |
| 5.4 | YOLOv8 微调（真实集） | ✅ | **mAP50 = 0.994 / mAP50-95 = 0.821**（val 160 张，5 分 10 秒） |
| 5.5 | 车牌识别调优 | ✅ | 端到端 **OCR 91.25% / 牌色 95.00% / 全对 88.75%**；修掉 OCR 静默失效 bug |
| 5.6 | MySQL 8 真机验证 | ✅ | **2026-10-06 真机跑通 19/19**（本机 ZIP 免安装版 MySQL 8.0.45，独立测试库）；凭据 `docs/acceptance/db/01-verify-mysql.{json,log}` |
| 5.9 | 测试与 lint 全绿 | ✅ | 后端 **202 passed**（目标 ≥160）+ algo **43 passed**，ruff + format 全绿 |

## 二、已完成

### C1–C3 / 5.7：三组后台接口（契约 v1.6 → v1.7）

按「先改契约 → @全员 → 升版本 → 再动代码」的流程执行：

- **§6.7 `GET /api/piles`**：桩列表 + `status` 精确筛选 + `pile_id` 模糊筛选；
  响应附 **`summary`（筛选后三状态计数）**，第 3 页总览卡可直接取用，不必前端再算。
- **§6.8 `GET /api/stats`**：`by_rule` **固定 4 项**（0/1/2/3 升序，无记录补 0）+ `by_date` **连续日期补洞**；
  聚合在 Python 侧做，不用 `DATE()` 这类库函数 —— 保证 SQLite 与 MySQL 行为一致。
- **§6.9 `GET/PUT /api/config`**：守 §7 红线，白名单仅两个阈值键（`extra="forbid"` 拒野键），
  取值范围 1–1440 分钟，值以字符串存取，键缺失抛 `ConfigMissingError` **不静默兜底**。
- **§6.10 `POST /api/piles/simulate`**（v1.7）：把模拟器暴露给前端，见下。

同步动作：三个占位页（`PilesView` / `StatisticsView` / `ConfigView`）的「契约未定义」提示条
已反转为「已定义、待接入」—— 契约纪律要求升版后必须消灭这类「活跃的谎言」。

### 5.2：algo/tests skip 守卫

此前模块级 `import numpy` 让 pytest 在**收集阶段**就 `ImportError`、退出码 **2**，
看起来像测试挂了，实际只是算法环境没装。现在三个测试模块在导入期 `importorskip("numpy")`：
后端环境跑 `algo/tests` → 3 skipped；与 `backend/tests` 合跑 → 退出码 0。

> 踩坑记在 `algo/tests/conftest.py`：**不能在 conftest 顶层调 `pytest.skip`**，
> conftest 在 pytest 启动阶段加载，此时抛 `Skipped` 会把整个 pytest 进程打崩（exit 1）。

### 5.8：充电状态模拟器

```
空闲(有车) --3min--> 充电中 --20min--> 已充满 --full_timeout_min--> 空闲(释放)
```

- 「已充满 → 释放」用的是**业务阈值** `full_timeout_min`（从 `system_config` 读，契约 §7），
  故模拟出的数据会自然命中规则③「充满未移车」，第 2/4 页因此有真数据可看。
- 前两段是模拟器节奏参数，**刻意不进 `system_config`** —— 那张表是规则引擎的唯一配置源。
- 一次调用只推进一步（否则演示时会跳过「充电中」这档）。
- CLI：`scripts/simulate_piles.py`（单次 / 循环 / `--at` 快进）；端点：`POST /api/piles/simulate`。

### 5.1：CV 产物凭据

`docs/acceptance/algo/` 存了复跑证据（RTX 4060 / CUDA）：

| 环节 | 证据 | 结论 |
|---|---|---|
| 环境自检 | `00-check-env.log` | 7/7 PASS |
| 数据集生成 | `01-gen-dataset.log` | 132 张（train 109 / val 23） |
| 训练 | `02-train.log`、`results.png` | epoch 27 早停，**mAP50 = 0.995** |
| 推理 | `03-predict.log`、`charging_006_pred.jpg` | 车辆 0.973 / 车牌 0.923 |

⚠️ **该 mAP 基于合成集**，只证明链路跑通，真实准确率待真实集重训后评估（README 已写明）。

## 三、进行中 / 阻塞

### 5.3–5.5：真实数据（走公开集路线）—— **已完成**

校园实拍尚未采集，按你的选择改用**公开真实照片**（CCPD）：

- `algo/tools/fetch_public_dataset.py`：走系统代理下载 CCPD2020（绿牌，865 MB）
  与 CCPD2019 子集（蓝牌为主，1.5 GB）；产物在 `algo/dataset_raw/`（不入库）。
- `algo/tools/ccpd_to_yolo.py`：解析 CCPD 文件名里的 bbox 与车牌号，产出
  **`plate` 单类**的 YOLO 数据集 + `meta.json`。
- `algo/tools/eval_real.py`（新增）：把**检测 / OCR / 牌色三段拆开**打分。
  拆分是刻意的设计——只有一个端到端数字时，掉点你根本不知道该重训检测器还是调阈值。

### 5.3+：网络实拍集 `dataset_web`（2026-10-06 新增，承接计划风险表备选②）

验收审查指出「CCPD 不是计划要求的四类实拍数据」后，按用户指示从网上补充**真实照片**：

- 采集：Commons + Openverse 共 90+ 查询词、1809 候选（ND 许可剔除），下载 884 张；
- 预筛：train_real 权重检出车牌 371 张、OCR 合法 238 张；
- **人工逐张目检**（联系表渲染核验）：入库 **174 张**（train 138 / val 36，绿 88 / 蓝 88），
  剔除海外车展/境外牌/展示牌/误检/重复角度约 710 张，全程记录在
  `algo/dataset_web_raw/review.json`，许可逐张登记 `algo/dataset_web/licenses.csv`。
- ⚠️ **诚实局限**：街景/停车场为主，充电位上下文样本极少（充电中 1 张、燃油占位 1 张），
  计划「四类各 ≥30」无法由网络照片诚实达成，充电位场景仍需校园实拍（备选①）；
  详见 `algo/dataset_web/README.md`。

#### 结果（val 160 张，绿 86 / 蓝 74）

| 环节 | 结果 |
|---|---|
| 训练 mAP50 / mAP50-95 | **0.994 / 0.821** |
| 检测 检出率 / IoU≥0.5 / 平均 IoU | **100% / 100% / 0.9005** |
| OCR 整串匹配 / 字符级 | **91.25% / 96.82%** |
| 牌色判定 | **95.00%** |
| 端到端 号码 / 号码+牌色全对 | **91.25% / 88.75%** |
| 分牌色：绿 OCR / 蓝 OCR | **96.51% / 85.14%** |

**蓝牌明显更难**（OCR 低 11pp、牌色低 11pp），剩余 14 张失败集中在省份汉字
（皖→粤/宁/京）与少量空值。答辩时这是要如实讲的短板。

#### ⚠️ 修掉的静默 bug：OCR 此前从来没工作过

第一次真实集评估跑出 OCR **0.00%**（160 张一张没认出），排查发现：
hyperlpr3 3.x 返回 `[号码, 置信度, 牌色, 框]`，而代码按 `(框, 号码, 置信度, 牌色)`
解析 → 拿置信度当号码、牌色当置信度 → 正则必然不过 → **静默恒定返回空串**。

**第 1 周为什么没发现**：合成牌本来就认不出号码（当时把"plate 为空"当正常），
所以这个 bug 在合成集上完全不可见。修复后 0% → 91.25%，并加防回归测试钉死字段顺序。

#### OCR 该喂裁剪 ROI 还是整帧？—— 实测整帧更好，线上已切

| OCR 输入 | 整串 | 字符级 | 蓝牌 |
|---|---|---|---|
| 裁剪 ROI | 82.50% | 89.42% | 68.92% |
| 整帧 | 91.25% | 96.82% | 85.14% |
| 整帧+按检测框挑（**采用**） | **91.25%** | **98.12%** | **85.14%** |

整帧"取最高分"在多车场景会认成隔壁车的牌（串号=短信发错人），
故线上按 **IoU 挑最贴合检测框**的那条，准确率持平但不会串号。

> **为什么只标 plate 一类**：CCPD 只有车牌框、**没有车辆框**。若混进 `vehicle` + `plate`
> 两类训练集，真实图上的车会被当成背景（漏标），反而把 `vehicle` 类教坏。
> 故真实集单独训练与评估，`vehicle` 类仍由合成集负责，校园实拍补标车辆框后再合并。

局限（须在答辩时如实说明）：CCPD 是停车场车头照，**没有充电桩与充电枪**，
因此「是否插枪 / 桩状态」这类场景特征仍需校园实拍补充。

### 5.6：MySQL 8 真机验证 —— ✅ 已真机跑通（2026-10-06，19/19 通过）

**真机结果（MySQL 8.0.45，独立测试库 `bupt_charging_guard_test`）**：19 项全 PASS，
凭据存 `docs/acceptance/db/01-verify-mysql.json`（机器读）与 `01-verify-mysql.log`（人读）。

其中最关键的几条（都是 SQLite 上验不出来、或验不准的）：

| 检查项 | 真机结果 |
|---|---|
| 四表 `ENGINE=InnoDB` + `utf8mb4` | PASS（4/4 表，排序规则 `utf8mb4_0900_ai_ci`） |
| `charging_pile.status` 原生 ENUM | PASS —— `enum('空闲','充电中','已充满')` |
| ENUM 非法值被拒 | PASS —— 抛 `DataError`（本次 `sql_mode` 含 `STRICT_TRANS_TABLES`，严格模式） |
| **FK `ON DELETE SET NULL` 真的置空** | PASS —— 删车后 `bound_plate=None` ✅ **SQLite 上这条可能从未生效** |
| `occupation_record.plate` 未加外键 | PASS |
| `DATETIME` 存取往返一致 | PASS —— 读出 `datetime(2026, 9, 8, 10, 0)`，无时区偏移 |
| `system_config.\`key\`` 反引号转义 | PASS |
| 种子数据行数 | PASS —— vehicle 6 / charging_pile 4 / system_config 2 |

> 环境是怎么来的：本机无 Docker、且 **wsl.exe 被安全策略拉黑 + Windows 为家用版无 Hyper-V**，
> 两条 Docker 路线都不通。改用 **MySQL 8 官方 ZIP 免安装版**（下载 234 MB、解压约 1 GB，
> 全部放 E 盘），`mysqld --initialize-insecure` 后直接起在 127.0.0.1:3306，跑完即关，不装系统服务。

已交付 `scripts/verify_mysql.py`（+ 6 条纯逻辑测试）。它对准 `backend/sql/schema.sql`，
建库建表后逐项断言，退出码 0/1，可 `--json` 存凭据。

重点验的是**SQLite 上根本验不出来**的几件事：

| 检查项 | 为什么必须上 MySQL 8 |
|---|---|
| 四表 `ENGINE=InnoDB` + `utf8mb4` | SQLite 没有引擎/字符集概念 |
| `charging_pile.status` 是**原生 ENUM** | SQLite 退化成 VARCHAR + CHECK |
| ENUM **非法值被拒** | 两边行为不同（MySQL 非严格模式会存空串，脚本两种都认） |
| **FK `ON DELETE SET NULL` 真的把 `bound_plate` 置空** | ⚠️ **SQLite 默认不启用外键**（`PRAGMA foreign_keys` OFF），这条在 SQLite 上可能压根没生效过而测试照样绿 —— 这是上真机的首要理由 |
| `occupation_record.plate` **未加** FK | 契约要求记录能留存已删车辆的历史 |
| `DATETIME` 存取往返一致（无时区） | SQLite 存字符串，MySQL 8 是原生 DATETIME |
| `system_config.\`key\`` 反引号转义可用 | `` `key` `` 是 MySQL 保留字，SQLite 不吃这套 |

复跑命令（拿到 MySQL 8 后）：

```bat
.venv\Scripts\python.exe -m pip install pymysql
set MYSQL_HOST=127.0.0.1
set MYSQL_PORT=3306
set MYSQL_USER=root
set MYSQL_PASSWORD=xxxx
set MYSQL_DB=bupt_charging_guard
.venv\Scripts\python.exe scripts\verify_mysql.py --json docs\acceptance\db\01-verify-mysql.json
```

⚠️ 脚本会 **DROP 并重建**目标库里的四张表（schema.sql 自带 DROP），**别指向有数据的库**。

SQLite 侧的等价性由 `backend/tests/test_models.py` 等覆盖（当前后端 208 passed）。
本机现状：无 MySQL 服务/客户端、无 Docker；**wsl.exe 被安全策略列入黑名单、无法调用**，
故暂不能在本机起 MySQL。

## 四、质量门禁（本地实测）

| 项 | 结果 |
|---|---|
| 后端 pytest | **208 passed**（含 piles 13 / stats 13 / config 24 / simulator 12 / simulate-api 8 / verify-mysql 6） |
| algo 测试（算法环境） | **43 passed**（plate / detect / ccpd 解析 / eval 纯函数） |
| algo 测试（后端环境，无 numpy） | 跳过，退出码 0 |
| `ruff check backend scripts algo` | All checks passed |
| `ruff format --check backend scripts algo` | 55 files already formatted |

> ⚠️ **lint 范围**：仓库标准命令是 `ruff check backend scripts`（`docs/design/tools/**` 不在范围内）。
> 跑 `ruff format .` 会误格式化吴和庆的设计工具脚本，务必按范围跑。
