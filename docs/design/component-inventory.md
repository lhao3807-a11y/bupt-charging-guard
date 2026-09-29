# 后台组件清单与 Element Plus 映射

> **版本** v1.3（2026-09-19 · §4.0 改为指针，列名唯一事实源收归 `CONTRACT.md` §3.5）
> **负责人** 吴和庆（UI / 美术）；v1.3 由吕浩修订
> **依据** `docs/CONTRACT.md` v1.4（§1.1 六页清单 + **§3.5 显示列名映射表**）、`design-tokens.md`、`wireframes/`
> **用途** 吕浩据此实现前端；本文件只**列清单和映射**，不新增业务字段。
> **校验** `python docs/design/tools/check_tokens.py`（第 5 项逐页核对表格列名，白名单**从契约 §3.5 派生**）

---

## 1. 一句话

6 页后台共用同一套骨架和同一批组件，只有「数据列 / 表单字段 / 图表」不同。
**先把通用件做出来，6 页就是 6 次排列组合。**

```
通用件（做一次，6 页复用）
├── AppShell          侧边栏 220px + 顶栏 56px + 内容区
├── PageHeader        页面标题 + 说明 + 右侧操作槽
├── FilterCard        栅格化筛选表单 + 查询/重置
├── DataCard          标题栏（标题 + 总数）+ 表格 + 分页
├── StatusTag         标签：车型 / 状态（浅底 + 描边 + 深字）
├── StatusPill        胶囊：带圆点的状态徽标
├── FormDialog        新增/编辑弹窗（520px）
├── ConfirmDialog     危险操作二次确认（420px）
└── EmptyState        空状态
```

---

## 2. 组件规格总表

规格值全部来自 `tokens.css`，**不要另定**。

| 组件 | 高度/尺寸 | 圆角 | 字号 | 关键令牌 |
|---|---|---|---|---|
| 主按钮 / 次按钮 | `32px` | `--radius-sm` | `--font-size-base` | `--brand-primary` / `--border-strong` |
| 输入框 / 下拉 / 日期 | `32px` | `--radius-sm` | `--font-size-base` | `--border-strong`；聚焦 `--brand-primary` + `--brand-primary-bg` 光晕 |
| 表格单元格 | padding `12px 16px` | — | `--font-size-base` | 表头 `--fill-light`；行线 `--border-light`；悬浮 `--brand-primary-bg` |
| 表格表头 | `44px` | — | `--font-size-sm` / 500 | `--fill-light` 底 + `--text-secondary` |
| 标签 StatusTag | `22px` | `--radius-xs` | `--font-size-xs` | `--state-*-bg` / `-border` / `-text` |
| 胶囊 StatusPill | `24px` | `--radius-pill` | `--font-size-xs` | `--state-*-bg` / `-border` / `-text` + `-solid` 圆点 |
| 卡片 | — | `--radius-md` | — | 白底 + `--border-base` + `--shadow-sm` |
| 弹窗 | 宽 `520px` | `--radius-lg` | 标题 `--font-size-md` | `--shadow-lg` + `--bg-mask` 遮罩 |
| 确认弹窗 | 宽 `420px` | `--radius-lg` | — | 图标底 `--state-warning-solid` + 深字 |
| 分页 | `28px` | `--radius-sm` | `--font-size-sm` | 当前页 `--brand-primary` 描边 + 字色 |
| 侧边导航项 | 高 `40px` | `--radius-sm` | `--font-size-base` | 选中 `--brand-primary-bg` + `--brand-primary` |
| 顶栏 | 高 `56px` | — | `--font-size-sm` | 白底 + `--border-base` 下边线 |

### 2.1 加载态规格（v1.4 新增 · 对应 PLAN §3.3 任务 6.2）

§5 第 8 项在第 1 周自述「加载态是前端实现细节，线框不画骨架屏，**第 2 周补**」—— 本节即补齐。
给出三类骨架的 `el-skeleton` 规格，**全部取自 `tokens.css`，不要另定数值**。
线框观感见 `wireframes/preview.html` 的「加载态样张」一节，实现照那三块做即可。

**三类共用的四条约束**

1. 骨架块底色 `--fill-light`、圆角 `--radius-sm`；**不加渐变扫光动画**（演示环境不需要，且会与真实内容抢注意力）。
2. 骨架块与真实内容**同位置、同尺寸** —— 数据到达后不产生位移，即「不跳版」。
3. 骨架期间**禁用容器内交互**（与 `FilterCard` 的 `loading` 行为一致），避免用户点到还没渲染出来的按钮。
4. **已知文本不套骨架条**：表头、卡片标题、页头文案这些不依赖接口，直接显示真实文案；只有「数字/内容未知」的部分才用骨架条。

**① 表格骨架**（第 1、2、5、6 页）

| 项 | 规格 |
|---|---|
| 行数 | **`8` 行** = 一屏可见行数。**不要按「每页 20 条」画满** —— 会比真实内容还长，反而像卡死 |
| 行高 | 与真实行一致：单元格 `padding: var(--space-3) var(--space-4)`，行高 `44px` |
| 列宽对齐 | 复用真实表头列宽（第 1 页为 `160 / 120 / 140 / 160 / 200 / 140`） |
| 骨架条宽度 | 取所在列宽的 **60% / 80% 交替**，避免排成整齐色块阵列 |
| 骨架条高度 | `12px`，圆角 `--radius-sm` |
| 列数 | **等于真实列数**，含「操作」列也要留骨架（否则数据到达时整行会重排） |

**② 卡片骨架**（第 3 页桩卡片）

| 项 | 规格 |
|---|---|
| 网格 | **`3` 列 × `2` 行 = 6 张** = 一屏可见卡片数 |
| 列间距 / 行间距 | `gap: var(--space-4)` |
| 卡片内边距 | `var(--space-4)` |
| 卡片描边 / 圆角 | `1px solid var(--border-base)` + `--radius-md`（与真实卡片一致；`--shadow-sm` 可省略） |
| 卡内骨架条 | 3 条：标题 `40%` / 副信息 `64%` / 正文 `100%`，条高 `12px`，条间距 `var(--space-3)` |
| 窄屏 | 宽度 < `1280px` 降为 `2` 列，**仍保持 2 行**（行数不随列数变，否则卡片会被拉长） |

