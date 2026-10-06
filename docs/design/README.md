# docs/design — 设计系统与素材规范

> **负责人** 吴和庆（UI / 美术）
> **归属** `CONTRACT.md` §8：`docs/design/**` → 吴和庆
> **依据** `docs/CONTRACT.md` v1.2 §1.1（后台 6 页清单）
> **第 1 周交付** 5 页线框（第 1~5 页）+ 21 个素材 + 走查记录，全部通过 `tools/check_tokens.py`

本目录是后台前端的**设计与素材唯一来源**。吕浩实现 `frontend/**` 时从这里取色、取组件规格、取切图。

---

## 1. 目录结构

```
docs/design/
├── README.md                    本文件：目录说明 + 切图与命名规范
├── design-tokens.md             设计系统基线：颜色/字体/圆角/间距/阴影/布局 + 对比度实测值（§13 深色模式方案）
├── tokens.css                   令牌代码实现，前端直接 import（**未被深色方案改动**，见 walkthrough §9.6 R8）
├── tokens-dark.css              深色模式覆盖块（方案件，未启用；由 check_darkmode.py 校验）
├── component-inventory.md       6 页组件清单、Element Plus 映射、加载态规格（§2.1）、图表规格（§3.1）、
│                                ECharts 主题规范（§3.2）、列名↔契约字段映射（§4.0）、素材清单（§6）
├── copywriting.md               界面文案规范：术语表 + 按钮/错误/确认/空态 + 与前端逐条核对清单（§7）
├── a11y-report.md               可访问性基础检查：键盘可达性 / aria 覆盖 / 对比度复核 + 问题清单
├── walkthrough.md               设计走查记录：检查单结论 + 发现项 + 待回签项（第 1 周 §8、第 2 周 §9 含 §9.9 复验）
├── wireframes/                  线框 7 个：后台 6 页 + 独立登录页
│   ├── vehicle-management.html  第 1 页 · 风格样板（表格列 = vehicle 全字段）
│   ├── records.html             第 2 页 · 违规记录查询（Demo 验收项）
│   ├── pile-status.html         第 3 页 · 充电状态展示（卡片 + 列表双视图）
│   ├── statistics.html          第 4 页 · 报警统计（ECharts 三图 + 下钻）
│   ├── system-config.html       第 5 页 · 系统参数配置（阈值行内编辑）
│   ├── preview.html             第 6 页 · 实时识别预览（第 2 周解禁，任务 6.1）
│   └── login.html               登录页 · **独立页**（无侧边导航，进 `STANDALONE_PAGES` 豁免，任务 6.6）
├── dark-mode/
│   └── sample.html              深色模式样张（真加载 tokens-dark.css，任务 6.8）
├── demo/                        答辩演示素材（任务 6.10）
│   ├── README.md                素材规范 + 可复现的截图方法 + 脱敏口径
│   ├── flow-overview.html       演示流程图：识别→判定→提醒→落库 + 四层架构 + 四规则
│   ├── ppt-template.html        答辩 PPT 视觉模板（封面/目录/内容/结束，16:9）
│   └── screenshots/
│       ├── raw/                 原始实拍截图（未加工，作为「真实页面」的证据）
│       └── *-framed.png         美化版（统一设备框 + 标题条 + 图注）
├── assets/                      切图与素材（本目录下文件名与取色受校验脚本约束）
│   ├── icons/                   18 个图标：侧边导航 6 + 违规规则 4 + 通用操作 8
│   ├── logos/                   logo-full / logo-mark / logo-mono
│   └── illustrations/           空状态插画 3 个（暂无数据 / 暂无违规记录 / 筛选无结果）
└── tools/
    ├── check_tokens.py          设计校验 6 项（令牌完整性 / 对比度 / 裸色值 / 快照一致 / 素材命名与取色 / 交付物与规格）
    ├── selftest_check_tokens.py 反例打靶 21 例：改坏即 exit 1（验证断言不是空跑）
    ├── check_darkmode.py        深色方案校验（覆盖完整性 / 白底残留 / 对比度 / 底层级）
    ├── selftest_darkmode.py     反例打靶 7 例
    ├── demo_seed.py             答辩素材的演示数据：走契约端点跑「判定 → 提醒」闭环（不直连数据库）
    └── demo_screenshots.py      答辩截图：真实页面拍摄 + 统一设备框美化（取色自 tokens.css）
```

---

## 2. 切图规范

### 2.1 格式优先级

