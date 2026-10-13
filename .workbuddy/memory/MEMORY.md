# 项目长期记忆 —— bupt-charging-guard（桩点北邮 · 充电桩车位防占）

> 北邮大创。CV + 充电桩状态 → 判别燃油占位/异常久停/充满未移车 → 短信提醒。
> 契约唯一事实源 `docs/CONTRACT.md`（**v1.9**，2026-10-12 汤起草，**待吕浩回签**）。
> 分工：吕浩（统筹/集成/前端）、汤瑾睿（后端/DB/算法）、吴和庆（UI/美术）。

## 仓库与 git
- `https://github.com/lhao3807-a11y/bupt-charging-guard.git`；`main` 保护分支，吕浩统一合入。
- `AGENTS.md` 硬约束：**每次改动必须 commit；必须带测试，交付前全绿**。
- **`git push` 先直连试**（`GIT_TERMINAL_PROMPT=0 git push origin <branch>`）；本机代理 `127.0.0.1:7897`
  常没开（`ProxyEnable=0`），带 `-c http.proxy` 反而连不上。credential.helper=manager 正常，令牌别塞 URL。
- 当前：`feature/api-week3` HEAD = `dbadfa5`（已推送）；`origin/main` = `58a1104`；
  **分叉 behind 43 / ahead 10** → 合入前必须先同步 `main` 再审查（清单亦如此要求）。

## 第 3 周（汤 T1–T7 已交付 + 10-13 返工补件）
- 原交付 commits `19c9b28→357540a→d43e22f→5362f86→cfc648e→b33da9c`；返工补件 `650709e`、`801fe23`、`dbadfa5`。
- 门禁：**后端 326 passed** + **算法 45 passed** + `ruff check/format` 全绿。
- 核心口径（改前必改契约升版本）：
  1. `occupancy_id`（§3.6）到车生成/离车清空/换车重生成，落库快照后**永不改写**。
  2. 判重键 `(pile_id, occupancy_id, rule_hit)`（§6.2）；复用**不刷新 `occur_time`**；
     废止 v1.2「已提醒过就新增一条」（自动轮询会每轮新增+重复发短信）。
  3. `/api/notify`（§6.3）入参 = 「记录 ID + `retry` 意图」，`notify_status` **由沙箱结果产生**；
     `notify_attempts/notify_error` 持久化**重启不清零**；无手机号**不计尝试次数**；并发用
     `UPDATE ... WHERE notify_attempts=n` 的 rowcount 乐观锁。
  4. `app/pipeline.py` + `scripts/run_pipeline.py`（§6.11）= **唯一自动入口**；
     `GET /api/pipeline/status` 只读状态文件。无新帧也按当前时刻**重判时间规则**。
  5. **`notified`（状态）≠ `newly_notified`（本轮真发）** —— A05 只看后者。
     **`elapsed_ms` 是墙钟**，固定演示时刻时不能算 `finished_at - started_at`（恒 0）。
  6. 加法迁移 `app/migrate.py` + `backend/sql/migration_v1.9.sql`（SQLite/MySQL 双方言，已验证幂等）。
  7. 部署配置**不进 `system_config`**：`NOTIFY_MAX_ATTEMPTS`/`SMS_SANDBOX_RESULT`/`FRAME_SOURCE_DIR`（§7 红线）。
  8. **real 识别读图目录与编排取帧目录必须同源**（`recognize.frame_source_dir()` 委托
     `pipeline.default_frame_dir()`），否则识别结果挂到另一帧摘要上（A10 串帧）。
  9. **real 失败必须显式**：缺图 404 / 缺 CV 依赖 503 / 未检出车牌 422 / **OCR 空号码 422**。
     空号码若放过 → 反查桩查不到 → 静默判「无违规」，看起来像成功。
- 返工凭据（`docs/acceptance/week3/`）：`01` MySQL 31/31、`02` 场景、`03` MySQL 闭环、`04` 耗时、
  `05` 测试复跑、`06` **real 端到端 9/9**、`07` 验收矩阵、`08` 三人签认表（**待吕/吴签**）。
  对账文档 `docs/week3/TANG_WEEK3_REWORK_RESPONSE.md`。