**③ 图表骨架**（第 4 页 ECharts）

| 项 | 规格 |
|---|---|
| 容器高度 | **必须锁定**，与真实图一致：柱 `230px`、环 `240px`、线 `200px`。不锁定就会出现「图加载完成时整页跳一下」 |
| 容器描边 / 圆角 | `1px solid var(--border-base)` + `--radius-md`；图内不加圆角容器（同 §3.1 ③） |
| 柱状占位 | 4 根柱，宽 `28px`，高按 `48 / 72 / 36 / 60` 错落，`align-items: flex-end`，柱间距 `var(--space-3)` |
| 文案 | 容器居中「图表区加载中…」，字号 `var(--font-size-sm)`、色 `--text-tertiary` |

> **与空态的区别（最容易做错的一处）**：**加载中**显示骨架屏；**确无数据**显示 `el-empty`（§3.1 ⑤ 已定）。
> 两者语义相反 —— 骨架是「等一下就有」，空态是「等也没有」。混用会让演示时看不出系统是否正常。

**④ 时长与超时**

- 骨架出现即请求已发出，**不设最小展示时长**（本地接口很快，强行延时反而显得卡）。
- 超过 `10s` 未返回则转**失败态**：`el-alert`（danger）+「重试」按钮，**不要无限转圈**。
- 若接口返回 `404`（如第 6 页取不到帧），直接进空态，不进失败态 —— 那是「确实没有」，不是「出错」。

---

## 3. 全局 Element Plus 组件清单

按用途分组，**括号里是 `tokens.css` 已覆盖到的变量或需要额外注意的点**。

| 分组 | Element Plus 组件 | 用途 | 备注 |
|---|---|---|---|
| 布局 | `el-container` / `el-aside` / `el-header` / `el-main` | 后台骨架 | 宽高取 `--layout-*` |
| 导航 | `el-menu` / `el-menu-item` | 侧边 6 页导航 | 选中态用主色浅底 + 主色字；第 6 项 `disabled` 置灰 |
| 导航 | `el-breadcrumb` | 顶栏面包屑 | `--text-tertiary` |
| 导航 | `el-avatar` | 顶栏用户 | 主色浅底 `--brand-primary-light-9` |
| 容器 | `el-card` | 筛选区、表格容器 | 圆角 `--radius-md`；**建议关掉 el-card 自带阴影改用 `--shadow-sm`** |
| 表单 | `el-form` / `el-form-item` | 筛选、弹窗表单 | label 用 `--text-secondary` |
| 表单 | `el-input` | 车牌号、车主、手机号 | 车牌/手机号加 `.mono` 等宽类 |
| 表单 | `el-select` / `el-option` | 车型筛选、桩状态 | |
| 表单 | `el-date-picker`（`type="daterange"`） | 录入时间、命中时间范围 | |
| 表单 | `el-input-number` | 第 5 页阈值配置 | 单位「分钟」，后缀用 `el-input` 的 `append` |
| 表单 | `el-switch` | 第 5 页开关型参数 | 主色 |
| 表单 | `el-radio-group` / `el-radio-button` | 第 4 页统计维度切换 | 选中用主色 |
| 操作 | `el-button` | 主/次/文字按钮 | 主按钮 `--brand-primary`；删除用 `danger` + `text` 形态 |
| 操作 | `el-popconfirm` / `el-message-box` | 删除二次确认 | 文案需说明后果（见 §4.1 标注 6） |
| 操作 | `el-message` | 操作结果提示 | |
| 数据 | `el-table` / `el-table-column` | 6 页主体 | 表头底色 `--fill-light`；悬浮行 `--brand-primary-bg` |
| 数据 | `el-pagination` | 分页 | 后端返回 `items+total+page+size`（契约 §6.4），直接用 `total` |
| 数据 | `el-tag` | 车型标签 | 需自定义 class 走 `--plate-*` 令牌 |
| 数据 | `el-descriptions` | 第 3 页桩详情 | 描边模式 |
| 数据 | `el-progress` | 第 3 页充电进度（演示用） | 主色 |
| 数据 | `el-statistic` | 第 4 页统计大数 | 字号 `--font-size-xl`；数字 `tabular-nums` |
| 数据 | `el-image` | 第 6 页帧截图 | 第 1 周不做，仅预留 |
| 反馈 | `el-empty` | 无数据 | |
| 反馈 | `el-skeleton` | 加载中 | |
| 反馈 | `el-tooltip` | 违规规则、字段说明 | |
| 反馈 | `el-alert` | 第 5 页改阈值的风险提示 | 用 `--state-warning-*` |
| 反馈 | `el-badge` | 违规条数角标 | 用 `--state-danger-*` |

> **图表**：第 4 页需要柱状/折线/饼图。Element Plus 无图表组件，
> 建议引入 **ECharts**，主色取 `--brand-primary`，状态色序列取
> `--state-danger-solid` → `-caution-solid` → `-warning-solid` → `-success-solid`
> （与 §3.3 的严重度梯度一致）。**这条超出 Element Plus 范围，需吕浩确认选型。**

> ✅ **已确认选用 ECharts（2026-09-13，吕浩）**。前端约定：
> - 依赖 `echarts` + `vue-echarts`，按需引入（`BarChart` / `LineChart` / `PieChart` + 必要组件），不全量打包。
> - 配色**从 `tokens.css` 的 CSS 变量读取**（`getComputedStyle(document.documentElement).getPropertyValue('--token')`），
>   **不要在图里写死十六进制** —— 否则改主题时图表不跟随，也过不了 `check_tokens.py` 的裸色值校验。
> - 序列顺序固定为严重度梯度：danger 红 → caution 橙 → warning 黄 → success 绿。
> - 第 4 页若需统计聚合接口，**先改 `CONTRACT.md` 再升版本**，不得前端硬凑。

### 3.1 第 4 页图表规格（ECharts）—— v1.1 新增

线框：`wireframes/statistics.html`（图与本表同源，改一处要同步另一处）。

**① 序列配色：顺序即严重度，不是审美选择**

| series | 对应 | 令牌 | 色 |
|---|---|---|---|
| `1` | `rule_hit = 1` 燃油车占位 | `--state-danger-solid` | 红 |
| `2` | `rule_hit = 2` 异常占位 | `--state-caution-solid` | 橙 |
| `3` | `rule_hit = 3` 充满未移车 | `--state-warning-solid` | 黄 |
| `4` | `rule_hit = 0` 正常充电 | `--state-success-solid` | 绿 |

