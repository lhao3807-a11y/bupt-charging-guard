# 吕浩 · 第 1 周完成情况审查

> **审查日期**：2026-09-19
> **审查对象**：`PLAN_4WEEKS.md` §2.1（任务 1.1–1.10）+ 契约 §11 验收清单
> **审查方式**：**不采信自评文档，全部复跑复现**。三项硬门禁 + 前端三验证 + 真实 HTTP e2e + 逐文件字节比对。
> **契约版本**：`docs/CONTRACT.md` **v1.4**

## 一、结论

**任务完成度 8/10，§11 验收 6/8。核心目标（第 2 页可演示）达成，但有 2 项实质未完成、3 项遗留隐患。**

| 维度 | 结果 |
|---|---|
| PLAN 任务 1.1–1.10 | **8 ✅ / 2 ⏳**（1.9、1.10 未完成） |
| 契约 §11 验收 8 项 | **6 ✅ / 2 ⏳**（第 5 项筛选、第 7 项车辆 CRUD） |
| 三项硬门禁 | **全绿** |
| 前端三验证 | **全绿** |
| e2e 闭环 | **8/8 PASS** |

> **判据**：第 1 周的核心是契约 §11 第 5 项「后台能看到违规记录」。
> 该项**已用真实浏览器截图证明达成**（`docs/acceptance/week1/p2-records.png`），
> 故本周**主线目标成立**，可进入第 2 周。

---

## 二、复跑证据（全部实跑，非引用）

| # | 验证项 | 命令 | 实测结果 |
|---|---|---|---|
| 1 | 后端测试 | `pytest backend/tests -q` | **57 passed**，1 warning |
| 2 | Python lint | `ruff check backend scripts` | **All checks passed**（exit 0） |
| 3 | 设计令牌校验 | `check_tokens.py` | **exit 0**，5 页漂移 0 / 裸色值 0 |
| 4 | 反例自测 | `selftest_check_tokens.py` | **13/13 全部拦下**，还原后 exit 0 |
| 5 | 前端类型 | `vue-tsc --noEmit` | **exit 0**，零错误 |
| 6 | 前端构建 | `vite build` | **成功**，6 页 code-split |
| 7 | 前端 lint | `eslint .` | **exit 0**，0 错 0 警 |
| 8 | 端到端闭环 | `scripts/e2e_check.py` | **8/8 PASS**，`ALL PASSED` |
| 9 | 前端裸色值 | grep `#[0-9A-Fa-f]{3,8}` | **0 处** |
| 10 | 令牌漂移 | `diff docs/design/tokens.css frontend/...` | **逐条一致，零漂移** |

**反向验证（关键）**：契约 §6.4 的筛选参数**实测无效**——
`GET /api/records?rule_hit=3` 返回了 `rule_hit=1` 的记录，`total` 也未随筛选变化。
后端**忽略了全部筛选参数**，说明汤瑾睿尚未开工（符合预期，任务书 `TASK_TANG_v1.3.md` 已发）。

---

## 三、逐任务对照

| # | 任务 | 判定 | 证据 / 缺口 |
|---|---|---|---|
| 1.1 | 前端脚手架 | ✅ | Vite 6 + Vue 3.5 + TS 5.6 + EP 2.8 + Router + Pinia + Axios，可 dev/build |
| 1.2 | 接入设计令牌 | ✅ | `src/styles/tokens.css` 存在（是我初查漏看），`main.ts` 顺序 tokens → EP → global 正确；裸色值 0 |
| 1.3 | AppShell + 通用件 | ✅ | 超预期：11 件（9 规格件 + `PlateTag`/`RuleHitPill`/`NotifyPill` 3 领域件） |
| 1.4 | 导航 6 项（第 6 置灰） | ✅ | `navRoutes` 顺序 = 契约 §1.1；`reserved` → `:disabled` + 「预留」角标 |
| 1.5 | API 客户端 + 代理 | ✅ | 5 端点封装；proxy → `127.0.0.1:8000` 实测通 |
| 1.6 | **第 2 页** ★ | ⚠️ **功能达成，口径未切** | 页面可用、真实数据渲染（截图存证）；但筛选仍是**前端过滤当前页**，未走 §6.4 参数 |
| 1.7 | 第 1 页 | ⚠️ **UI 达成，数据源临时** | 全字段列 + 弹窗 + 二次确认齐备；但用 **localStorage**，未接 §6.6 |
| 1.8 | 第 3/4/5 页占位 | ✅ | `PlaceholderView` 标出「开发中」+ 计划周次 + 依赖缺口，无白屏 |
| 1.9 | **联调与 e2e 回归** | ⏳ **未完成** | `e2e_check.py` 仍是**纯后端 API**，未扩到前端；前端 typecheck/lint/build 虽过，但不等于联调 |
| 1.10 | 本周集成与合入 | ⏳ **部分** | 4 个提交已 push，`main` 干净；但 1.9 未完 → 本任务未达标 |

