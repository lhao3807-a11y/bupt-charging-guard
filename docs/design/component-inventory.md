# 后台组件清单与 Element Plus 映射

> **版本** v1.1（2026-09-19 · 补 §3.1 图表规格、§6 素材清单，5 页线框全部就位）
> **负责人** 吴和庆（UI / 美术）
> **依据** `docs/CONTRACT.md` v1.2 §1.1（6 页清单）、`design-tokens.md`、`wireframes/`
> **用途** 吕浩据此实现前端；本文件只**列清单和映射**，不新增业务字段。
> **校验** `python docs/design/tools/check_tokens.py`（第 5 项会逐页核对表格列名是否越界）

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

## 4. 逐页清单

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
| 筛选 | `el-form` | 车牌号、车型、桩 ID、命中规则 `rule_hit`、提醒状态 `notify_status`、命中时间范围 |
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
| 统计卡 | `el-statistic` × 4 | 总违规数、燃油占位、异常占位、充满未移车（各自用对应状态色） |
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

### 4.6 第 6 页 · 实时识别预览（**第 1 周不做，仅预留**）

| 区域 | 组件 | 字段 / 内容 |
|---|---|---|
| 导航 | `el-menu-item` `disabled` | 置灰 + 「第 1 周预留」角标 |
| 页面 | `el-image` | 最近一帧截图，`el-skeleton` 占位 |
| 轮询 | — | 依赖预留端点 `GET /api/frame/latest`（契约 §6.5） |
| 说明 | `el-alert`（info） | 「仅展示最近一帧截图（轮询刷新），不接实时视频流」——开发大纲已确认 |

> `CONTRACT.md` §1.1 明确：本页第 1 周 Demo **不验收**。
> 线框里只做导航占位，不做页面。

---

## 5. 跨页一致性检查（交付前自查）

**v1.1 起第 1~3、6~9 项已进 `tools/check_tokens.py` 第 [5] 项自动校验**，改坏了会直接 exit 1；
走查结果与逐项证据见 `walkthrough.md`。

| # | 检查项 | 自动 | 说明 |
|---|---|---|---|
| 1 | 6 页的侧边导航顺序一致，第 6 页置灰 | ✅ | 逐页比对导航文案与 `CONTRACT.md` §1.1 顺序，并要求恰有 1 个 `is-active`、第 6 项 `is-reserved` |
| 2 | 所有表格：表头 `--fill-light`、行线 `--border-light`、悬浮 `--brand-primary-bg` | ✅ | 正则校验三条 CSS 声明存在 |
| 3 | 所有车牌/桩 ID/手机号/时间：等宽字族 + `tabular-nums` | ✅ | 每页 `.mono` 使用数 ≥ 4 |
| 4 | 所有状态标记：白底上用 `-text` 档，实心块上橙/黄配深字 | ⚠️ 部分 | 对比度由第 [2] 项断言；「白底用 `-text` 档」靠 `StatusPill` 的类名约定 + 人工确认 |
| 5 | 所有违规色：严格按 `design-tokens.md` §3.3 映射，无自选色 | 👁 人工 | 语义映射表见 §3.3① ②，线框标注里逐条引用 |
| 6 | 所有间距：只取 `--space-*` 与 `--layout-*` | ✅ | 扫描 `padding/margin/gap`，出现 ≥4px 的裸 px 即失败 |
| 7 | 页面里没有裸色值 | ✅ | 逐页扫描 `#hex`（快照块除外） |
| 8 | 空态 `el-empty`、加载态 `el-skeleton` 都有 | ✅ 空态 / — 加载 | 空态逐页必查；加载态是前端实现细节，线框不画骨架屏，第 2 周补 |
| 9 | 表格列名与契约字段一一对应，没有自造字段 | ✅ | 逐页对照契约字段白名单，越界即失败；新增页面须先登记 |

