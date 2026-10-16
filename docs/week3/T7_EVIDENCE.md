# 第 3 周 T7 凭据索引（汤瑾睿 · 2026-10-12，2026-10-13 补 real 链路与测试复跑）

> 一句话：**第 3 周的闭环不是在 SQLite 上「跑通了」，而是在真机 MySQL 8 上跑通了；
> 并且 `real` 模式也在真实街拍图上跑通了。**
> 本页只做索引与口径说明，原始凭据都在 `docs/acceptance/week3/` 下。

## 1. 凭据清单

| 文件 | 内容 | 结果 |
|---|---|---|
| `01-verify-mysql-v19.log` / `.json` | MySQL 8 真机验证：四表结构、原生 ENUM、FK `ON DELETE SET NULL`、DATETIME 往返、**v1.9 五个新列 + 两个索引**、**加法迁移补列与幂等** | **31/31 通过** |
| `02-seed-demo.log` | 四场景夹具布置（PILE-D1..D4） | ①②③④ 四类各命中一次 |
| `03-pipeline-mysql.log` / `.json` | 自动闭环在 **MySQL** 上跑一轮（4 帧） | 识别 4/4、违规 3、本轮新发 3 |
| `04-timing-sample.log` / `.json` | 连跑 5 轮的耗时采样（整轮 + 逐帧） | 见 §2 |
| `05-test-rerun.log` | 复跑：后端全量 + 10 个专项文件 + ruff + 算法 | 后端 **326 passed**、专项 **168 passed**、算法 **45 passed**、ruff 全绿 |
| `06-pipeline-real.log` / `.json` | **real 模式端到端**（真实街拍图，非 stub）：识别→判定→落库→发送；含坏图/无牌失败样例、失败重试、无手机号补绑定 | **9/9 断言通过**，见 §3 |
| `07-acceptance-matrix.md` | A01–A17 逐项回填（通过/部分/未测 + 证据路径 + 责任人） | A01–A10、A12、A16 通过；A11/A13/A15 **部分**；A17 未做 |
| `08-signoff.md` | T1 契约 v1.9 与 T6 真值表的三人签认表 | 汤已签，**待吕浩、吴和庆** |

环境：本机 **MySQL 8.0.45**（官方 ZIP 免安装版，数据目录 `E:\WorkBuddy\tools\mysql8-data`），
目标库 `bupt_charging_guard_test`（**独立测试库**，验证脚本会 DROP 重建四表）。

## 2. 耗时采样（stub 识别 + MySQL 8，4 帧，5 轮）

| 指标 | min | p50 | mean | max |
|---|---|---|---|---|
| 整轮 | 21.41 ms | 22.34 ms | 34.20 ms | 81.73 ms |
| `001.jpg`（规则④ 正常） | 2.05 ms | 2.53 ms | 11.98 ms | 50.10 ms |
| `002.jpg`（① 燃油占位） | 4.96 ms | 6.15 ms | 7.44 ms | 12.47 ms |
| `003.jpg`（② 异常占位） | 5.07 ms | 6.12 ms | 6.44 ms | 8.75 ms |
| `004.jpg`（③ 充满未移车） | 5.34 ms | 7.00 ms | 7.21 ms | 9.25 ms |

- **第 1 轮 81.73 ms**（真识别一次），**第 2 轮起约 22 ms**（复用识别结果）—— 差的约 60 ms
  就是「内容没变就复用」省下的一次识别。
- `001.jpg` 是规则④ 正常的帧：不落库、不调用发送器，中位数 2.5 ms，是四条里最快的。

⚠️ **口径（别拿错数去汇报）**：这是 **stub 识别**（读标注）+ 单机 MySQL 的数字。
**真实 CV 链路**（`RECOGNITION_MODE=real`，YOLO 检测 + OCR）的耗时是另一个量级，
不是同一件事，两者不可直接比较。采样的目的只有两个：
证明闭环**每轮都能跑完、没有卡死**，以及量化「复用识别」到底省了多少。

## 3. A05「不重复提醒」的真机证据

5 轮采样里 `notified` 恒为 3，而 **`newly_notified` 全程为 0** ——
状态一直是「已提醒」，但**一条短信都没再发**；库里 `notify_attempts` 仍是 1
（第 1 次发送就成功，可在 `03-pipeline-mysql.json` 与 `04-timing-sample.json` 对帧核对）。

这正是第 2 周「自动轮询下每轮新增一条记录 + 重复发短信」那个坑被修掉的证据：
判重键换成了 `(pile_id, occupancy_id, rule_hit)`（契约 v1.9 §6.2）。

## 3. real 模式端到端（`06-pipeline-real.*`，2026-10-13 补）

返工清单点名要的「real 模式从帧到落库/提醒的成功与失败实测」，由
`scripts/accept_real_chain.py` 产出（**必须用 `.venv-algo` 跑**）：

```powershell
& ".venv-algo\Scripts\python.exe" scripts\accept_real_chain.py
```

它拿 `algo/dataset_web/` 的**网络实拍图**（不是标注 JSON）走完整闭环，9 项断言 **9/9 通过**：