| 优先级 | 格式 | 适用 | 说明 |
|---|---|---|---|
| **1** | **SVG** | 图标、Logo、线稿、简单插画 | 矢量、可随主题改色、体积极小。**能用 SVG 就用 SVG** |
| 2 | WebP | 照片、复杂插画 | 同等画质比 PNG 小 25–35% |
| 3 | PNG | 需要透明通道且 WebP 不可用 | 仅兜底 |
| ❌ | JPG | — | 后台界面里不使用（不支持透明、有色块压缩噪点） |

### 2.2 图标

| 项 | 规范 |
|---|---|
| 画布 | `24 × 24`，`viewBox="0 0 24 24"` |
| 安全区 | 内容留 2px 边距（实际绘制区 20×20） |
| 描边 | `stroke-width: 1.5`，`stroke-linecap: round`，`stroke-linejoin: round` |
| 填充 | 默认 `fill="none"`，用描边；实心图标单独命名 |
| 颜色 | **必须用 `currentColor`**，不要在 SVG 里写死色值。这样父元素 `color` 一变，图标跟着变，才能复用设计令牌 |
| 对齐 | 与文字并排时用 `--space-1`（4px）间距，垂直居中 |

### 2.3 位图

| 项 | 规范 |
|---|---|
| 倍图 | **`@2x` 起步**，需要放大展示的提供 `@3x` |
| 命名 | 倍率后缀写在文件名末尾：`empty-state@2x.webp` |
| 导出 | 关闭「导出为 Web 所用格式」的元数据；PNG 做无损压缩 |
| 显示尺寸 | 在页面里按 1x 逻辑尺寸写 `width/height`，倍图只影响清晰度 |

### 2.4 Logo

| 项 | 规范 |
|---|---|
| 格式 | SVG（必备）+ PNG `@2x` `@3x`（兜底） |
| 版本 | 完整版（含文字）/ 图形版（仅标识）/ 单色版，共 3 个文件 |
| 最小尺寸 | 图形版不小于 `24px`；后台侧边栏用在 `28 × 28` 容器内 |
| 命名 | `logo-full.svg` / `logo-mark.svg` / `logo-mono.svg` |

侧边栏 Logo 区的规格：容器 `28 × 28`，圆角 `--radius-sm`，底 `--brand-primary`，文字 `--text-inverse`，字号 `--font-size-xs`，字重 600。

---

## 3. 命名规范

**规则：全小写 kebab-case，只允许 `a-z`、`0-9`、`-`。禁止空格、下划线、中文、大写字母。**

结构：`<类别>-<主体>[-<变体>][@<倍率>].<ext>`

| ✅ 正确 | ❌ 错误 | 错在哪 |
|---|---|---|
| `icon-vehicle.svg` | `Icon Vehicle.svg` | 大写 + 空格 |
| `icon-pile-charging.svg` | `icon_pile_charging.svg` | 下划线 |
| `icon-rule-fuel-occupy.svg` | `图标-燃油占位.svg` | 中文 |
| `empty-state-no-record.svg` | `emptyStateNoRecord.svg` | 驼峰 |
| `logo-full.svg` | `LOGO-full.svg` | 大写 |
| `demo-cover@2x.webp` | `demo-cover@2X.webp` | 倍率必须小写 `x` |

**常用类别前缀**

| 前缀 | 用途 | 示例 |
|---|---|---|
| `icon-` | 界面图标 | `icon-search.svg`、`icon-alert.svg` |
| `logo-` | 项目标识 | `logo-mark.svg` |
| `empty-` | 空状态图 | `empty-state-no-data.svg` |
| `illus-` | 插画 | `illus-occupy-scene.svg` |
| `demo-` | 答辩/文档配图 | `demo-flow-close-loop.webp` |

> 命名由 `tools/check_tokens.py` 第 4 项自动校验，不合规会直接判失败。
> 校验只认「全小写 kebab-case」，中文名、驼峰、下划线一律拦下。

---

## 4. 语义命名约定（图标与业务对齐）

图标名直接对应业务枚举，**吕浩按名引用即可，不用问「哪个图是燃油占位」**：

| 业务语义 | 契约字段 | 图标文件名 |
|---|---|---|
| 燃油车占位 | `rule_hit = 1` | `icon-rule-fuel-occupy.svg` |
| 异常占位 | `rule_hit = 2` | `icon-rule-abnormal-park.svg` |
| 充满未移车 | `rule_hit = 3` | `icon-rule-full-not-moved.svg` |
| 正常充电 | `rule_hit = 0` | `icon-rule-normal.svg` |
| 车辆信息管理 | 第 1 页 | `icon-nav-vehicle.svg` |
| 违规记录查询 | 第 2 页 | `icon-nav-records.svg` |
| 充电状态展示 | 第 3 页 | `icon-nav-pile-status.svg` |
| 报警统计 | 第 4 页 | `icon-nav-stats.svg` |
| 系统参数配置 | 第 5 页 | `icon-nav-config.svg` |
| 实时识别预览 | 第 6 页 | `icon-nav-preview.svg` |

