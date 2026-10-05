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
| 5.3 | 真实数据集 | 🟡 进行中 | 公开集路线（CCPD），工具已交付，数据转换中 |
| 5.4 | YOLOv8 微调（真实集） | 🟡 依赖 5.3 | 待真实集就绪后微调并报 mAP50 |
| 5.5 | 车牌识别调优 | 🟡 依赖 5.3 | 待真实集就绪后评估 OCR 与绿/蓝牌判定 |
| 5.6 | MySQL 8 真机验证 | 🔴 阻塞 | 本机无 MySQL 服务/客户端、无 Docker（见下） |
| 5.9 | 测试与 lint 全绿 | ✅ | 后端 **202 passed**（目标 ≥160），ruff + format 全绿 |

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

### 5.3–5.5：真实数据（走公开集路线）

校园实拍尚未采集，按你的选择改用**公开真实照片**：

- `algo/tools/fetch_public_dataset.py`：走系统代理下载 CCPD2020（绿牌 / 新能源，865 MB）
  与 CCPD2019 子集（蓝牌 / 燃油，1.5 GB）；产物在 `algo/dataset_raw/`（不入库）。
- `algo/tools/ccpd_to_yolo.py`：解析 CCPD 文件名里的 bbox 与车牌号，产出
  **`plate` 单类**的 YOLO 数据集 + `meta.json`。

> **为什么只标 plate 一类**：CCPD 只有车牌框、**没有车辆框**。若混进 `vehicle` + `plate`
> 两类训练集，真实图上的车会被当成背景（漏标），反而把 `vehicle` 类教坏。
> 故真实集单独训练与评估，`vehicle` 类仍由合成集负责，校园实拍补标车辆框后再合并。

局限（须在答辩时如实说明）：CCPD 是停车场车头照，**没有充电桩与充电枪**，
因此「是否插枪 / 桩状态」这类场景特征仍需校园实拍补充。

### 5.6：MySQL 8 真机验证 —— 环境不具备

本机既无 MySQL 服务/客户端，也无 Docker。待你决定后执行（装 Server 约 600 MB–1 GB，
ZIP 版可整包放 E 盘避开 C 盘；或提供远程实例，我写脚本跑建表 + `InnoDB` / `ENUM` 补验）。

## 四、质量门禁（本地实测）

| 项 | 结果 |
|---|---|
| 后端 pytest | **202 passed**（含 piles 13 / stats 13 / config 24 / simulator 12 / simulate-api 8） |
| algo 测试（后端环境） | 3 skipped，退出码 0 |
| `ruff check backend scripts algo` | All checks passed |
| `ruff format --check` | 全绿 |
