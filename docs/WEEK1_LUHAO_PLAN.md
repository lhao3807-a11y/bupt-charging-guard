# 第 1 周 · 吕浩开发安排（细化版）

> **依据** `docs/PLAN_4WEEKS.md` v1.0 §2.1（任务 1.1–1.10）、§2.4（验收 8 项）
> **契约** `docs/CONTRACT.md` v1.2（唯一事实源）
> **设计** `docs/design/component-inventory.md` + `design-tokens.md` + `tokens.css`
> **编写** 吕浩（统筹 / 集成 / 前端）
> **状态** 第 1 周主交付已落地，见 §2 完成度与 §5 待决事项

---

## 1. 任务拆解与依赖顺序

第 1 周的 10 项任务并非平行，实际是一条**依赖链**。按下面的顺序做，返工最少：

```
1.1 脚手架 ──▶ 1.2 令牌接入 ──▶ 1.3 通用件 ──▶ 1.4 导航/路由 ──▶ 1.6 第2页 ★
                                    │                              │
                                    │                              ▼
                             1.5 API 客户端 ──────────────▶  1.7 第1页
                                                                   │
                                                             1.8 占位路由
                                                                   │
                                                             1.9 联调 e2e ──▶ 1.10 合入
```

**关键判断**：
- **1.3（通用件）是杠杆点**。9 个通用件做扎实，第 1、2 页各只剩「排列组合」，第 2 周第 3–5 页同理。
- **1.2（令牌接入）必须在 1.3 之前**。否则组件会先写死色值、后改令牌，等于白做。
- **1.5（API 客户端）可以早就绪**，它只依赖契约 §4/§5 的类型定义，不依赖组件。
- **1.6（第 2 页）是唯一影响验收的任务**——契约 §11 第 5 项。其余任务出问题都不影响 Demo 能看。

---

## 2. 完成度对照

### 2.1 逐任务状态

| # | 任务 | 状态 | 落地位置 |
|---|---|---|---|
| 1.1 | 前端脚手架 | ✅ | `frontend/`（Vite 6 + Vue 3.5 + TS 5.6 + Element Plus 2.8 + Router + Pinia + Axios） |
| 1.2 | 接入设计令牌与主题 | ✅ | `src/styles/tokens.css`（`docs/design/tokens.css` 副本）、`main.ts` 引入顺序 tokens → element-plus |
| 1.3 | AppShell + 通用件 | ✅ | `src/components/layout/AppShell.vue` + `src/components/common/` 8 件 + `src/components/domain/` 3 件 |
| 1.4 | 侧边导航 6 项（第 6 页置灰） | ✅ | `src/router/index.ts`（顺序 = 契约 §1.1）、`AppShell.vue` |
| 1.5 | API 客户端 + 代理 | ✅ | `src/api/http.ts` + `src/api/index.ts`；`vite.config.ts` proxy → 127.0.0.1:8000 |
| 1.6 | **第 2 页 违规记录查询** ★ | ✅ | `src/views/records/RecordsView.vue` + `src/stores/records.ts` |
| 1.7 | 第 1 页 车辆信息管理 | ✅ | `src/views/vehicle/VehicleView.vue` + `src/stores/vehicle.ts` |
| 1.8 | 第 3/4/5 页占位路由 | ✅ | `src/views/{piles,statistics,config}/` → `PlaceholderView.vue` |
| 1.9 | 联调与 e2e 回归 | ⏳ | 前端 typecheck/lint/build 已过；**真机双端联调待 H 在本机执行**（需后端 + 前端同时起） |
| 1.10 | 本周集成与合入 | ⏳ | 待 1.9 完成后 commit + push |

### 2.2 契约 §11 验收清单对照

| # | 验收点 | 责任 | 状态 |
|---|---|---|---|
| 1 | `POST /api/recognize` 返回合规 `RecognitionResult` | 汤/吕 | ✅ 已过（stub） |
| 2 | `POST /api/judge` 四规则正确 | 汤 | ✅ 已过 |
| 3 | `POST /api/notify` 沙箱写库 + 日志落盘 | 吕 | ✅ 已过 |
| 4 | `GET /api/records` 分页 `total` 正确 | 吕 | ✅ 已过 |
| 5 | **后台「违规记录查询」页能看到该条记录** | **吕** | ✅ **已实现，待真机联调确认** |
| 6 | `GET /api/health`=200 | 吕 | ✅ 已过 |
| 7 | pytest 四规则 + TestClient 端点 | 汤/吕 | ✅ 57 passed |
| 8 | 本周不卡准确率 / 响应时间 | 全员 | ✅ 遵守 |

---

## 3. 关键实现口径（避免与汤/吴再对一遍）

### 3.1 状态取色：唯一入口

`src/constants/status.ts` 是**唯一**的状态→颜色映射处，严按 `design-tokens.md` §3.3：

| 场景 | 值 | 令牌前缀 |
|---|---|---|
| `rule_hit` | 1 | `danger` 红 |
| | 2 | `caution` 橙 |
| | 3 | `warning` 黄 |
| | 0 | `success` 绿 |
| `notify_status` | 未提醒 / 已提醒 / 失败 | `warning` / `success` / `danger` |
| `pile.status` | 空闲 / 充电中 / 已充满 | `info` / **品牌主色** / `caution` |
| `vtype` | 新能源 / 燃油 | `--plate-new-energy-*` / `--plate-fuel-*` |

> 组件里**不写死色值**，也不写 `--state-xxx` 字符串，一律通过这些映射函数取。