> 第 9 项是**最值得自动化**的一条：`CONTRACT_COLUMNS` 白名单写在 `check_tokens.py` 里，
> 想加一个自造字段，绕过校验的唯一办法是去改 `CONTRACT.md` —— 这正是契约流程想要的。

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
| 6 实时识别预览（第 1 周置灰） | `assets/icons/icon-nav-preview.svg` |

### 6.2 违规规则图标（4 个，对应 `rule_hit`）

| 枚举 | 语义 | 文件 |
|---|---|---|
| `rule_hit = 1` | 燃油车占位 | `assets/icons/icon-rule-fuel-occupy.svg` |
| `rule_hit = 2` | 异常占位 | `assets/icons/icon-rule-abnormal-park.svg` |
| `rule_hit = 3` | 充满未移车 | `assets/icons/icon-rule-full-not-moved.svg` |
| `rule_hit = 0` | 正常充电 | `assets/icons/icon-rule-normal.svg` |

> 规则图标**自带语义**，可以直接给第 2 页表格的规则列或第 4 页图表自定义图例用；
> 上色必须走 `--state-*-text`（白底）或 `--state-*-solid`（实心块），不要给图标写死颜色。

### 6.3 界面通用图标（6 个）

| 文件 | 用于 |
|---|---|
| `icon-search.svg` | 筛选区「查询」 |
| `icon-refresh.svg` | 「刷新」（第 2 页页头） |
| `icon-plus.svg` | 「新增车辆」（第 1 页） |
| `icon-edit.svg` | 行内「编辑」 |
| `icon-delete.svg` | 行内「删除」 |
| `icon-send.svg` | 行内「发送提醒」（第 2 页） |

### 6.4 Logo（3 个）

| 文件 | 形态 | 用途 |
|---|---|---|
| `assets/logos/logo-full.svg` | 完整版（图形 + 文字 + 副标题） | 登录页、报告封面、答辩 PPT 首页 |
| `assets/logos/logo-mark.svg` | 图形版（品牌底色块 + 白色闪电） | 侧边栏 28×28 容器（替代当前线框里的「桩」字占位） |
| `assets/logos/logo-mono.svg` | 单色版（`currentColor`） | 深色底、水印、单色印刷 |

> Logo / 插画里的色值写成 `var(--brand-primary, #1668E3)` 形式：内联时跟随主题，
> 以 `<img>` 引入时 CSS 变量不参与级联，兜底值保证仍显示品牌色。

### 6.5 空状态插画（2 个）

| 文件 | 用于 |
|---|---|
| `assets/illustrations/empty-state-no-data.svg` | 通用「暂无数据」（表格/列表为空） |
| `assets/illustrations/empty-state-no-record.svg` | 「暂无违规记录」（第 2 页，带绿色对勾语义） |

> 线框里的空态插画是**内联 SVG 简化版**（为了单文件可直接预览）；
> 素材目录里的是正式版，前端实现时用素材替换，尺寸按 160×120 等比缩放。
> `assets/illustrations/empty-state-search-empty.svg`（筛选无结果）留待第 2 周补，
> 本期线框用同一插画 + 不同文案区分。

---

## 7. 变更记录

| 版本 | 日期 | 变更 | 发起人 |
|---|---|---|---|
| **v1.1** | 2026-09-19 | 第 1 周设计交付：① 新增 **§3.1 第 4 页图表规格**（序列严重度顺序、分类份额改主色梯度、图元→令牌映射、三图规格、交互与空态、数据来源与契约风险）；② 补齐 §4.2–4.5 四页线框引用与硬约束，§4.1 标注空态已补；③ §5 走查清单改为「自动校验覆盖情况」表；④ 新增 §6 素材清单（16 图标 + 3 Logo + 2 插画）；⑤ 第 9 项「表格列名不越界」进 `check_tokens.py` 白名单 | 吴和庆 |
| v1.0 | 2026-09-13 | 首版。6 页组件清单、Element Plus 组件总表与逐页映射、组件规格总表、跨页一致性检查单 9 项 | 吴和庆 |
