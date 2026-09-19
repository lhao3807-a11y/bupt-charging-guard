# 第 1 周末 Demo 验收证据

**验收日期**：2026-09-19
**验收人**：吕浩
**契约版本**：`docs/CONTRACT.md` **v1.4**
**环境**：开发期 SQLite（`backend/app.db`）+ FastAPI 8000 + Vite 5173

> 本目录是契约 §11 的**视觉证据**。截图由真实浏览器（Chrome 153，CDP 驱动）
> 打开 `http://127.0.0.1:5173` 实拍，非设计稿、非模拟数据。

## 截图清单

| 文件 | 页面 | 路由 | 第 1 周范围 |
|---|---|---|---|
| `p1-vehicle.png` | ① 车辆信息管理 | `/vehicle` | 完整实现 |
| `p2-records.png` | ② 违规记录查询 | `/records` | 完整实现（Demo 验收项） |
| `p3-status.png` | ③ 充电状态展示 | `/piles` | 占位路由 |
| `p4-stats.png` | ④ 报警统计 | `/statistics` | 占位路由 |
| `p5-config.png` | ⑤ 系统参数配置 | `/config` | 占位路由 |
| `p6-preview.png` | ⑥ 实时识别预览 | `/preview` | 不做（导航置灰） |

## 契约 §11 逐项对照

| # | 验收项 | 状态 | 证据 |
|---|---|---|---|
| 1 | `POST /api/recognize` 返回合规 `RecognitionResult` | ✅ | `scripts/e2e_check.py` 8/8 PASS |
| 2 | `POST /api/judge` 三规则命中 + 正常返回 `null` | ✅ | e2e；`pytest backend/tests` 57 passed |
| 3 | `POST /api/notify` 沙箱写库 + 日志落盘 | ✅ | e2e；`p2-records.png` 第 3 行「已提醒」 |
| 4 | `GET /api/records` 可查、分页 `total` 正确 | ✅ | `p2-records.png` 显示「共 3 条」 |
| 5 | `GET /api/records` 筛选参数（§6.4）生效 | ⏳ | **待汤瑾睿**（`docs/TASK_TANG_v1.3.md` 任务 A） |
| 6 | 后台「违规记录查询」能看到该条记录 | ✅ | **`p2-records.png`** ← 本项为 Demo 核心 |
| 7 | 后台「车辆信息管理」可用（§6.6 CRUD） | ⏳ | **待汤瑾睿**（任务 B）；当前为 localStorage 演示，见 `p1-vehicle.png` 黄色警示条 |
| 8 | `GET /api/health` = 200 + `test_health.py` 通过 | ✅ | `curl /api/health` → `{"status":"ok"}` |
| 9 | pytest 四规则全过 + TestClient 端点全过 | ✅ | 57 passed |
| 10 | 本周不卡准确率 / 响应时间 | — | 不适用 |

**结论**：前端侧 6 页骨架就位，**第 2 页（Demo 验收项）已在真实浏览器中渲染出后端真实数据**，
#5 / #7 两项依赖汤瑾睿的后端改动（任务书已发），不影响第 2 页演示。

## 从截图可验证的设计系统约束

- **车牌底色**：`京AD67890` 新能源 → 绿底；`京A88888` 燃油 → 蓝底（`PlateTag`）
- **状态色四档**（严按 `design-tokens.md` §3.3）：充满未移车 → 黄 / 燃油占位 → 红 / 已提醒 → 绿 / 未提醒 → 橙
- **禁用态**：`已提醒` 行的「发送提醒」按钮正确置灰
- **第 6 项导航**：`实时识别预览` 带「预留」角标且不可点
- **裸色值 0 处**：`check_tokens.py` exit 0

## 复现方式

```bash
# 1) 后端
./.venv/Scripts/python.exe -m uvicorn backend.app.main:app --port 8000

# 2) 前端
cd frontend && npm run dev

# 3) 端到端
python scripts/e2e_check.py

# 4) 浏览器实拍（复用本机 Chrome，无需下载 Chromium）
export AGENT_BROWSER_EXECUTABLE_PATH="C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
agent-browser open http://127.0.0.1:5173/records
agent-browser screenshot
```
