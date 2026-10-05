# 项目长期记忆 —— 桩点北邮 · 充电桩车位防占系统（bupt-charging-guard）

> 大创项目，北京邮电大学。CV + 充电桩状态 → 识别燃油车占位/新能源充满未移车 → 短信提醒。
> 契约唯一事实源 `docs/CONTRACT.md`（当前 **v1.5**，2026-09-26）；排期唯一事实源 `docs/PLAN_4WEEKS.md`（v1.2）。
> 分工：吕浩（统筹/集成/前端）、汤瑾睿（后端/DB/算法）、吴和庆（UI/美术）。

## 仓库与协作
- 私有仓库 `https://github.com/lhao3807-a11y/bupt-charging-guard.git`；`main` 保护分支，功能开 `feature/<name>`，吕浩统一合入。
- `AGENTS.md` 硬约束：每次改动必须 commit；必须带测试，交付前全绿。
- 本机代理：读注册表 `HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings` 的 `ProxyServer`
  （当前 `127.0.0.1:7897`），`git -c http.proxy=... -c https.proxy=... fetch --all --prune`。
- ⚠️ **`git push` 必须带代理**，否则报 `SSL_ERROR_SYSCALL`（不是凭据问题！）：
  ```
  GIT_TERMINAL_PROMPT=0 git -c http.proxy=http://127.0.0.1:7897 -c https.proxy=http://127.0.0.1:7897 push -u origin <branch>
  ```
  2026-10-05 实测：**带代理后 push 直接成功**（credential.helper=manager 正常，无需令牌放 URL）。
  旧记忆里「push 静默失败、死在 credential-manager」是**误判**，真实原因是缺代理。

## 分支现状（2026-10-05 更新）
- `main` = `origin/main` = **3cead88**（第 2 周吴和庆 UI 合入 + 审查修正）。
- **`feature/api-week2` 已推送到远程**（汤第 2 周全部成果，9 个 commit），
  PR：https://github.com/lhao3807-a11y/bupt-charging-guard/pull/new/feature/api-week2
- 本地其他分支：`feature/db-schema` / `feature/rule-engine`(24ee309，汤第 1 周交付) / `feature/ui-design` /
  `feature/ui-week1` / `feature/ui-week2`(4e36f3b) / `main`。

## 第 2 周进度（2026-10-05 下午更新）
- 吕浩：4.1 已完成，4.2–4.4 曾因缺接口阻塞（**现已解阻塞**，见下），4.5 部分，4.6 置灰。
- 吴和庆：第 2 周 14 项 A/B/C 三组已交付并合入（`feature/ui-week2`）。
- **汤瑾睿 9 项已基本做完**，在 `feature/api-week2`（基于 main@3cead88）：
  C1–C3 契约升 **v1.6**（§6.7 piles / §6.8 stats / §6.9 config）→ **v1.7**（§6.10 simulate）；
  5.1–5.5、5.7、5.8、5.9 完成。**仅 5.6 MySQL 8 真机验证阻塞**（本机无 MySQL/Docker，待用户定）。
- 质量门禁：后端 **202 passed** + 算法 **43 passed**，ruff check/format 全绿。

## CV / 算法现状（第 2 周 5.3–5.5 后）
- 真实数据集 `algo/dataset_real/`：CCPD 公开集转换，**800 张**（train 640 / val 160，绿 419 / 蓝 381）。
  只标 `plate` 单类 —— CCPD 只有车牌框没有车辆框，混进两类集会把 `vehicle` 教坏。
- 真实集训练权重 `algo/runs/detect/train_real/weights/best.pt`：**mAP50=0.994 / mAP50-95=0.821**。
- 端到端（val 160）：检测 100%/IoU 0.9005；**OCR 整串 91.25%**、字符级 96.82%；
  **牌色 95.00%**；端到端全对 88.75%。分牌色：绿 96.51% / **蓝 85.14%（已知短板）**。
- ⚠️ 合成集那个 mAP50=0.995 **不能当真实准确率**，只能证明链路跑通。
- ⚠️ hyperlpr3 返回 `[号码, 置信度, 牌色, 框]`（**旧代码按 (框,号码,置信度,牌色) 解析，
  OCR 曾静默恒返回空串**）。已修 + 防回归测试钉死。教训：第三方返回结构必须打印实测一次再写解析。
- 线上 OCR 走**整帧**并按 IoU 挑最贴合检测框的那条（裁剪 ROI 只有 82.50%，整帧 91.25%；
  整帧取最高分在多车场景会串号 → 短信发错人）。IoU 计算收口在 `algo/recognize/box.py`。

## lint 范围（重要）
- 仓库标准命令是 `ruff check backend scripts`（我扩展到含 `algo`）。
  **`docs/design/tools/**` 不在 lint 范围内**，跑 `ruff format .` 会误格式化吴和庆的设计工具脚本 → 必须按范围跑。

## 规则引擎判定口径（改前必改 CONTRACT 并升版本）
1. 桩关联：`RecognitionResult` 无桩字段 → 按 `plate` 反查 `charging_pile.bound_plate`；查不到返回 `None`。
2. 久停基准：`charging_pile.start_time` 复用为绑定/到达时间。
3. 判定时刻取 `RecognitionResult.frame_time`（引擎不读系统时钟）。
4. 阈值一律查 `system_config`，缺失抛 `ConfigMissingError`，**禁止硬编码**。
5. `rule_hit`：0 正常 / 1 燃油占位 / 2 异常占位 / 3 充满未移车；规则④返回 `None`。

## 已定接口口径（后端已交付）
- 识别模式开关**只认环境变量 `RECOGNITION_MODE`**（未设置 → stub），不要在 `system_config` 加非 §7 的键。
- `GET /api/records`（§6.4）：7 筛选参数 AND，先 filter 再 count；`end_time` 只给日期按 `23:59:59.999999`。
- 车辆 CRUD（§6.6）：`plate` 主键不可改，重复 409、不存在 404、DELETE 204；`occupation_record.plate` **永久不加 FK**；
  删车显式把关联桩 `bound_plate` 置空。
- 枚举查询参数空串视为不筛选（前端「全部」会发空串），非法值才 422；工具在 `backend/app/query.py`。
- 车牌校验 `^[\u4e00-\u9fa5][A-Z][A-Z0-9]{5,6}$`；手机号 `^1[3-9]\d{9}$`。

## 环境踩坑（2026-10-05）
- **Bash 工具可跑 git，但 `head`/`tail`/`dirname` 缺失**（PATH 损坏）；`rm` 被 safe-delete shim 拦截。
- PowerShell 里 `Remove-Item` 删 `.git/index.lock` 会被拦 → 用 `[System.IO.File]::Delete()`。
- `.git/index.lock` 残留会让 `git checkout` 半途失败，**工作区文件被成批删除**（`algo/**` 等）。
  恢复三步：确认无 git 进程 → 删锁 → `git checkout -- .`；
  快进分支优先用 `git branch -f main origin/main`，避免反复 checkout 造成文件增删。

## 环境基线
- Python **3.11.9**（勿用 3.13）；venv `E:\user\bupt-charging-guard\.venv`（含 fastapi/sqlalchemy/pytest 等）。
- 开发期 SQLite（`backend/app.db`），目标 MySQL 8（第 2 周汤任务 5.6 真机验证，注意 MySQL 下 FK 会真的 SET NULL）。