**第 1 周不必出图标。** 先用 Element Plus 自带图标集（`@element-plus/icons-vue`）把页面跑通，
第 1 周 Demo 验收不看图标；自有图标在第 2 周替换，命名按上表预留好即可。

> **（2026-09-19 更新）图标已提前落地**：上表 10 个图标 + 6 个通用操作图标已全部产出到
> `assets/icons/`，可直接替换 Element Plus 图标。前端若第 1 周来不及替换，**不影响 Demo 验收**；
> 但第 2 周必须换完，否则侧边导航会出现两套图标风格并存。

> **（2026-09-26 更新）第 2 周已完成替换与收口（任务 6.4 / 6.7）**：
>
> - 图标共 **18 个**已同步到 `frontend/src/assets/icons/`，由 `AppIcon.vue` 统一渲染
>   （**CSS `mask-image` + `currentColor`**）——组件里**不再直接引用 `@element-plus/icons-vue`**；
> - 新增 2 个通用图标：`icon-reset.svg`（重置）、`icon-warning.svg`（警示，`ConfirmDialog` 用）；
> - 新增 1 个空态插画 `empty-state-search-empty.svg`（**筛选无结果**，与「暂无数据」「暂无违规记录」语义区分），
>   插画合计 **3 个**；
> - Logo 3 个已接入：侧边栏 28×28 用 `logo-mark.svg`（替换原「桩」字占位）、`favicon.svg` 进浏览器标签页；
> - 素材总数 **24 个**（18 图标 + 3 Logo + 3 插画），由 `check_tokens.py` 第 [4] 项校验命名与取色。
>
> ⚠️ **素材 SVG 里 `aria-label` 的真实作用范围**（详见 `a11y-report.md` §2.2）：
> 本项目通过 **CSS `mask-image`** 渲染图标，`mask` 只取形状、**不继承被遮罩元素的任何语义**，
> 因此 SVG 内部的 `role="img"` / `aria-label` **不会**被屏幕阅读器读到（改走 `<img src>` 同样需要 `alt`）。
> 它们只在「直接打开 SVG」或「内联 SVG」时有意义。**图标的无障碍语义必须靠 `AppIcon` 的 `label` prop
> 或外层按钮的 `aria-label` 提供** —— 这是约定缺口，已列 `a11y-report.md` A2 待回签。

---

## 5. 校验

```bash
# 仓库根目录执行
python docs/design/tools/check_tokens.py
```

覆盖 7 项，**交付前必须全绿**（`AGENTS.md`：交付用户前确保所有测试与验证全部通过）：

| # | 校验项 | 不通过意味着 |
|---|---|---|
| 1 | 令牌完整性（91 个必需令牌、无重复、取值合法） | 前端引用的令牌名不存在，页面会掉色 |
| 2 | WCAG 2.1 AA 对比度 | 某处文字/图形不可读 |
| 3 | 线框引用的每个 `var(--x)` 都已定义 | 令牌名拼错，静默失效 |
| 4 | 线框内联快照与 `tokens.css` 逐条一致 | 改色没同步，预览与真实页面不一致 |
| 5 | 线框不出现裸色值 | 改主题时该处不跟随 |
| 6 | `assets/` 命名 kebab-case + 取色规范（图标只用 `currentColor`） | 图标无法随主题变色 |
| 7 | **跨页一致性**（导航顺序 / 当前页高亮 / 空态齐备 / 表格规格 / 表格列名 ⊆ 契约字段 / **同表跨页列名同写法** / 间距取 4px 栅格） | 各页各做各的，或自造了契约里没有的字段 |

> 第 7 项是第 1 周新增的：把 `component-inventory.md` §5 的走查清单从「人工打勾」变成「机器断言」。
> 走查结论与反例自测记录见 `walkthrough.md`。

**想知道「全绿」是不是脚本没查到？** 跑反例自测：

```bash
python docs/design/tools/selftest_check_tokens.py   # 改坏 9 处，期望每次 exit 1；结束自动还原
```

---

## 6. 交付流程