> 与第 2 页表格的 `StatusPill` 色**完全同序**。跨页换色会让用户在两个页面之间重新学一遍颜色。

**② 分类份额（饼图 / 环形图）不用违规色**

「按桩占比」是份额比较而非严重度，用红橙黄会暗示「份额大的桩更严重」。按份额从大到小取：

| 序位 | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| 令牌 | `--brand-primary` | `--brand-primary-light-3` | `--brand-primary-light-5` | `--brand-primary-light-7` | `--state-info-solid` | `--state-info-border` |

**③ 图元 → 令牌 映射（逐项照抄，不要临场发挥）**

| 图元 | 令牌 / 规格 |
|---|---|
| 柱体 / 折线（按序列） | `--state-*-solid`（同 ①） |
| 单序列趋势线 | `--brand-primary`，`lineWidth: 2`，`symbolSize: 6` |
| 折线下方面积 | `--brand-primary-bg`，`opacity: 1`（不再二次调透明度） |
| 坐标轴主线 | `--border-base`，`lineWidth: 1` |
| 网格分隔线 | `--border-light`，只保留横向，`type: 'dashed'` |
| 轴刻度文字 | `--text-tertiary`，字号 `--font-size-xs`，字族 `--font-family-base` |
| 数值标签 | `--text-secondary`，字号 `--font-size-xs`，仅柱状图显示 |
| 图例 | 置于底部横向，`textStyle.color = --text-secondary`，色块与序列同色 |
| 提示框 | 背景 `--bg-container`，`borderColor: --border-base`，`borderWidth: 1`，阴影 `--shadow-lg`，文字 `--text-primary`，数值 `--font-family-mono` + `tabular-nums` |
| 图表容器圆角 | 由外层 `el-card` 控制（`--radius-md`），图内不加圆角容器 |

**④ 三张图的规格**

| 图 | 类型 | X / 分类 | Y / 数值 | 说明 |
|---|---|---|---|---|
| 按命中规则分布 | 柱状图 | `rule_hit` 枚举（1 / 2 / 3，**不含 0**） | 条数，从 0 起不截断 | 顶部显示数值标签；点击柱体下钻 |
| 违规趋势 | 折线图 | 日期（近 7 天 / 30 天） | 条数，从 0 起不截断 | 单序列用主色；面积填充 `--brand-primary-bg` |
| 按桩占比 | 环形图 | 桩 ID（Top 6 + 其他） | 占比 % | 中心显示总数；分类份额色见 ② |

**⑤ 交互与状态**

- **下钻**：点柱体 → 下方明细表按该 `rule_hit` 过滤，过滤条件用 `el-tag`（可关闭）展示，**不新增路由**。
- **维度切换**：`el-radio-button`（按规则 / 按天 / 按桩），只换聚合口径，不换数据源。
- **空数据**：`occupation_record` 为空时显示 `el-empty`（线框给的是 `--state-success-solid` 打勾插画），**不画一张全 0 的图**。
- **加载态**：`el-skeleton` 占位，容器高度固定（柱 520×230、环 240×240、线 520×200 的比例），避免数据到达后跳版。
- **响应式**：`resize` 时调 `chart.resize()`；宽度 < 1280px 时两张并排图改为单列堆叠。

**⑥ 数据来源与口径**

数据源 `occupation_record` 按 `rule_hit` / 时间聚合。契约 §6 **目前只有 `GET /api/records`**，没有统计接口：

- 第 1 周：前端用 `/api/records` 分页拉取后在本地聚合，**不改契约**。
- 第 2 周若数据量增大需要后端聚合 → 走「先改 `CONTRACT.md` → @全员 → 升版本号」流程。
- 自检口径：**三个规则分项之和必须等于总数**（第 4 页最容易出的错就是这个对不上）。

---

### 3.2 ECharts 主题规范（v1.4 新增 · 对应 PLAN §3.3 任务 6.9）

> **与 §3.1 的分工**：§3.1 回答「第 4 页画什么」（图型 / 序列 / 下钻口径），
> 本节回答「怎么让 ECharts 长成设计系统要求的样子」—— 给出一份**可注册的 theme**，
> 吕浩照抄即可，不需要在 `option` 里逐项写样式。

**0) 一条硬约束：JS 里不出现十六进制色值**

ECharts 的配置吃的是**真实色值**，不认 `var(--token)`。若为了省事直接抄令牌的 hex，
就违反了红线 1（页面里不出现裸色值），且改主题时图表不跟随。正确做法是
**运行时从 `:root` 读 CSS 变量**，再交给 ECharts：

```ts
// frontend/src/charts/tokens.ts —— 图表侧的令牌读取层
const TOKENS = getComputedStyle(document.documentElement)

/** 读令牌原值，如 '#CF1322' / '12px' */
export const token = (name: string): string => TOKENS.getPropertyValue(name).trim()

/** 读数值型令牌，如 '--font-size-xs' → 12 */
export const px = (name: string, fallback: number): number =>
  Number.parseFloat(token(name)) || fallback

/** hex → rgba，用于 areaStyle 的透明度，避免在代码里写 rgba(...) 裸值 */
export const alpha = (hex: string, a: number): string => {
  const [r, g, b] = [1, 3, 5].map((i) => Number.parseInt(hex.slice(i, i + 2), 16))
  return `rgba(${r}, ${g}, ${b}, ${a})`
}
```

> 令牌快照必须在**挂载后**读取（`onMounted`），早于样式表生效会读到空串。
> `check_tokens.py` 第 [3] 项只扫线框 HTML，扫不到 TS，**这条靠评审守**。

**① 色板序列（两套，用途不同不可混用）**

| 用途 | 序位 | 令牌 | 说明 |
|---|---|---|---|
| **语义序列**（按 `rule_hit` 分布 / 趋势按规则拆分） | 1 / 2 / 3 / 4 | `--state-danger-solid` / `--state-caution-solid` / `--state-warning-solid` / `--state-success-solid` | **顺序 = 严重度**，见 §3.1 ①。任何图里出现这四色，顺序不得变 |
| **份额序列**（按桩占比等分类份额） | 1–6 | `--brand-primary` / `--brand-primary-light-3` / `--brand-primary-light-5` / `--brand-primary-light-7` / `--state-info-solid` / `--state-info-border` | 见 §3.1 ②。份额不是严重度，**不得**借语义色 |