### 3.2 第 2 页筛选口径（**契约有缺口**）

契约 §6.4 只定义 `?page=&size=`，**没有筛选参数**。两种做法：

| 方案 | 优点 | 代价 |
|---|---|---|
| **当前实现**：拉取当前页 → 前端过滤 → 分页条用服务端 `total` | 不越契约、当天可用 | 筛选只作用于当前页；跨页筛选不完整 |
| 改契约加参数（`plate` / `vtype` / `rule_hit` / …） | 语义正确、可跨页 | 需改 `CONTRACT.md` + 升版本 + 汤改后端 + 补测试 |

页面上已如实提示「本页 X / Y 条命中，筛选仅作用于当前页」，**不伪装成服务端筛选**。
建议第 2 周随「6 页全部上线」一并补服务端参数。

### 3.3 第 1 页数据源（**契约有缺口**）

契约 §6 未定义 `vehicle` 的 CRUD 接口，因此第 1 页暂用 `localStorage`：
- `stores/vehicle.ts` 顶部注释写明原因与替换路径；
- 页面顶部有**黄色警示条**明确告知评审「这是本地演示数据」；
- 校验规则（车牌/手机号正则）与契约字段类型对齐。

> **不能装作已接后端**——答辩被问到会很难看。这条比"看起来完整"重要。

### 3.4 手机号脱敏（**已按建议启用，可一键关**）

`utils/format.ts` 的 `maskPhone()` 显示为 `138****6621`。
这是 `component-inventory.md` §4.1「待吕浩确认的 2 处」之一，属**展示层**处理、不改字段、不影响契约。
如需关闭，改该函数直接返回原值即可。

---

## 4. 交付物清单

```
frontend/
├── package.json / vite.config.ts / tsconfig.json / index.html
├── .eslintrc.cjs / .prettierrc.json / .prettierignore / .gitignore
├── README.md                       # 前端开发说明（含三条红线）
└── src/
    ├── main.ts                     # tokens → element-plus 引入顺序
    ├── App.vue
    ├── api/            http.ts, index.ts
    ├── components/     layout/AppShell.vue
    │                   common/{PageHeader,FilterCard,DataCard,StatusTag,
    │                           StatusPill,FormDialog,ConfirmDialog,EmptyState}.vue
    │                   domain/{PlateTag,RuleHitPill,NotifyPill}.vue
    ├── constants/      status.ts
    ├── router/         index.ts
    ├── stores/         records.ts, vehicle.ts
    ├── styles/         tokens.css（副本）, global.css
    ├── types/          contract.ts
    ├── utils/          format.ts
    └── views/          vehicle/, records/, piles/, statistics/, config/,
                        preview/, placeholder/
docs/
└── WEEK1_LUHAO_PLAN.md             # 本文件
```

---

## 5. 待 H 决策（**具体细节，需讨论**）

| # | 事项 | 选项 | 影响 |
|---|---|---|---|
| 1 | **第 2 页筛选是否走服务端** | A 保持前端过滤（不越契约）／ B 改契约 §6.4 加筛选参数 | B 更正确，但要汤改后端 + 补测试；A 当天可交付但跨页筛选不完整 |
| 2 | **第 1 页是否接后端** | A 继续 localStorage／ B 改契约增 `vehicle` CRUD 端点 | 契约 §1.1 把「车辆信息管理」列为第 1 周范围，但 §6 未给接口——**这是契约自身的缺口** |
| 3 | **第 3/4/5 页第 1 周的深度** | A 占位（当前）／ B 第 1 周就做到可用 | 契约 §1.1 标「做」，PLAN §2.1 任务 1.8 只说「占位路由」——**两份文档口径不一致** |
| 4 | 手机号是否脱敏 | A 脱敏（当前）／ B 明文 | 展示层，随时可改 |
| 5 | JSON 字段命名 | 后端返回 snake_case（`pile_id` / `occur_time` / `rule_hit`） | 前端已按契约原样用，**不做 camelCase 转换**——保持与契约逐字一致，减少对不齐的风险。如 H 要求驼峰需统一约定 |

### 5.1 关于第 3 项（**建议优先讨论**）

契约 §1.1 第 1 周范围把页面 1–5 都标「做」，但 `PLAN_4WEEKS.md` §2.1 任务 1.8 只要求
3/4/5 页「占位路由 + 不留白屏」。两者口径不同。

**现状**：按 PLAN 执行（占位），理由是第 3/4/5 页都缺接口——第 3 页要桩列表接口、
第 4 页要统计聚合接口、第 5 页要参数读写接口，**三个都要先改契约**。
若第 1 周就要做，实际是「改 3 次契约 + 汤写 3 组接口 + 前端 3 页」，工期不现实。

**建议**：在第 1 周验收说明中注明「3/4/5 页为占位」，把契约 §1.1 的表述与 PLAN 对齐，
避免第 1 周末对表时口径打架。

---

## 6. 下一步（建议顺序）

1. **H 本机跑真机联调**（任务 1.9）：
   ```bash
   # 终端 1 —— 后端
   ./.venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000 --app-dir backend
   # 终端 2 —— 前端
   cd frontend && npm run dev
   ```
   浏览器开 `http://localhost:5173` → 自动落在第 2 页 → 用 `/api/recognize` + `/api/judge`
   造一条记录 → 刷新页面应能看到 → 点「发送提醒」应变成「已提醒」。
2. 确认 §5 的 5 项决策，据此决定是否改契约。
3. 全绿后 commit（信息格式 `frontend: 第 1 周骨架 + 第 1/2 页可用`）并 push。
