# 后台组件清单与 Element Plus 映射

> **版本** v1.0（2026-09-13）
> **负责人** 吴和庆（UI / 美术）
> **依据** `docs/CONTRACT.md` v1.1 §1.1（6 页清单）、`design-tokens.md`、`wireframes/vehicle-management.html`
> **用途** 吕浩据此实现前端；本文件只**列清单和映射**，不新增业务字段。

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

---

## 4. 逐页清单

### 4.1 第 1 页 · 车辆信息管理 —— 风格样板，已完成线框

**线框**：`wireframes/vehicle-management.html`（后续 5 页照此对齐）

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

| 区域 | 组件 | 字段 / 内容 |
|---|---|---|
| 页头 | `PageHeader` | 标题 + 说明（数据来自 `occupation_record`） |
| 筛选 | `el-form` | 车牌号、车型、桩 ID、命中规则 `rule_hit`、提醒状态 `notify_status`、命中时间范围 |
| 表格 | `el-table` | 列 = `ViolationRecord`：ID / 车牌 / 车型 / 桩 ID / 命中规则 / 命中时间 / 提醒状态 / 提醒时间 / 操作 |
| 状态渲染 | `StatusPill` | `rule_hit` 按 `design-tokens.md` §3.3① 映射 红/橙/黄/绿；`notify_status` 按 ② 映射 黄/绿/红 |
| 操作 | `el-button` | 「发送提醒」调 `POST /api/notify`，成功后 `el-message` 提示并刷新该行 |
| 分页 | `el-pagination` | 用响应里的 `total`（契约 §6.4） |
| 数据源 | `GET /api/records?page=&size=` | |

> **验收清单**（契约 §11）要求「后台违规记录查询页面能看到该条记录」，
> 所以这一页是第 1 周**必须上线**的页面，优先级高于其余 4 页。

---

### 4.3 第 3 页 · 充电状态展示

| 区域 | 组件 | 字段 / 内容 |
|---|---|---|
| 页头 | `PageHeader` | |
| 概览 | `el-statistic` × 3 | 空闲 / 充电中 / 已充满 的桩数量 |
| 卡片网格 | `el-card` + `StatusPill` | 每桩一卡：桩 ID（等宽）、状态胶囊、绑定车牌（等宽）、开始/结束时间 |
| 表格视图 | `el-table` | 列 = `charging_pile` 全字段，供「列表/卡片」切换 |
| 状态渲染 | `StatusPill` | `空闲` 中性灰 / `充电中` 主色蓝 / `已充满` 橙（§3.3③） |
| 说明 | `el-alert`（info） | 「充电状态为模拟数据，预留 OCPP 适配层」——**演示时避免被误解为真实接口** |

> 开发大纲 M7 只要求「充电状态展示」，卡片式比表格更适合答辩讲解，
> 但表格便于核对字段，故两者都给，用 `el-radio-button` 切换。

---

### 4.4 第 4 页 · 报警统计

| 区域 | 组件 | 字段 / 内容 |
|---|---|---|
| 页头 | `PageHeader` | |
| 统计卡 | `el-statistic` × 4 | 总违规数、燃油占位、异常占位、充满未移车（各自用对应状态色） |
| 维度切换 | `el-radio-group` | 按 `rule_hit` / 按天 / 按桩 |
| 图表 | **ECharts** | 柱状图（按 `rule_hit` 分布）、折线图（按天趋势）、饼图（按桩占比） |
| 图例色 | ECharts 配色 | 见 §3 末尾：红 → 橙 → 黄 → 绿 严重度梯度 |
| 表格 | `el-table` | 明细下钻（点图表柱子后过滤） |

> 数据源：`occupation_record` 按 `rule_hit` / 时间聚合。
> 契约未定义专门统计接口，若前端聚合不便，**需向吕浩提新增接口**（改契约流程：先改 `CONTRACT.md` 再升版本）。

---

### 4.5 第 5 页 · 系统参数配置

| 区域 | 组件 | 字段 / 内容 |
|---|---|---|
| 页头 | `PageHeader` | |
| 参数表 | `el-table` + 行内编辑 | 列 = `system_config` 全字段：参数键 `key` / 参数值 `value` / 说明 `note` |
| 阈值编辑 | `el-input-number` | `full_timeout_min`（充满超时阈值，默认 30）、`abnormal_park_min`（异常占位久停阈值，默认 30） |
| 单位 | `el-input` append | 「分钟」 |
| 保存 | `el-button`（主） | |
| 风险提示 | `el-alert`（warning） | 「修改阈值将直接影响规则引擎判定结果，建议在无正在进行的演示时调整」 |
| 只读键 | `el-tooltip` | 非阈值的 `key` 说明其用途 |

> **契约 §7 明令：阈值一律从 `system_config` 读取，严禁硬编码**。
> 本页是这三个数字的**唯一修改入口**，所以页面上要写清「改了会影响什么」。

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

- [ ] 6 页的侧边导航顺序一致，第 6 页置灰
- [ ] 所有表格：表头 `--fill-light`、行线 `--border-light`、悬浮 `--brand-primary-bg`
- [ ] 所有车牌/桩 ID/手机号/时间：等宽字族 + `tabular-nums`
- [ ] 所有状态标记：白底上用 `-text` 档，实心块上橙/黄配深字
- [ ] 所有违规色：严格按 `design-tokens.md` §3.3 映射，无自选色
- [ ] 所有间距：只取 `--space-*` 与 `--layout-*`
- [ ] 页面里没有裸色值（跑 `tools/check_tokens.py` 会自动查）
- [ ] 空态 `el-empty`、加载态 `el-skeleton` 都有
- [ ] 表格列名与契约字段一一对应，没有自造字段