**② 网格与坐标轴**

| 项 | 规格（全部取令牌） |
|---|---|
| 容器内边距 | `grid: { left: 8, right: 8, top: 24, bottom: 8, containLabel: true }`（单位为 px 的**数字**，ECharts 不支持 var） |
| 横向网格线 | `splitLine: { show: true, lineStyle: { color: token('--border-light'), type: 'dashed' } }` |
| 纵向网格线 | **关闭**（`splitLine.show = false`）—— 纵向线会和柱体/折线抢视觉 |
| 坐标轴主线 | `axisLine: { show: true, lineStyle: { color: token('--border-base') } }` |
| 轴刻度 | `axisTick: { show: false }`（有网格线就不需要刻度） |
| 轴文字 | `axisLabel: { color: token('--text-tertiary'), fontSize: px('--font-size-xs', 12) }` |
| 轴文字截断 | 类目名超 6 字用 `axisLabel.formatter` 截断加 `…`，**不倾斜文字**（倾斜后字号观感变小） |
| 数值轴起点 | `min: 0`，**不截断**（§3.1 ④ 已定）；`scale: false` |
| 字体 | `textStyle.fontFamily = token('--font-family-base')`（数值标签另用 `--font-family-mono`） |

**③ 提示框（tooltip）**

| 项 | 规格 |
|---|---|
| 触发 | 柱/环 `trigger: 'item'`；折线 `trigger: 'axis'` + `axisPointer: { type: 'line', lineStyle: { color: token('--border-strong') } }` |
| 背景 | `backgroundColor: token('--bg-container')` |
| 描边 | `borderColor: token('--border-base')`，`borderWidth: 1` |
| 阴影 | `extraCssText: 'box-shadow: ' + token('--shadow-lg')` |
| 文字 | 标题/键 `color: token('--text-secondary')`，值 `color: token('--text-primary')` |
| 数值字体 | `fontFamily: token('--font-family-mono')` + `font-variant-numeric: tabular-nums`（等宽，避免数字跳动） |
| 默认样式 | **关掉 ECharts 自带的 `color`/`border` 覆盖**，`confine: true` 防溢出容器 |

**④ 图例**

| 项 | 规格 |
|---|---|
| 位置 | 底部横向：`legend: { bottom: 0, left: 'center', orient: 'horizontal' }` |
| 图标 | `itemWidth: 8, itemHeight: 8, itemGap: px('--space-4', 16)`，**方形**（`icon: 'rect'`），与 `StatusPill` 色块同形 |
| 文字 | `textStyle: { color: token('--text-secondary'), fontSize: px('--font-size-xs', 12) }` |
| 选中态 | 默认 ECharts 行为（置灰未选项）即可，未选项用 `inactiveColor: token('--text-disabled')` |
| 环图 | 分类 ≥ 5 项时图例改**右侧竖排**（`orient: 'vertical', right: 0, top: 'middle'`），否则底部会挤成两行 |

**⑤ 无数据态：** **不画空图**

- 判定：`total === 0`（或所有 series 的 `value` 求和为 0）→ **不渲染图表**，替换为 `el-empty`
  （第 4 页用 `--state-success-solid` 打勾插画那版文案，见 §3.1 ⑤）。
- **禁止**用 ECharts 的 `graphic` 或 `title.subtext` 在空图里写「暂无数据」——
  会出现「有坐标轴没有柱子」的破图，演示时最像系统坏了。
- 与加载态的分工见 §2.1 ③：**加载中**给骨架、**确无数据**给空态，两者不可互换。

**⑥ 主题注册（可直接复制）**

```ts
// frontend/src/charts/theme.ts
import * as echarts from 'echarts'
import { token, px } from './tokens'

let registered = false

/** 注册并返回主题名；重复调用只注册一次 */
export function ensureChartTheme(): string {
  const name = 'bupt-guard'
  if (registered) return name

  const mono = token('--font-family-mono')
  const axisLabel = { color: token('--text-tertiary'), fontSize: px('--font-size-xs', 12) }

  echarts.registerTheme(name, {
    color: [
      token('--state-danger-solid'), token('--state-caution-solid'),
      token('--state-warning-solid'), token('--state-success-solid'),
    ],
    backgroundColor: 'transparent',            // 底色交给外层 el-card
    textStyle: { fontFamily: token('--font-family-base') },
    grid: { left: 8, right: 8, top: 24, bottom: 8, containLabel: true },
    categoryAxis: {
      axisLine:  { show: true, lineStyle: { color: token('--border-base') } },
      axisTick:  { show: false },
      axisLabel,
      splitLine: { show: false },
    },
    valueAxis: {
      axisLine:  { show: false },
      axisTick:  { show: false },
      axisLabel,
      splitLine: { show: true, lineStyle: { color: token('--border-light'), type: 'dashed' } },
    },
    legend: {
      bottom: 0, left: 'center', icon: 'rect',
      itemWidth: 8, itemHeight: 8, itemGap: px('--space-4', 16),
      textStyle: { color: token('--text-secondary'), fontSize: px('--font-size-xs', 12) },
      inactiveColor: token('--text-disabled'),
    },
    tooltip: {
      backgroundColor: token('--bg-container'),
      borderColor: token('--border-base'),
      borderWidth: 1,
      textStyle: { color: token('--text-primary') },
      extraCssText: `box-shadow: ${token('--shadow-lg')}`,
      confine: true,
    },
    line: { itemStyle: { borderWidth: 2 }, symbolSize: 6 },
    bar:  { itemStyle: { borderRadius: [Number(token('--radius-xs').replace('px', '')) || 2] } },
  })

  registered = true
  return name
}
```

用法（`vue-echarts`）：

```vue
<VChart :option="option" :theme="chartTheme" autoresize class="chart-canvas" />
```
```ts
import { ensureChartTheme } from '@/charts/theme'
const chartTheme = ensureChartTheme()   // 在 onMounted 之后调用
```

**⑦ 复核清单：与吕浩第 4 页实现逐条对齐（待回签）**

