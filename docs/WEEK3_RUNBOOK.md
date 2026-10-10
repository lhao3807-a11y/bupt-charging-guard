# 第三周本地演示运行手册（阶段性）

> 当前版本只能启动已有 FastAPI 与 Vue 前端。自动识别编排、自动沙箱发送与 `/api/pipeline` 结果接口尚未合入；此手册不代表 M4–M6 自动闭环已完成。

## 前置条件

- 仓库根目录，Python 项目环境 `.venv` 和前端 `frontend/node_modules` 已安装。
- 默认本机 SQLite 路径由 `backend/app/db.py` 管理；需要 MySQL 时按 `.local/mysql8/README.txt` 启动服务，并使用独立演示库。
- real CV 识别使用算法环境 `.venv-algo`、本机忽略的模型权重和 `algo/samples/frames/` 图片。权重未随 Git 入库。

## 启动已有后端

在仓库根目录打开 PowerShell 窗口 A：

```powershell
$env:NO_PROXY = '*'
$env:no_proxy = '*'
# 默认 stub，保证没有算法环境时仍能运行已有演示闭环。
..\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

需要 real CV 实拍验证时，在新窗口设置模式并运行算法环境：

```powershell
$env:NO_PROXY = '*'
$env:no_proxy = '*'
$env:RECOGNITION_MODE = 'real'
..\.venv-algo\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

real 与 stub 共用端口，一次只启动其中一个。real 模式只接受 `algo/samples/frames/` 中 basename 匹配的 JPG/PNG；加载流程尚未将任意 `FRAME_SOURCE_DIR` 的图像交给识别器。不得把接口读取到的自定义目录截图声称为 real CV 处理结果。

## 启动前端

窗口 B：

```powershell
Set-Location frontend
npm run dev
```

打开 Vite 输出的网址（默认 `http://127.0.0.1:5173`）。页面经 Vite `/api` 代理调用 `http://127.0.0.1:8000`。后台现有路径包括 `/records`、`/piles`、`/statistics`、`/config` 和 `/preview`。

## 当前手工闭环与限制

已有 `scripts/e2e_check.py` 覆盖历史 20 项 FastAPI/Vite HTTP 验收，演示 stub 识别、判定落库、人工点按沙箱端点更新提醒并在记录页查询。当前 `/api/notify` 的入参含调用方指定状态，它仍是早期写库桩；“已提醒”响应目前不能证明自动发送、失败重试、去重或真实短信发送。

模拟器可用 `scripts/simulate_piles.py` 单步或按固定时刻推进；HTTP API 为 `POST /api/piles/simulate`。本次端到端计划中的四个可控场景、自动通知服务及持久化尝试记录，仍依赖后端周三任务完成。

## 完成自动编排后的启动要求

本段等 `scripts/run_pipeline.py` 与 `backend/app/routers/pipeline.py` 合入后补全：按服务责任分窗口启动编排器、设置帧源和结果查询地址、自检 `/api/health` 与编排状态、确认关闭/重启行为，并指向对应专项 E2E 和 MySQL 演示库。当前没有该脚本或端点，不要手工创建同名假入口。
