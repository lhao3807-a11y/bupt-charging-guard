# frontend —— 「桩」点北邮 · 后台管理平台

> **技术栈** Vue 3 + Vite + TypeScript + Element Plus + Vue Router + Pinia + ECharts
> **契约** `docs/CONTRACT.md` v1.2（唯一事实源，**任何结构变动先改契约再升版本**）
> **设计** `docs/design/**`（`tokens.css` 是唯一色彩与尺寸来源）
> **排期** `docs/PLAN_4WEEKS.md` §2.1（吕浩第 1 周任务 1.1–1.10）

---

## 1. 快速开始

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173
```

后端需同时启动（Vite proxy 把 `/api` 转发到 `127.0.0.1:8000`）：

```bash
# 仓库根目录
./.venv/Scripts/python.exe -m uvicorn backend.app.main:app --reload --port 8000
```

## 2. 常用命令

| 命令 | 作用 |
|---|---|
| `npm run dev` | 开发服务器（5173，proxy → 8000） |
| `npm run build` | `vue-tsc` 类型检查 + 生产构建 |
| `npm run typecheck` | 只做类型检查 |
| `npm run lint` | ESLint，`--max-warnings 0` |
| `npm run format` | Prettier 格式化 |

**交付前**（对齐 `AGENTS.md` 与 `PLAN_4WEEKS.md` §5）：

```bash
npm run typecheck && npm run lint && npm run build
# 仓库根目录三件套
./.venv/Scripts/python.exe -m pytest backend/tests -q
./.venv/Scripts/python.exe -m ruff check backend scripts
./.venv/Scripts/python.exe docs/design/tools/check_tokens.py
```

## 3. 目录结构

```
frontend/src/
├── api/
│   ├── http.ts              # axios 实例 + 统一错误提取
│   └── index.ts             # 契约 §6 五个端点封装
├── components/
│   ├── common/              # 通用件（component-inventory.md §2）
│   │   ├── PageHeader.vue
│   │   ├── FilterCard.vue
│   │   ├── DataCard.vue
│   │   ├── StatusTag.vue
│   │   ├── StatusPill.vue
│   │   ├── FormDialog.vue
│   │   ├── ConfirmDialog.vue
│   │   └── EmptyState.vue
│   ├── domain/              # 业务件（复用状态色映射）
│   │   ├── PlateTag.vue     # 车型标签，取车牌底色
│   │   ├── RuleHitPill.vue  # 违规类型，§3.3①
│   │   └── NotifyPill.vue   # 提醒状态，§3.3②
│   └── layout/
│       └── AppShell.vue     # 侧栏 220 + 顶栏 56 + 内容区
├── constants/
│   └── status.ts            # 状态 → 令牌前缀映射（唯一入口）
├── router/index.ts          # 6 页导航，顺序 = 契约 §1.1
├── stores/
│   ├── records.ts           # 第 2 页
│   └── vehicle.ts           # 第 1 页
├── styles/
│   ├── tokens.css           # ⚠️ docs/design/tokens.css 的逐字副本，勿直接编辑
│   └── global.css           # 全局基础样式（无裸色值）
├── types/contract.ts        # 契约 §3/§4/§5 类型，**手写对齐**
├── utils/format.ts          # 时间 / 手机号 / bbox 格式化
└── views/                   # 6 页 + 占位 + 404
```

## 4. 三条硬规矩（不可越，`PLAN_4WEEKS.md` §5「红线」）

1. **页面里不出现裸色值**，一律 `var(--token)`。
   状态取色只走 `src/constants/status.ts` 的映射函数（严按 `design-tokens.md` §3.3），
   组件里不许自选色。
2. **表格列以契约字段为准**，不自造字段、不自造枚举。
   页面增删列须先改 `CONTRACT.md` §1.1 并升版本。
3. **阈值一律从 `system_config` 读**（契约 §7），前端不兜底默认值。

### tokens.css 同步

`src/styles/tokens.css` 是 `docs/design/tokens.css` 的副本（吴和庆拥有原件）。
上游改动后同步：

```bash
cp docs/design/tokens.css frontend/src/styles/tokens.css
```

校验脚本 `check_tokens.py` 以 `docs/design/tokens.css` 为准。

## 5. 第 1 周交付范围

| # | 页面 | 状态 |
|---|---|---|
| 1 | 车辆信息管理 | ✅ 实现（本地存储，见下） |
| 2 | 违规记录查询 | ✅ 实现（**Demo 验收项**，接 `GET /api/records`） |
| 3 | 充电状态展示 | ⬜ 占位（契约 §1.1 属第 1 周范围，待排） |
| 4 | 报警统计 | ⬜ 占位（排第 2 周） |
| 5 | 系统参数配置 | ⬜ 占位（排第 2 周） |
| 6 | 实时识别预览 | ⬜ 导航置灰预留（契约 §1.1 明确第 1 周不做） |

## 6. 两处「契约缺口」的处置（**契约已补齐，等后端实现**）

> 2026-09-19 契约升至 **v1.3**，两处缺口已在**契约侧**补齐。
> 但**后端尚未实现**（实测：`?rule_hit=3` 仍返回 `rule_hit=1` 的记录、`/api/vehicles` 返回 404），
> 后端改动任务书见 `docs/TASK_TANG_v1.3.md`。
> **后端接口就绪后，前端需做两处切换**（代码里已留好替换点）。

### 6.1 第 2 页筛选 → 待切服务端

- **契约现状**：§6.4 已定义 7 个筛选参数（`plate`/`vtype`/`pile_id`/`rule_hit`/`notify_status`/`start_time`/`end_time`），
  AND 关系，`total` 随筛选变化。
- **前端现状**：**后端未实现筛选**，故仍是**前端过滤当前页**（`stores/records.ts`），页面有 info 条如实标注。
- **待办**：后端就绪后，把 `filters` 作为查询参数传给 `fetchRecords`，改为服务端筛选与分页。
  这样跨页筛选才正确，同时移除页面上的提示条。

### 6.2 第 1 页数据源 → 待切后端

- **契约现状**：§6.6 已定义车辆 CRUD 四端点（`GET/POST /api/vehicles`、`PUT/DELETE /api/vehicles/{plate}`）。
- **前端现状**：**后端未实现**（404），故仍是 `localStorage`（`stores/vehicle.ts`），页面顶部有黄色警示条。
- **待办**：后端就绪后替换 `stores/vehicle.ts` 的实现为 `api/` 调用，并**移除页面顶部的警示条**
  （该条是"未接后端"的诚实标注，接了就该撤掉）。
  注意契约口径：`plate` 不可改、重复新增返回 `409`、`DELETE` 返回 `204` 且**不级联删违规记录**。

---

## 9. 设计令牌同步（**已脚本化，勿再人肉 cp**）

`src/styles/tokens.css` 是 `docs/design/tokens.css` 的逐字副本，设计侧是唯一事实源。

```bash
npm run check:tokens    # 校验两份文件是否逐条一致（有漂移即 exit 1，交付前必跑）
npm run sync:tokens     # 从设计侧覆盖前端副本
npm run verify          # 一键：check:tokens + typecheck + lint + build
```

脚本 `scripts/copy-tokens.mjs` 只比对 `--token: value` 定义本身，**忽略文件头注释差异**
（前端副本会多一段「本文件是副本」的说明，属预期）。

> 与 `docs/design/tools/check_tokens.py` 的分工：
> 那个管**合规性**（令牌齐全 / WCAG 对比度 / 页面裸色值 / 列名口径）；
> 这个管**一致性**（两份 tokens.css 是否同源）。**两者都要跑。**

## 10. 端到端验证

```bash
# 需同时起后端(8000)与前端(5173)
../.venv/Scripts/python.exe ../scripts/e2e_check.py
```

`scripts/e2e_check.py` 覆盖两段（共 12 项）：
- §1–8 **后端 API 闭环**：health → recognize → judge → notify → records → 容错 → 规则①
- §9–12 **前端联调**：dev server 起得来 → Vite 代理通 → 第 2 页数据源含目标记录 → 入口资源可加载

前端未起时 §9–12 会明确报 FAIL，**不静默跳过**。