---

## 四、契约 §11 验收 8 项

| # | 验收点 | 判定 | 说明 |
|---|---|---|---|
| 1 | `POST /api/recognize` 返回合规结果 | ✅ | e2e PASS |
| 2 | `POST /api/judge` 四规则正确 | ✅ | 实测规则④ 返回 `null`，规则①/③ 命中 |
| 3 | `POST /api/notify` 沙箱写库 + 日志 | ✅ | e2e PASS |
| 4 | `GET /api/records` 分页 `total` 正确 | ⚠️ | 全表分页正确；**筛选后 `total` 不生效** |
| 5 | **后台页能看到记录** ★ | ✅ | **真实浏览器截图** `p2-records.png` |
| 6 | `GET /api/health`=200 + 冒烟 | ✅ | 200 `{"status":"ok"}` |
| 7 | 车辆 CRUD（§6.6） | ⏳ | **两端点均 404**，后端未实现 |
| 8 | 不卡准确率 / 响应时间 | ✅ | 遵守 |

---

## 五、发现的问题（按严重度）

### 🔴 P0-1：`stores/vehicle.ts` 与 `RecordsView.vue` 注释**过时且误导**

契约 v1.3 已补齐缺口，但代码里仍写「契约未定义」：

- `frontend/src/stores/vehicle.ts:4` —— 「契约未定义 `vehicle` 表的增删改查接口（**§6 只有 5 个端点**）」
- `frontend/src/views/records/RecordsView.vue:158` —— 页面 info 条仍向用户展示「**契约 §6.4 未定义筛选参数**」

**危害**：契约 v1.4 §6.4/§6.6 白纸黑字定义了这些接口。
这个提示条是**给老师演示时能看到的**，会直接暴露"文档与实现不符"。
**修法**：后端就绪前，两处注释/文案改为「**契约已定义，后端待实现**」，语义必须反转为"等后端"而非"没定义"。

### 🔴 P0-2：1.9「e2e 扩到前端」未做，1.10 因此不达标

`scripts/e2e_check.py` 只打后端 API。PLAN 明写「真机起后端 + 前端，走通识别→判定→提醒→第 2 页看到记录」。
**当前缺自动化**——第 2 页的闭环是我**手工**用浏览器验的，没进脚本，下一个人无法一键复现。

### 🟠 P1：`tokens.css` 同步机制**根本不存在**

- `frontend/src/styles/tokens.css` 文件头自称"与 `docs/design/tokens.css` 逐字一致，由 `frontend/scripts/copy-tokens.mjs` 比对"
- **该文件不存在**，`package.json` 也**无对应脚本**
- 实测**当前零漂移**，但这是运气——上游改了忘同步，**无人拦**

**修法**：写 `copy-tokens.mjs` 做比对（或把这两份文件的 diff 并入 `check_tokens.py`），
并在 `package.json` 加 `"check:tokens"` 脚本。

### 🟡 P2：提交信息与实际内容不符