> 以下 8 条**由吕浩实现后逐条回签**；吴和庆负责比对，**不直接改代码**（同任务 6.5 的原则）。

| # | 检查点 | 期望 | 回签 |
|---|---|---|---|
| 1 | TS 里无十六进制色值 | `grep -nE '#[0-9A-Fa-f]{6}' frontend/src/charts/` 无输出 | ☐ |
| 2 | 主题已注册且被 3 张图共用 | 无 `option` 内联 `color: [...]` | ☐ |
| 3 | 语义序列顺序 | 红 → 橙 → 黄 → 绿（柱图/趋势图按规则拆分时） | ☐ |
| 4 | 份额序列未借用违规色 | 环图用主色梯度，无红/橙/黄 | ☐ |
| 5 | 网格线 | 仅横向、`--border-light`、虚线 | ☐ |
| 6 | tooltip 数值等宽 | `--font-family-mono` + `tabular-nums` | ☐ |
| 7 | 无数据态 | total=0 时 `el-empty` 替换图表；**无「有轴无柱」的破图** | ☐ |
| 8 | 三分项之和 = 总数 | 自检口径，见 §3.1 ⑥ | ☐ |

> ⚠️ **前置依赖**：契约 **C2（`GET /api/stats`）尚未定义**（`CONTRACT.md` §6 目前只有 `GET /api/records`）。
> 本节把**与数据结构无关的视觉部分**（色板 / 网格 / 坐标轴 / tooltip / 图例 / 空态）先定死；
> 等 C2 落地后，只需复核 **序列与维度映射**（第 3、4 条）是否仍成立，其余条款不受影响。
> 任务书 §附 亦提示「6.9 建议等 C2 定义后再做」—— 故本节的**收口时点定在 C2 之后**。

---

## 4. 逐页清单

### 4.0 列名与 `prop` 的取用方式（v1.3 改为指针，不再复述列名）

> **v1.3（2026-09-19，吕浩）**：本节原本逐条列出「显示标签 → 契约表.字段」，是列名的**第四份副本**。
> 现列名的**唯一事实源已收归 `CONTRACT.md` §3.5「显示列名映射表」**，本节只保留
> 「怎么用」的说明，不再复述名称 —— 避免同一信息多处维护、改一处漏三处。

**取用顺序**（写前端表格时照此三步，不要凭印象写 label）：

1. 打开 `CONTRACT.md` §3.5，按「页面列」找到本页对应的行（P1–P5 对应第 1–5 页）；
2. `el-table-column` 的 `label` **照抄**该表的「列名」列，`prop` 用同行的「字段」列；
3. 若本页需要 §3.5 里没有的列 → **先改契约**（§3.5 加行 + 升版本号），再回到第 1 步。

**跨页通用列**：`操作` 不属于任何表字段，是纯 UI 交互列，不进 §3.5，由
`check_tokens.py` 单独放行（每个含表格的页面都允许出现一次）。

**两条容易搞错的边界**（`check_tokens.py` 已断言，犯错即失败）：

- **同表同字段必须同列名，跨表允许不同。** `plate` 在第 1 页显示「车牌号」（属 `vehicle` 表）、
  在第 2/4 页显示「车牌」（属 `occupation_record` 表）—— 这是**有意为之**，判定粒度是「表 + 字段」。
- **改列名的入口只有一个。** 只改线框或只改前端而不改 §3.5，会被 [5] 项断言拦下。

### 4.1 第 1 页 · 车辆信息管理 —— 风格样板

**线框**：`wireframes/vehicle-management.html`（其余 4 页照此对齐，已全部就位）
**v1.1 补齐**：空态区块（第 0 天交付时遗漏，见 `walkthrough.md` 发现项 F1）

| 区域 | 组件 | 字段 / 内容 |
|---|---|---|
| 页头 | `PageHeader` | 标题「车辆信息管理」+ 说明 + 右侧「批量导入」「新增车辆」 |
| 筛选 | `el-form`（行内栅格） | 车牌号 `el-input`、车型 `el-select`、车主 `el-input`、录入时间 `el-date-picker`、查询/重置 |
| 表格 | `el-table` | **列 = `vehicle` 全字段**：车牌号 / 车型 / 车主 / 手机号 / 录入时间，另加「操作」列 |
| 表格 | 单元格渲染 | 车牌号 `.mono` + 500 字重；车型 `el-tag` 走 `--plate-*`；手机号 `.mono`；时间 `.mono` |
| 操作列 | `el-button`（text） | 编辑（主色）/ 删除（`--state-danger-text`）+ `el-popconfirm` |
| 分页 | `el-pagination` | 每页 20 条 |
| 弹窗 | `FormDialog` | 新增/编辑共用：车牌号 / 车型 / 车主 / 手机号；车牌号主键，**编辑态只读** |
| 弹窗 | `ConfirmDialog` | 删除确认，需说明「违规记录保留但不再关联手机号，后续无法自动提醒」 |
| 空态 | `el-empty` | 无车辆时引导「新增车辆」 |

**待吕浩确认的 2 处**（线框标注 ② ③）：
1. 手机号是否脱敏显示（`138****6621`）。仅改展示不改字段，但契约未规定。
2. 车型标签取车牌底色（新能源绿 / 燃油蓝）是否接受与「正常绿」同色系。

---

### 4.2 第 2 页 · 违规记录查询（Demo 验收项）

**线框**：`wireframes/records.html`

| 区域 | 组件 | 字段 / 内容 |
|---|---|---|
| 页头 | `PageHeader` | 标题 + 说明（数据来自 `occupation_record`） |
| 筛选 | `el-form` | 车牌、车型、桩 ID、命中规则 `rule_hit`、提醒状态 `notify_status`、命中时间范围 |
| 表格 | `el-table` | 列 = `ViolationRecord`：ID / 车牌 / 车型 / 桩 ID / 命中规则 / 命中时间 / 提醒状态 / 提醒时间 / 操作 |
| 状态渲染 | `StatusPill` | `rule_hit` 按 `design-tokens.md` §3.3① 映射 红/橙/黄/绿；`notify_status` 按 ② 映射 黄/绿/红 |
| 操作 | `el-button` | 「发送提醒」调 `POST /api/notify`，**v1.2 起入参必须带 `id`**，成功后 `el-message` 提示并刷新该行 |
| 分页 | `el-pagination` | 用响应里的 `total`（契约 §6.4） |
| 数据源 | `GET /api/records?page=&size=` | |