## 算法 / CV 现状
- 线上默认权重 `algo/runs/detect/train_real_web/weights/best.pt`（CCPD+web 合并）。
  谱系：`train/`（**合成集，只能证链路，勿用于真实图**）→ `train_real/`（纯 CCPD）→ `train_real_web/`。
- 真实集端到端：OCR 整串 91.25% / 牌色 95.00% / 端到端全对 88.75%；**蓝牌 85.14% 是已知短板**。
- 实拍集 `algo/dataset_web/` 174 张（val 36）：检出 91.7% / OCR 84.85% / 牌色 93.94%。
- OCR 走**整帧**并按 IoU 锚定检测框（裁剪 ROI 只有 82.5%；整帧取最高分多车会串号 → 短信发错人）。
- ⚠️ hyperlpr3 返回 `[号码, 置信度, 牌色, 框]`；旧代码解析顺序写错 → OCR 曾静默返回空串。
  **第三方返回结构必须先打印实测再写解析。**
- ⚠️ `cv2.imread` 对「文件不存在」与「损坏图」都返回 None，**必须分开报错**。
- ⚠️ `dataset_real/meta.json` 的 key 已带 `.jpg`（合成集的不带）。

## 规则引擎（4 条，改前必改契约）
按 `plate` 反查 `charging_pile.bound_plate`；查不到 → `None`（不编造桩关联）。
`start_time` 复用为到达时间；判定时刻取 `frame_time`（不读系统时钟）；阈值只从 `system_config` 读，
缺失抛 `ConfigMissingError`。`rule_hit`：1 燃油占位 / 2 异常久停 / 3 充满未移 / ④ 正常返回 `None`。

## 接口口径
- 识别模式开关**只认环境变量 `RECOGNITION_MODE`**（未设置 = stub），别往 `system_config` 加键。
- `/api/records` 7 参数 AND，先 filter 再 count；枚举参数**空串 = 不筛选**，非法值才 422。
- 车辆 CRUD：`plate` 主键不可改；重复 409 / 不存在 404 / DELETE 204；
  `occupation_record.plate` **永久不加 FK**。车牌 `^[\u4e00-\u9fa5][A-Z][A-Z0-9]{5,6}$`，手机 `^1[3-9]\d{9}$`。

## 环境基线（本机）
- Python **3.11.9**（勿 3.13）；后端 venv `.venv`；**算法测试必须 `.venv-algo`**
  （`.venv` 无 ultralytics，跑 `pytest algo/tests` 只得 5 passed/4 skipped，看着绿其实没测到）。
  已往 `.venv-algo` 补装 `sqlalchemy pymysql cryptography`。
- 开发 SQLite（`backend/app.db`），目标 MySQL 8。**Docker 不可用**（wsl 被黑名单拦、家用版无 Hyper-V）→
  用官方 ZIP 免安装版，一键脚本 `E:\WorkBuddy\tools\mysql8_week3.py`（起库→验证→闭环→采样→关库，不入仓库）。
- lint 只跑 `ruff check backend scripts`（`docs/design/tools/**` 不在范围内，`ruff format .` 会误格式化吴的脚本）。

## 本机 shell 踩坑（每次都会遇到）
- **Bash 工具 PATH 极易损坏**：`grep/head/tail/dirname/cd` 常全缺 → 除 `git` 外一律用 **PowerShell**；
  找文件/搜内容改用 Grep/Glob 工具。
- **PowerShell 工具 stdout 常回显为空**：判断结果必须 `... | Out-File -Encoding utf8 <文件>` 再读。
  `Tee-Object -FilePath` 默认写 **UTF-16**，别用。
- 回退单文件**别用** `git show x:path | Out-File -NoNewline`（多行会塌成一行）→
  先备份再 `git checkout -- <path>`，跑完拷回并用 MD5 核对。
- 抓 pytest 结果要正则 `(\d+ (passed|failed)[^\r\n]*)`，`Select-Object -Last 2` 会抓到 safe-delete 噪声。
- `.git/index.lock` 残留会让 checkout 半途失败并成批删文件 → 确认无 git 进程后删锁，再 `git checkout -- .`。

## 可复用手法：验证「回归测试真的会红」
改完源码后把源文件临时还原成旧版，跑新测试确认**会失败**，再还原。
自动生成的验收脚本模板见 `scripts/accept_real_chain.py`（真实照片跑完整闭环 + 断言表）。