`c574aac`（信息为"契约 v1.3"）里夹带了 `WEEK1_LUHAO_PLAN.md` 的**新增**——
文档首次提交被塞进契约提交，事后追溯困难。违反 `AGENTS.md` 的 `模块: 简述` 规范。

### 🟡 P2：构建产物 1.1MB，有优化空间

`index-P1XpHpZ3.js` **1,100.30 kB**（gzip 353.51 kB），触发 Vite 警告。
不阻塞第 1 周，但第 4 周"打包优化"任务要处理。

---

## 六、超预期完成项

1. **契约缺口主动补齐**（v1.3）—— 发现 §6 无 vehicle CRUD、§6.4 无筛选参数、§1.1 与 PLAN 表述冲突，
   **先改契约再改代码**，完全符合「契约是唯一事实源」的纪律
2. **列名口径收归单一事实源**（v1.4）—— 发现同一字段列名散落 4 处且**已实际分叉**，
   新增 §3.5 映射表并让 `check_tokens.py` **从契约解析白名单**，删掉硬编码
3. **反例自测扩到 13 例**（原 9 例）—— 新增 4 条契约侧反例，证明"改契约就能拦下"非空跑
4. **回签不采信自评** —— 对吴和庆的交付独立复跑，并**有理有据地不采纳**其「设计侧不再有阻塞项」的结论
5. **ruff 修复带行为等价证明** —— 重构 `build_doc_html.py` 后，用「渲染产物与已提交版**逐字比对**」证明行为不变

---

## 七、下一步（按优先级）

| 优先级 | 事项 | 责任 | 说明 |
|---|---|---|---|
| 🔴 P0 | 反转两处过时注释/文案 | 吕浩 | 后端就绪前也要先改，避免演示时暴露 |
| 🔴 P0 | 补 `scripts/e2e_check.py` 前端段 | 吕浩 | 1.9 收尾，让第 2 页闭环可一键复现 |
| 🟠 P1 | 补 `copy-tokens.mjs` 或并入校验 | 吕浩 | 消除令牌同步盲区 |
| ⏳ | 筛选 7 参数 + 车辆 CRUD | 汤瑾睿 | `docs/TASK_TANG_v1.3.md`，后端就绪后前端切两处 |
| 🟡 P2 | 提交规范 | 全员 | 一提交一主题 |

---

## 八、审查方法说明（可复现）

本审查**不依赖任何自评文档**，全部结论来自实跑：

```bash
# 三项硬门禁
.venv/Scripts/python.exe -m pytest backend/tests -q
.venv/Scripts/python.exe -m ruff check backend scripts
.venv/Scripts/python.exe docs/design/tools/check_tokens.py
.venv/Scripts/python.exe docs/design/tools/selftest_check_tokens.py

# 前端三验证（沙箱需先清代理变量）
cd frontend && node node_modules/vue-tsc/bin/vue-tsc.js --noEmit
node node_modules/vite/bin/vite.js build
node node_modules/eslint/bin/eslint.js .

# 端到端（需先起后端）
cd backend && ../.venv/Scripts/python.exe -m uvicorn app.main:app --port 8000 &
.venv/Scripts/python.exe scripts/e2e_check.py

# 反向验证：筛选参数是否真生效（本次发现后端未实现）
curl --noproxy '*' "http://127.0.0.1:8000/api/records?rule_hit=3"
# → 返回含 rule_hit=1 的记录 ⇒ 筛选被忽略

# 分叉分支内容核验（不是整分支 merge，是按目录摘取）
git diff --stat origin/feature/ui-week1:docs/design origin/main:docs/design
# → 4 文件差异，经查全部是 main 侧主动改造（回签 + 列名收归），非遗漏
```

**关于两个「未合入」分支的澄清**：
`git merge-base --is-ancestor origin/feature/ui-week1 origin/main` 返回非 0，
但这**不代表内容丢失**——经逐文件比对，`docs/design/` 全部 38 个文件在 `main` 上**全部存在**，
且 main 侧是**超集**（多出回签 §8 与列名改造）。属正常的「按目录摘取」合入。