1. **改颜色或尺寸** → 只改 `tokens.css`，改完跑校验。
   若线框里出现「快照漂移」失败，说明同步没做，按提示更新线框顶部的 tokens 快照块。
2. **加素材** → 放进 `assets/` 对应子目录，命名按 §3，跑校验确认命名合规。
3. **改设计规则** → 先改 `design-tokens.md` 的对应章节，再改 `tokens.css`，最后同步 `wireframes/`。
4. **每次改动建一个 commit**，信息用 `design: 简述`（如 `design: 补第 2 页违规记录页线框`）。
5. **需要改契约**（加字段、加页面、加接口）→ 走 `CONTRACT.md` §9 流程：
   **先改契约 → @全员 + 升版本号 → 再动设计**。设计侧不得私自新增业务字段。

---

## 7. 与契约的边界

| 本目录可以决定 | 本目录**不能**决定 |
|---|---|
| 颜色、字体、间距、圆角、阴影 | 表字段、字段类型、枚举值 |
| 组件选型与规格 | API 路径、请求/响应结构 |
| 页面内布局与信息层级 | 页面清单的增删（须先改 `CONTRACT.md` §1.1） |
| 状态色到枚举的**视觉**映射 | 规则判定逻辑与阈值 |

> 第 0 天开发文档已确认：`CONTRACT.md` 是唯一事实源。
> 设计可以「把枚举翻译成颜色」，但**不能发明枚举**。
> 本目录 §4 的图标命名表之所以能直接对着 `rule_hit` 起名，正是因为枚举来自契约而非设计。

---

## 8. 变更记录

| 版本 | 日期 | 变更 | 发起人 |
|---|---|---|---|
| — | 2026-10-06（**第二轮走查**） | 承接吕浩委托复核（`walkthrough.md` §10）留给设计侧的四项：① **6.4 图标逐处收口完成** —— 编辑 / 删除 / 发送 / 规则图标接入业务位置，并把「逐处替换」落成机器断言（前端新增 `AppIcon.test.ts`：每个图标必须在 `src` 里被引用过，附反例；`RuleHitPill.test.ts`：四条规则各渲染对应图标）；② **6.5 / 6.9 复核完成**，共记 21 处偏差与 ECharts §3.2 的 8 条逐项结论，见 `walkthrough.md` §11.3/§11.4；③ **6.10 截图补齐 7 张**（含第 3/4/5 页的**开发夹具画面**、第 6 页的预留画面），新增 `tools/demo_seed.py` 让演示数据也可复现；④ 本节目录树补 `demo_seed.py` | 吴和庆 |
| — | 2026-09-29（**交付后复核**） | 二次核对「第 2 周 14 项是否全部完成」时发现本文件 §1 目录树已过时（仍写「第 6 页第 1 周不做」「16 个图标」「2 个工具脚本」）。按**实际文件**重写目录树：线框 7 个（含 `preview.html` 与独立页 `login.html`）、图标 18、插画 3、新增 `dark-mode/`、`demo/`（含截图）、`copywriting.md`、`a11y-report.md` 与 4 个校验脚本 + `demo_screenshots.py`。同时当日补齐 6.6 前端骨架与 6.10 截图，见 `walkthrough.md` §9.9。**同日终检**：新增「答辩截图可追溯」断言（`*-framed.png` 必须对得上 `screenshots/raw/` 原件，守住 6.10「不许用线框冒充」），反例 `selftest_check_tokens.py` **19 → 21 例**，见 `walkthrough.md` §9.10 | 吴和庆 |
| — | 2026-09-19（**交付前终检**） | 终检发现第 2 页 `plate` 列名写「车牌号」，而 `occupation_record` 的契约说明与第 4 页均为「车牌」，文档/契约/线框三方分叉（白名单出自同一手，抓不到）。已统一为「车牌」；`component-inventory.md` 升 **v1.2** 新增 §4.0 列名↔契约字段映射表；`check_tokens.py` 增**同表跨页列名**断言，`selftest` 用例 **8 → 9** | 吴和庆 |
| — | 2026-09-19 | 第 1 周：5 页线框全部就位；新增 `walkthrough.md`（走查记录）；§5 校验扩到 7 项（新增跨页一致性）；§1 目录结构更新；图标提前落地（§4 已更新说明）。表格列名白名单进脚本，**自造字段会被直接拦下** | 吴和庆 |
| v1.0 | 2026-09-13 | 首版。目录说明、切图规范（格式/图标/位图/Logo）、命名规范、语义命名约定、校验与交付流程、与契约的边界 | 吴和庆 |