**本页三条硬约束**（线框标注已逐条写明）：

1. **`id` 列必须展示**——它是 `/api/notify` 的入参与去重定位键，藏进 tooltip 会让联调无法核对。
2. **表中不出现 `rule_hit = 0`**——规则 ④ 返回 `null` 不落库（契约 §6.2），筛选下拉只给 1 / 2 / 3。
3. **前端不做去重**——同 `pile_id` + 同 `rule_hit` 且未提醒时后端复用原记录（契约 v1.2 §6.2），前端自行合并会导致与统计页数字不一致。

> **验收清单**（契约 §11）要求「后台违规记录查询页面能看到该条记录」，
> 所以这一页是第 1 周**必须上线**的页面，优先级高于其余 4 页。

---

### 4.3 第 3 页 · 充电状态展示

**线框**：`wireframes/pile-status.html`（卡片视图 + 列表视图并列给出，字段一致）

| 区域 | 组件 | 字段 / 内容 |
|---|---|---|
| 页头 | `PageHeader` | 标题 + 说明 + 视图切换（卡片 / 列表） |
| 免责 | `el-alert`（info） | 「充电状态为模拟数据，预留 OCPP 适配层」——**答辩时避免被误解为真实接口** |
| 概览 | `el-statistic` × 3 | 空闲 / 充电中 / 已充满 的桩数量 |
| 卡片网格 | `el-card` + `StatusPill` | 每桩一卡：桩 ID（等宽）、状态胶囊、绑定车牌（等宽）、开始/结束时间 |
| 表格视图 | `el-table` | 列 = `charging_pile` 全字段，供「列表/卡片」切换 |
| 状态渲染 | `StatusPill` | `空闲` 中性灰 / `充电中` 主色蓝 / `已充满` 橙（§3.3③） |
| 详情 | `el-descriptions` + `el-progress` | 描边模式；进度条为演示用视觉，**不新增字段** |

> 开发大纲 M7 只要求「充电状态展示」，卡片式比表格更适合答辩讲解，
> 但表格便于核对字段，故两者都给，用 `el-radio-button` 切换。
> **「空闲 + 有绑定车牌」是真实场景**（车停了没充），即规则 ② 的判定输入。

---

### 4.4 第 4 页 · 报警统计

**线框**：`wireframes/statistics.html`　**图表规格**：本文件 §3.1

| 区域 | 组件 | 字段 / 内容 |
|---|---|---|
| 页头 | `PageHeader` | 标题 + 时间范围（近 7 天 / 近 30 天）+ 导出 |
| 统计卡 | `el-statistic` × 4 | 总违规数、燃油车占位、异常占位、充满未移车（各自用对应状态色） |
| 维度切换 | `el-radio-group` | 按 `rule_hit` / 按天 / 按桩 |
| 图表 | **ECharts** | 柱状图（按 `rule_hit` 分布）、折线图（按天趋势）、环形图（按桩占比） |
| 图例色 | ECharts 配色 | 见 §3.1：红 → 橙 → 黄 → 绿；分类份额改用主色梯度 |
| 表格 | `el-table` | 明细下钻（点图表柱子后过滤，过滤条件用 `el-tag` 可关闭） |

> 数据源：`occupation_record` 按 `rule_hit` / 时间聚合。
> 契约未定义专门统计接口，第 1 周前端本地聚合；若第 2 周需要后端聚合，
> **需走「先改 `CONTRACT.md` 再升版本」流程**（详见 §3.1 ⑥）。
> 自检：三个规则分项之和必须等于总数。

---

### 4.5 第 5 页 · 系统参数配置

**线框**：`wireframes/system-config.html`

| 区域 | 组件 | 字段 / 内容 |
|---|---|---|
| 页头 | `PageHeader` | 标题 + 「撤销改动」+「保存并生效」 |
| 风险提示 | `el-alert`（warning） | 「修改阈值将直接影响规则引擎判定结果，建议在无正在进行的演示时调整」 |
| 参数表 | `el-table` + 行内编辑 | 列 = `system_config` 全字段：参数键 `key` / 参数值 `value` / 说明 `note` |
| 阈值编辑 | `el-input-number` | `full_timeout_min`（充满超时阈值，默认 30）、`abnormal_park_min`（异常占位久停阈值，默认 30），`append` 单位「分钟」 |
| 未保存态 | 底部提示条 | 改动行主色描边，表底压黄色条列出「哪个键、从多少改到多少」 |
| 保存确认 | `el-message-box` | 正文写清「改前 → 改后」+ 影响面，不用「确定要保存吗」这种无信息量文案 |
| 取值范围 | 行内校验 | 大于 0 的整数；填 0 会让规则恒不命中，等于关掉该条判定 |
| 空态 | `el-empty` | 种子未写入时表格为空 —— 阈值缺失会让规则 ② ③ **无法判定** |

> **契约 §7 明令：阈值一律从 `system_config` 读取，严禁硬编码**。
> 本页是这两个数字的**唯一修改入口**，所以页面上要写清「改了会影响什么」。
> 只放契约里已有的两个键，**本期不预造键名**（造了联调时会对不上）。

---

### 4.6 第 6 页 · 实时识别预览（**第 2 周解禁导航，页面仍属占位**）

线框 `wireframes/preview.html` 已于第 2 周交付（任务 6.1），导航**不再置灰**。
但页面本身仍是**未就绪占位**：后端 `GET /api/frame/latest`（契约 §6.5）尚未实现，
故本页**不进第 2 周验收**，完整实现排在第 3 周。

| 区域 | 组件 | 字段 / 内容 |
|---|---|---|
| 导航 | `el-menu-item` | **第 2 周起不置灰**（`check_tokens.py` 第 [5] 项要求 6 页均无 `is-reserved`） |
| 最近一帧 | 卡片 + `el-image` | 最近一帧截图；取不到帧时进空态（**非失败态**，见 §2.1 ④） |
| 说明 | `el-alert`（info） | 「仅展示最近一帧截图（轮询刷新），不接实时视频流」——开发大纲已确认 |
| 本次识别结果 | 描述列表（KV） | 车牌 / 车型 / 桩 ID / 命中规则 / 命中时间 |
| 最近识别记录 | `el-table` | 5 列，**复用 `occupation_record` 同名列名**（见 §4.0） |
| 加载 / 空态 | `el-skeleton` / `el-empty` | 骨架规格见 §2.1；两种空态：**取不到帧** vs **未命中规则** |