| 断言 | 实测 |
|---|---|
| A01 一轮跑完 | 帧 6，违规 3 |
| A02 规则② | `b_idle_park` 命中 2 |
| A03 规则③ | `a_full_timeout` 命中 3 |
| A04 规则④ 不落库 | `c_normal` 无记录、不发送 |
| A05 不重复发 | 第 2 轮 `newly_notified=0`（第 3 轮换进程同样 0） |
| A06 无手机号 | 燃油记录 `attempts` **0**、状态失败；补绑定后重试成功 `attempts=1` |
| A07 失败重试 | 沙箱强制失败 `attempts=1` → 重试成功 `attempts=2` |
| A09 失败可见 | 坏图 → `ValueError: 图片无法解码`；无牌 → `422 OCR 空结果`，都不伪造结果 |
| A10 无串帧 | 逐帧核对「帧→车牌→桩」三元组，一致 |

**真实 CV 耗时**（4 帧真识别，单机 CPU，仅作量级参考）：

| 轮次 | 整轮耗时 | 说明 |
|---|---|---|
| 1 | 4264.66 ms | 4 帧真识别（YOLO + OCR） |
| 2 | 1121.37 ms | 识别结果复用，仍重判时间规则 |
| 3 | 3799.61 ms | **换进程**后重新识别（验证重启不清零） |

⚠️ 与 §2 的 stub 采样**不是同一件事**：这里每帧约 0.9–1.0 s，是 CV 的真实量级。
不要把 §2 的 22 ms 当成「识别耗时」对外汇报。

## 4. 复现步骤

```powershell
# ① 起临时 MySQL 8 并跑全套（跑完自动 SHUTDOWN，全程约 2 分钟）
& "E:\user\bupt-charging-guard\.venv\Scripts\python.exe" E:\WorkBuddy\tools\mysql8_week3.py

# ①' real 模式端到端（**必须用 .venv-algo**，后端 .venv 没有 torch）
& ".venv-algo\Scripts\python.exe" scripts\accept_real_chain.py

# ①'' 测试复跑（见 05-test-rerun.log）
.venv\Scripts\python.exe -m pytest backend/tests -q
.venv-algo\Scripts\python.exe -m pytest algo/tests -q
.venv\Scripts\python.exe -m ruff check backend scripts

# ② 库已在跑时，只想重跑闭环 / 耗时
$env:DATABASE_URL = "mysql+pymysql://root@127.0.0.1:3306/bupt_charging_guard_test?charset=utf8mb4"
$env:PYTHONUTF8 = "1"
.venv\Scripts\python.exe scripts\seed_week3_demo.py --at 2026-09-08T10:00:00
.venv\Scripts\python.exe scripts\run_pipeline.py --at 2026-09-08T10:00:00 `
    --bind-map 002.jpg=PILE-D1,003.jpg=PILE-D2,004.jpg=PILE-D3,001.jpg=PILE-D4 `
    --status-file docs\acceptance\week3\03-pipeline-mysql.json
.venv\Scripts\python.exe scripts\run_pipeline.py --at 2026-09-08T10:00:00 `
    --bind-map 002.jpg=PILE-D1,003.jpg=PILE-D2,004.jpg=PILE-D3,001.jpg=PILE-D4 `
    --timing 5 --timing-out docs\acceptance\week3\04-timing-sample.json
```

⚠️ `scripts/verify_mysql.py` 会 **DROP 并重建**目标库里的四张表（schema.sql 自带 DROP），
**永远指向独立测试库**，别指到有数据的库上。

## 5. 为什么是 ZIP 版 MySQL 而不是 Docker

本机 Docker 走不通，两条引擎都不通：

- WSL2 引擎：`wsl.exe` 被安全中心程序黑名单拦截（沙箱不允许绕过）；
- Hyper-V 引擎：Windows 版本为 `CoreCountrySpecific`（家用版），**没有 Hyper-V**。

改用 MySQL 官方 ZIP 免安装版：不装系统服务、不需要管理员权限，用完 `SHUTDOWN` 即关。
编排脚本 `E:\WorkBuddy\tools\mysql8_week3.py`（本机工具，不入仓库）负责
「起库 → 建测试库 → 跑验证 → 布场景 → 跑闭环 → 采样 → 关库」。

## 6. 2026-10-13 顺手修掉的两个真缺陷（有防回归测试）

返工对账时发现的、清单没点名的缺陷，都修了并加了测试（改前已验证测试会红）：

1. **real 识别读图目录与编排取帧目录会分叉**（串帧，A10）。
   旧实现写死 `algo/samples/frames/`，编排按 `FRAME_SOURCE_DIR` 取帧；两处不等时
   识别结果会挂到另一帧的内容摘要上。修法：`recognize.frame_source_dir()` 委托
   `pipeline.default_frame_dir()`，**收口到一处**（提交 `650709e`，4 个新测试）。
2. **real 模式 OCR 空号码被静默放过**（A09）。检出框但号码为空时，旧实现把空串交给下游，
   反查桩查不到 → 判成「无违规」，界面上像「识别成功但什么都没发生」。
   修法：空号码 → `422`，不猜号码、不落库（提交 `801fe23`，3 个新测试）。
   顺带把坏图的报错从「读不到图片（`FileNotFoundError`）」改成
   「图片无法解码」（`cv2.imread` 对缺文件与坏图都返回 `None`，混着报会让排障找错方向）。