> ⚠️ **线框与前端的有意差异（待吕浩确认）**：`frontend/src/router/index.ts` 里本页仍标
> `meta.reserved: true`（接口未就绪，前端继续置灰）。这是**有意为之**——线框表达的是
> 「设计侧已解禁」，前端表达的是「实现侧未就绪」。二者不对齐属预期，不需要改前端；
> 待第 3 周接口落地后由吕浩一并放开。已记入 `walkthrough.md` §9 待回签项。

---

## 5. 跨页一致性检查（交付前自查）

**v1.1 起第 1~3、6~9 项已进 `tools/check_tokens.py` 第 [5] 项自动校验**，改坏了会直接 exit 1；
走查结果与逐项证据见 `walkthrough.md`。

| # | 检查项 | 自动 | 说明 |
|---|---|---|---|
| 1 | 6 页的侧边导航顺序一致，**第 6 页不置灰** | ✅ | 逐页比对导航文案与 `CONTRACT.md` §1.1 顺序，要求恰有 1 个 `is-active`、**且 6 页均不得出现 `is-reserved`**（契约 v1.5 起第 6 页解禁） |
| 2 | 所有表格：表头 `--fill-light`、行线 `--border-light`、悬浮 `--brand-primary-bg` | ✅ | 正则校验三条 CSS 声明存在 |
| 3 | 所有车牌/桩 ID/手机号/时间：等宽字族 + `tabular-nums` | ✅ | 每页 `.mono` 使用数 ≥ 4 |
| 4 | 所有状态标记：白底上用 `-text` 档，实心块上橙/黄配深字 | ⚠️ 部分 | 对比度由第 [2] 项断言；「白底用 `-text` 档」靠 `StatusPill` 的类名约定 + 人工确认 |
| 5 | 所有违规色：严格按 `design-tokens.md` §3.3 映射，无自选色 | 👁 人工 | 语义映射表见 §3.3① ②，线框标注里逐条引用 |
| 6 | 所有间距：只取 `--space-*` 与 `--layout-*` | ✅ | 扫描 `padding/margin/gap`，出现 ≥4px 的裸 px 即失败 |
| 7 | 页面里没有裸色值 | ✅ | 逐页扫描 `#hex`（快照块除外） |
| 8 | 空态 `el-empty`、加载态 `el-skeleton` 都有 | ✅ 空态 / ✅ 样张 | 空态逐页必查；加载态规格见 **§2.1**，`preview.html` 内出可读样张（类名 `.skeleton`），由第 [6] 项断言三类齐全 |
| 9 | 表格列名与契约字段一一对应，没有自造字段 | ✅ | 逐页对照 `CONTRACT.md` **§3.5 显示列名映射表**（v1.4 起为唯一入口），越界即失败；**同一张表被多页引用时列名必须同一写法**，分叉即失败；**新增线框须先登记**（无表格的独立页走 `STANDALONE_PAGES` 豁免，见下） |

> 第 9 项是**最值得自动化**的一条：列名白名单不再硬编码在脚本里，而是**解析 `CONTRACT.md` §3.5 派生**
> （v1.4 改造，见 §7 变更记录）。想加一个自造字段，绕过校验的唯一办法是去改 `CONTRACT.md` —— 这正是契约流程想要的。
>
> **独立页豁免**：`login.html`（任务 6.6）不属后台 6 页骨架，无侧边导航、无契约表格，
> 因此登记进脚本的 `STANDALONE_PAGES` 白名单豁免列名与导航校验；**豁免项必须写明理由**，
> 否则「未登记」一律判失败（v1.5 起由警告改为**失败**，防止新增线框被静默漏检 —— `preview.html` 当初正是踩了这个坑）。
>
> **但白名单挡不住「自己写错自己」**：白名单和线框出自同一手，写错时两边一起错，比对不出来
> （2026-09-19 终检就是这么踩到的 —— 第 2 页写「车牌号」而第 4 页写「车牌」）。
> 所以额外加了 `SHARED_TABLE_PAGES` 交叉断言：同一个表被多页引用时，列名集合必须一致。

---

## 6. 素材清单（v1.1 新增）

规范见 `README.md` §2 / §3；命名与取色由 `check_tokens.py` 第 [4] 项自动校验。

### 6.1 侧边导航图标（6 个，一个页面一个）

| 页面 | 文件 |
|---|---|
| 1 车辆信息管理 | `assets/icons/icon-nav-vehicle.svg` |
| 2 违规记录查询 | `assets/icons/icon-nav-records.svg` |
| 3 充电状态展示 | `assets/icons/icon-nav-pile-status.svg` |
| 4 报警统计 | `assets/icons/icon-nav-stats.svg` |
| 5 系统参数配置 | `assets/icons/icon-nav-config.svg` |
| 6 实时识别预览（第 2 周起不置灰） | `assets/icons/icon-nav-preview.svg` |

### 6.2 违规规则图标（4 个，对应 `rule_hit`）

| 枚举 | 语义 | 文件 |
|---|---|---|
| `rule_hit = 1` | 燃油车占位 | `assets/icons/icon-rule-fuel-occupy.svg` |
| `rule_hit = 2` | 异常占位 | `assets/icons/icon-rule-abnormal-park.svg` |
| `rule_hit = 3` | 充满未移车 | `assets/icons/icon-rule-full-not-moved.svg` |
| `rule_hit = 0` | 正常充电 | `assets/icons/icon-rule-normal.svg` |

> 规则图标**自带语义**，可以直接给第 2 页表格的规则列或第 4 页图表自定义图例用；
> 上色必须走 `--state-*-text`（白底）或 `--state-*-solid`（实心块），不要给图标写死颜色。

### 6.3 界面通用图标（8 个）

| 文件 | 用于 |
|---|---|
| `icon-search.svg` | 筛选区「查询」 |
| `icon-refresh.svg` | 「刷新」（第 2 页页头） |
| `icon-plus.svg` | 「新增车辆」（第 1 页） |
| `icon-edit.svg` | 行内「编辑」 |
| `icon-delete.svg` | 行内「删除」 |
| `icon-send.svg` | 行内「发送提醒」（第 2 页） |
| `icon-reset.svg` | 「重置」（筛选区，v1.4 新增） |
| `icon-warning.svg` | 二次确认弹窗的警示图标（v1.4 新增） |

> **v1.4 起前端已全部替换**（任务 6.4）：18 个图标同步到 `frontend/src/assets/icons/`，
> 由 `AppIcon.vue` 用 **CSS `mask-image` + `currentColor`** 渲染，组件里不再引用
> `@element-plus/icons-vue`。选 `mask` 而非 `<img>` 的原因：`<img>` 是独立的替换元素，
> `currentColor` 不参与级联，图标无法跟随主题色。
>
> ⚠️ 副作用（已知并接受）：`mask` 只取形状，**不继承语义**，所以素材 SVG 里的
> `aria-label` 在 mask 模式下读不到 —— 图标的无障碍语义必须由 `AppIcon` 的 `label` prop
> 或外层按钮的 `aria-label` 提供。详见 `a11y-report.md` §2.2。

### 6.4 Logo（3 个）

| 文件 | 形态 | 用途 |
|---|---|---|
| `assets/logos/logo-full.svg` | 完整版（图形 + 文字 + 副标题） | 登录页、报告封面、答辩 PPT 首页 |
| `assets/logos/logo-mark.svg` | 图形版（品牌底色块 + 白色闪电） | 侧边栏 28×28 容器（替代当前线框里的「桩」字占位） |
| `assets/logos/logo-mono.svg` | 单色版（`currentColor`） | 深色底、水印、单色印刷 |

> Logo / 插画里的色值写成 `var(--brand-primary, #1668E3)` 形式：内联时跟随主题，
> 以 `<img>` 引入时 CSS 变量不参与级联，兜底值保证仍显示品牌色。

### 6.5 空状态插画（3 个）

| 文件 | 用于 |
|---|---|
| `assets/illustrations/empty-state-no-data.svg` | 通用「暂无数据」（表格/列表为空） |
| `assets/illustrations/empty-state-no-record.svg` | 「暂无违规记录」（第 2 页，带绿色对勾语义） |
| `assets/illustrations/empty-state-search-empty.svg` | 「筛选无结果」（第 2 页筛选滤空，v1.4 补齐） |

> 线框里的空态插画是**内联 SVG 简化版**（为了单文件可直接预览）；
> 素材目录里的是正式版，前端实现时用素材替换，尺寸按 160×120 等比缩放。
>
> **三类空态必须同时用插画 + 文案区分**（`EmptyState.vue` 的 `illustration` prop 取
> `no-data` / `no-record` / `search-empty`）：第 2 页的两种空态语义相反 ——
> 「筛选无结果」要引导**重置筛选**，「暂无违规记录」才是"真的没数据"。
> 用同一张插画只换文案，用户会不知道该点哪里。

---

## 7. 变更记录

| 版本 | 日期 | 变更 | 发起人 |
|---|---|---|---|
| **v1.4** | 2026-09-26 | **第 2 周设计交付**（任务 6.1/6.2/6.4/6.9/6.12）：① **新增 §2.1 加载态规格**（表格 8 行 / 卡片 3×2 / 图表锁定高度三类骨架，附与空态的区别、时长与超时口径）；② **新增 §3.2 ECharts 主题规范**（两套色板序列、网格与坐标轴、tooltip、图例、无数据态、**可注册的 theme 代码**、8 条待回签复核清单；前置依赖契约 C2）；③ **§4.6 第 6 页改写为「导航解禁、页面仍属占位」**，并记入「设计侧解禁 vs 前端仍 `reserved`」的有意差异（待吕浩确认）；④ §5 第 1 项断言**反转为「6 页均不得 `is-reserved`」**、第 8 项加载态改为「规格 + 样张」、第 9 项补独立页豁免与「未登记即失败」；⑤ §6.1/6.3/6.5 素材数量更新（图标 16→**18**、插画 2→**3**），并补记 `mask-image` 渲染对 `aria-label` 的影响；⑥ 依据升级为**契约 v1.5** | 吴和庆 |
| **v1.3** | 2026-09-19 | **列名单一事实源改造**：① §4.0 由「逐条列名映射表」改为**指针式说明**（原来那张表是列名的第四份副本，改一处要动四处）—— 列名唯一入口改为 `CONTRACT.md` **§3.5 显示列名映射表**，本节只留「label/prop 怎么取用」的三步法与两条边界；② 依据升级为契约 v1.4；③ §5 第 9 项对应断言的实现说明更新（白名单已由硬编码改为**解析契约 §3.5 生成**，并新增「§3.x 说明档 ↔ §3.5 一致」断言） | 吕浩 |
| **v1.2** | 2026-09-19 | **终检修正**：① 新增 **§4.0 线框列名 ↔ 契约字段映射表**（逐条给出显示标签 → 契约表.字段 → 契约说明，吕浩写 `prop` 直接照抄）；② 第 2 页筛选与列表的 `plate` 列名由「车牌号」统一为**「车牌」**（`occupation_record` 的契约说明是「车牌」，且第 4 页原本就写「车牌」，原先三处分叉）；③ §5 第 9 项补入**同表跨页列名一致性**断言，并说明「白名单挡不住自己写错自己」的原因 | 吴和庆 |
| **v1.1** | 2026-09-19 | 第 1 周设计交付：① 新增 **§3.1 第 4 页图表规格**（序列严重度顺序、分类份额改主色梯度、图元→令牌映射、三图规格、交互与空态、数据来源与契约风险）；② 补齐 §4.2–4.5 四页线框引用与硬约束，§4.1 标注空态已补；③ §5 走查清单改为「自动校验覆盖情况」表；④ 新增 §6 素材清单（16 图标 + 3 Logo + 2 插画）；⑤ 第 9 项「表格列名不越界」进 `check_tokens.py` 白名单 | 吴和庆 |
| v1.0 | 2026-09-13 | 首版。6 页组件清单、Element Plus 组件总表与逐页映射、组件规格总表、跨页一致性检查单 9 项 | 吴和庆 |
