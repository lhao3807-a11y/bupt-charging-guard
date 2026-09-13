# 设计系统基线 · Design Tokens

> **版本** v1.0（2026-09-13）
> **负责人** 吴和庆（UI / 美术）
> **依据** `docs/CONTRACT.md` v1.1 §1.1「后台页面清单（6 页）」、`docs/design/wireframes/vehicle-management.html`（风格样板）
> **适用范围** `frontend/**` 全部页面。本文档与 `tokens.css` 是**唯一色彩与尺寸来源**。

---

## 0. 文件关系与使用方式

| 文件 | 作用 | 谁改 |
|---|---|---|
| `design-tokens.md` | 本文件。规则的**说明与依据**，含对比度实测值 | 吴和庆 |
| `tokens.css` | 令牌的**代码实现**，可直接 import | 吴和庆 |
| `wireframes/vehicle-management.html` | 第 1 页线框 + **风格样板**，后续 5 页照此对齐 | 吴和庆 |
| `component-inventory.md` | 6 页的组件清单与 Element Plus 映射 | 吴和庆 |
| `tools/check_tokens.py` | 自动化校验（令牌完整性、对比度、裸色值、快照一致、素材命名） | 吴和庆 |

**引入方式**（`frontend/src/main.ts`，顺序不能颠倒）：

```ts
import '@/styles/tokens.css'          // 本设计令牌，先引入
import 'element-plus/dist/index.css'  // Element Plus，后引入
```

> `tokens.css` 里已经覆盖了 `--el-*` 变量，所以引入顺序上是「令牌先、组件库后」，
> 但两者作用在同一组变量上、值一致，先后都不会出错；写成上面这样是为了让令牌的
> 落点更清晰：**任何颜色都要能从 `tokens.css` 查到出处**。

---

## 1. 四条设计原则

1. **严重度一眼可辨**。这是监管类后台，用户扫一眼就要分出「燃油占位 / 异常占位 / 充满未移车」。
   所以违规色按严重度排成 红 → 橙 → 黄 → 绿 的梯度，而不是随手取四个颜色。
2. **可读性优先于装饰**。后台的主体是表格和数字，不用渐变、不用玻璃拟态、不用大面积彩底。
3. **令牌唯一**。页面里不出现裸色值（`#xxxxxx`），一律 `var(--token)`。
   漏改一个色就全局不一致，是把设计系统做废最快的方式。
4. **无障碍达标**。白底上的正文与图形**实测 ≥ 4.5:1**（WCAG 2.1 AA）。
   第 3.2 节所有数字都是脚本跑出来的，不是估的。

---

## 2. 品牌主色

取「电」的青蓝 `#1668E3`。不选绿色做主色的原因见 §3.3 末尾——绿色要留给「正常」状态，两者一撞就分不清「品牌」和「状态」。

| 令牌 | 值 | 用途 |
|---|---|---|
| `--brand-primary` | `#1668E3` | 主按钮底、链接、选中态、进行中状态、图表主色 |
| `--brand-primary-hover` | `#145ECC` | 主按钮悬浮 |
| `--brand-primary-active` | `#1253B6` | 主按钮按下、`--el-color-primary-dark-2` |
| `--brand-primary-bg` | `#F0F6FF` | 浅底：选中行、主色标签底、聚焦光晕 |
| `--brand-primary-border` | `#BFDBFF` | 浅底上的描边 |

**Element Plus 主色梯度**（已按 `mix(#FFFFFF, 主色, i*10%)` 烘焙成十六进制写进 `tokens.css`）：

| 令牌 | 值 |
|---|---|
| `--brand-primary-light-3` | `#5C95EB` |
| `--brand-primary-light-5` | `#8AB4F1` |
| `--brand-primary-light-7` | `#B9D2F7` |
| `--brand-primary-light-8` | `#D0E1F9` |
| `--brand-primary-light-9` | `#E8F0FC` |

主色本身在三种场景都过 AA：白字在主色底 **5.09**、主色字在白底 **5.09**、主色字在浅底 **4.69**。
一个 `--brand-primary` 同时承担「按钮底」和「链接字」，不必拆两个色。

---

## 3. 语义状态色

### 3.1 四档模型与使用边界

每种状态固定四档。**这四档不是深浅变体，而是四个用途，混用是最常见的出错点**：

| 档位 | 命名 | 允许用在哪 | 禁止用在哪 |
|---|---|---|---|
| `-solid` | 实心填充 | 按钮底、标签实心底、进度条、色块、`--el-color-*` 主色 | ❌ 白底上的文字、图标、圆点、色条 |
| `-text` | 白底文字与图形 | 白底上的**一切**可见文字、图标、圆点、色条、描边 | ❌ 大面积填充（太重） |
| `-bg` | 浅底 | 标签底、提示条底、图表区块底 | ❌ 承载正文 |
| `-border` | 描边 | 浅底标签的边框、卡片强调边 | ❌ 当文字色 |

> **一句话规则**：白底上看得见的东西，一律用 `-text` 档；
> 鲜艳的 `-solid` 档只允许出现在「它自己就是底色」的地方。
>
> 这条规则不是洁癖，是因为 `--state-caution-solid`（2.38）和 `--state-warning-solid`（1.90）
> 在白底上根本达不到 3:1，拿来当白底图形就是不可见。校验脚本对这两条会给出警告。

### 3.2 对比度实测表（WCAG 2.1 AA，阈值 4.5:1）

数据来源：`python docs/design/tools/check_tokens.py`，脚本每次跑都会重新计算并断言。

| 状态 | `-solid` | `-text` | `-bg` | `-border` | text/白底 | text/自身浅底 | solid/白底 |
|---|---|---|---|---|---|---|---|
| 违规红 danger | `#CF1322` | `#A8071A` | `#FFF1F0` | `#FFCCC7` | **7.75** ✅ | **7.04** ✅ | **5.57** ✅ |
| 异常橙 caution | `#FA8C16` | `#C4320A` | `#FFF7E6` | `#FFD591` | **5.52** ✅ | **5.17** ✅ | 2.38 ⚠️ 仅填充 |
| 超时黄 warning | `#FAAD14` | `#946200` | `#FFFBE6` | `#FFE58F` | **5.24** ✅ | **5.04** ✅ | 1.90 ⚠️ 仅填充 |
| 正常绿 success | `#0E7A2E` | `#0E7A2E` | `#F0FBF2` | `#B7EB8F` | **5.47** ✅ | **5.15** ✅ | **5.47** ✅ |
| 中性 info | `#8A919F` | `#4E5969` | `#F2F3F5` | `#D9D9D9` | **7.10** ✅ | **6.40** ✅ | 3.17 ✅ |

`-solid` 档上放文字时，白字与深字取更优的那个：

| 状态 | `-solid` | 最优方案 | 对比度 |
|---|---|---|---|
| danger | `#CF1322` | 白字 | 5.57 |
| caution | `#FA8C16` | 深字 `--text-primary` | 6.63 |
| warning | `#FAAD14` | 深字 `--text-primary` | 8.31 |
| success | `#0E7A2E` | 白字 | 5.47 |
| info | `#8A919F` | 深字 `--text-primary` | 4.98 |

> 注意 caution 与 warning 的实心块**必须配深字**——配白字分别只有 2.38 / 1.90，直接不可读。

### 3.3 业务语义映射

后端枚举 → 视觉的对照表。**吕浩写前端时直接查这张表，不要临场发挥**。

**① 违规类型** `occupation_record.rule_hit`（第 2、4 页）

| rule_hit | 语义 | 令牌前缀 | 色 | 严重度 |
|---|---|---|---|---|
| `1` | 燃油车占位（蓝牌占充电位） | `--state-danger-*` | 红 | 最高 |
| `2` | 异常占位（新能源未充电且久停） | `--state-caution-*` | 橙 | 中 |
| `3` | 充满未移车（充满超时未离场） | `--state-warning-*` | 黄 | 低 |
| `0` | 正常充电（不提醒） | `--state-success-*` | 绿 | — |

**② 提醒状态** `occupation_record.notify_status`（第 2 页）

| notify_status | 令牌前缀 | 色 |
|---|---|---|
| `未提醒` | `--state-warning-*` | 黄（待处理） |
| `已提醒` | `--state-success-*` | 绿 |
| `失败` | `--state-danger-*` | 红 |

**③ 充电桩状态** `charging_pile.status`（第 3 页）

| status | 令牌 | 色 | 理由 |
|---|---|---|---|
| `空闲` | `--state-info-*` | 中性灰 | 无状态 |
| `充电中` | `--brand-primary` + `--brand-primary-bg` | 主色蓝 | 「进行中」用品牌色，与违规色系彻底分开 |
| `已充满` | `--state-caution-*` | 橙 | 需要关注（是「充满未移车」的前置状态） |

**④ 车型** `vehicle.vtype`（第 1 页）

| vtype | 令牌 | 色 | 理由 |
|---|---|---|---|
| `新能源` | `--plate-new-energy-*` | 绿牌绿 `#0E7A2E` | **与真实车牌底色一致** |
| `燃油` | `--plate-fuel-*` | 蓝牌蓝 `#1D4FD8` | **与真实车牌底色一致** |

> 车型标签取车牌底色，是为了让「后台看到的」和「现场拍的」一眼对上，
> 减少演示时解释成本。新能源绿与「正常绿」同色系，但两者出现在不同列、
> 不同语义，同一屏内不会造成误读。

**⑤ 按钮**

| 场景 | 令牌 |
|---|---|
| 主操作（查询、新增、确定） | `--brand-primary` 底 + `--text-inverse` 字（5.09 ✅） |
| 次操作（重置、取消、批量导入） | 白底 + `--border-strong` 描边 + `--text-primary` 字 |
| 行内编辑（文字按钮） | `--brand-primary`（5.09 ✅） |
| 行内删除（文字按钮） | `--state-danger-text`（7.75 ✅），**不用 `-solid`**，实心红太抢眼 |

### 3.4 为什么比第 0 天文档多了一档橙

第 0 天开发文档 §5.3.2 只列了「违规红 / 正常绿 / 警告黄」三色。但第 2 页「违规记录查询」和第 4 页「报警统计」需要**同时区分三种违规类型**，三色不够用，因此补一档橙 `--state-caution-*`。

- 这是**纯视觉增补**：不改 `CONTRACT.md`，不动任何字段、接口、枚举。
- 颜色只落在设计令牌层，吕浩按 §3.3 的映射表取值即可。
- 若三人评审后决定不要橙色，可以在评审时直接砍掉这一档，代价是三种违规类型退化为「红/黄」两色。

---

## 4. 中性色

| 令牌 | 值 | 对比度（白底 / 页面底 `#F7F8FA` / 浅底 `#F2F3F5`） | 用途 |
|---|---|---|---|
| `--text-primary` | `#1F2329` | 15.78 / 14.85 / — | 标题、表格主字段、正文 |
| `--text-secondary` | `#4E5969` | 7.10 / 7.10 / 6.40 | 次要正文、表格副字段、表头 |
| `--text-tertiary` | `#64707D` | 5.05 / 4.76 / 4.55 ✅ | 说明、单位、表单提示 |
| `--text-disabled` | `#C9CDD4` | 1.59（**WCAG 1.4.3 豁免**） | 仅禁用态；不得承载有效信息 |
| `--text-inverse` | `#FFFFFF` | — | 深底上的文字 |
| `--border-base` | `#E5E6EB` | — | 表格线、分割线、输入框描边 |
| `--border-strong` | `#C9CDD4` | — | 需要强调的描边、次按钮边线 |
| `--border-light` | `#F2F3F5` | — | 表格行线、弹窗内分隔 |
| `--fill-light` | `#F2F3F5` | — | 表头底、斑马纹、禁用底 |
| `--bg-page` | `#F7F8FA` | — | 页面底色 |
| `--bg-container` | `#FFFFFF` | — | 卡片 / 表格 / 弹窗底 |
| `--bg-mask` | `rgba(31,35,41,.5)` | — | 弹窗遮罩 |

> `--text-tertiary` 从常见的 `#86909C`（白底仅 3.24）加深到 `#64707D`，是为了让
> 「单位」「表单提示」这类真实信息也能过 AA。禁用态则按 WCAG 1.4.3 明确豁免，
> 保持弱化观感——**两者不要互相替代**。

---

## 5. 字体与排版

**字族**

| 令牌 | 值 | 用途 |
|---|---|---|
| `--font-family-base` | `-apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", "Helvetica Neue", Arial, sans-serif` | 全部界面文字 |
| `--font-family-mono` | `"SF Mono", "JetBrains Mono", Consolas, "Courier New", monospace` | **车牌号、桩 ID、手机号、时间戳** |

车牌用等宽是有实际原因的：`京AD12345` 这类定长串在表格里要竖直对齐，且等宽字形能避免 `0/O`、`1/l` 误读。
配合 `--font-variant-numeric: tabular-nums` 让数字等宽，翻页时列宽不跳动。

**字号阶梯**

| 令牌 | 值 | 用途 |
|---|---|---|
| `--font-size-xs` | `12px` | 标签、角标、胶囊、图表刻度 |
| `--font-size-sm` | `13px` | 表格辅助列、表头、表单提示 |
| `--font-size-base` | `14px` | **正文与表格主字段（基准）** |
| `--font-size-md` | `16px` | 卡片标题、弹窗标题 |
| `--font-size-lg` | `20px` | 页面标题 |
| `--font-size-xl` | `24px` | 统计卡大数（第 4 页） |
| `--font-size-2xl` | `30px` | 大屏/主指标（第 4 页可选） |

**字重与行高**

| 令牌 | 值 | 用途 |
|---|---|---|
| `--font-weight-regular` | `400` | 正文、表格单元格 |
| `--font-weight-medium` | `500` | 表头、当前导航项、卡片标题、车牌号 |
| `--font-weight-semibold` | `600` | 页面标题、统计大数 |
| `--line-height-tight` | `1.3` | 标题 |
| `--line-height-base` | `1.5714` | 正文（14px → 22px） |
| `--line-height-relaxed` | `1.7` | 长段说明、帮助文案 |

---

## 6. 圆角

| 令牌 | 值 | 用途 |
|---|---|---|
| `--radius-xs` | `2px` | 标签、小角标、导航序号块 |
| `--radius-sm` | `4px` | **默认**：按钮、输入框、下拉、聚焦光晕 |
| `--radius-md` | `6px` | 卡片、筛选区、表格容器 |
| `--radius-lg` | `8px` | 弹窗、抽屉 |
| `--radius-xl` | `12px` | 统计卡、特色模块 |
| `--radius-pill` | `999px` | 状态胶囊、头像、圆点 |

---

## 7. 间距

4px 栅格，**只允许取下列值**，不写 `13px`、`18px` 这种随手数。

| 令牌 | 值 | 典型用途 |
|---|---|---|
| `--space-1` | `4px` | 图标与文字间距、标签内左右 |
| `--space-2` | `8px` | 按钮组间距、表单项内间距 |
| `--space-3` | `12px` | 表格单元格上下 padding、表单行间距 |
| `--space-4` | `16px` | 卡片内边距、表格单元格左右 padding、卡片间距 |
| `--space-5` | `20px` | 弹窗主体内边距 |
| `--space-6` | `24px` | 区块间距 |
| `--space-8` | `32px` | 大区块间距 |
| `--space-10` | `40px` | 内容区底部留白 |
| `--space-12` | `48px` | 遮罩区留白、空状态上下留白 |

**常用组合**（直接抄，不必再想）

| 组合 | 值 |
|---|---|
| 页面左右留白 | `--layout-gutter`（24px） |
| 卡片内边距 | `--space-4`（16px） |
| 卡片之间 | `--layout-card-gap`（16px） |
| 页头与首个卡片之间 | `--space-4`（16px） |
| 表格单元格 | `--space-3`（上下）/ `--space-4`（左右） |

---

## 8. 阴影

| 令牌 | 值 | 用途 |
|---|---|---|
| `--shadow-sm` | `0 1px 2px rgba(31,35,41,.06)` | 静态卡片（默认） |
| `--shadow-md` | `0 2px 8px rgba(31,35,41,.08)` | 卡片悬浮、下拉面板 |
| `--shadow-lg` | `0 6px 16px rgba(31,35,41,.12)` | 弹窗、抽屉、`--el-box-shadow` |

阴影颜色统一用 `--text-primary` 的同色系 `rgba(31,35,41,·)`，不用纯黑，避免发灰。

---

## 9. 布局骨架

| 令牌 | 值 | 说明 |
|---|---|---|
| `--layout-sidebar-width` | `220px` | 侧边导航展开宽 |
| `--layout-sidebar-collapsed-width` | `64px` | 收起宽（第 1 周可不做收起） |
| `--layout-header-height` | `56px` | 顶栏高，同时用于侧边栏 logo 区高 |
| `--layout-gutter` | `24px` | 页面左右留白 |
| `--layout-max-width` | `1440px` | 内容区最大宽；设计基准 1440，最小支持 1280 |
| `--layout-card-gap` | `16px` | 卡片纵向间距 |

侧边导航顺序 = `CONTRACT.md` §1.1 的 6 页顺序：

1. 车辆信息管理
2. 违规记录查询
3. 充电状态展示
4. 报警统计
5. 系统参数配置
6. 实时识别预览（第 1 周**置灰占位**，依赖 §6.5 预留端点 `GET /api/frame/latest`）

`z-index` 分层：`--z-dropdown` 1000 / `--z-sticky` 1010 / `--z-modal` 2000 / `--z-message` 3000。

---

## 10. Element Plus 变量映射

`tokens.css` 末尾已把语义色接进 Element Plus 变量，组件库不用逐组件改样式。关键映射：

| Element Plus 变量 | 映射到 |
|---|---|
| `--el-color-primary` | `--brand-primary` |
| `--el-color-primary-light-3/5/7/8/9` | `--brand-primary-light-*`（已烘焙） |
| `--el-color-primary-dark-2` | `--brand-primary-active` |
| `--el-color-success` / `-warning` / `-danger` / `-error` | `--state-success-solid` / `-warning-solid` / `-danger-solid` |
| `--el-color-success-light-9` 等浅档 | 对应 `--state-*-bg` |
| `--el-text-color-primary` | `--text-primary` |
| `--el-text-color-regular` | `--text-secondary` |
| `--el-text-color-secondary` / `-placeholder` | `--text-tertiary` |
| `--el-border-color` / `-light` | `--border-base` |
| `--el-fill-color` / `-light` | `--fill-light` |
| `--el-bg-color` / `-page` | `--bg-container` / `--bg-page` |
| `--el-font-family` / `--el-font-size-base` | `--font-family-base` / `--font-size-base` |
| `--el-border-radius-base` | `--radius-sm` |
| `--el-box-shadow` / `-light` / `-lighter` | `--shadow-lg` / `-md` / `-sm` |

**关于 `color-mix()`**：语义色的 `light-3/5/7/8/9` 与 `dark-2` 用 `color-mix()` 现算，等价于 SCSS
`mix($white, $color, i*10%)` / `mix($black, $color, 20%)`（都是 sRGB 通道直混，结果一致）。

- 现代浏览器（Chrome 111+ / Safari 16.2+ / Firefox 113+）直接可用。
- 若答辩机器浏览器过旧，按同一公式**预先烘焙成十六进制**再覆盖即可，公式：
  `light-i = round(白色 × i/10 + 色值 × (1 - i/10))`，逐通道取整。
- 主色梯度已经按这个公式烘焙好了（§2 表），可以直接照抄那 5 个值当模板。

---

## 11. 使用规则（Do / Don't）

| ✅ Do | ❌ Don't |
|---|---|
| 颜色一律 `var(--token)` | 写 `#1668E3`、`rgb(...)` 等裸色值 |
| 白底文字/图形用 `-text` 档 | 用 `-solid` 档在白底上画圆点、写文字 |
| 橙/黄实心块配 `--text-primary` 深字 | 橙/黄实心块配白字（不可读） |
| 间距取 `--space-*` | 写 `13px`、`18px`、`22px` |
| 车牌/桩 ID/时间用 `--font-family-mono` | 用默认字族（列会跳） |
| 违规严重度按 §3.3 映射表取色 | 自己挑「看着好看」的红 |
| 新增颜色先加进 `tokens.css` 并跑校验 | 在页面里临时定义一个色 |

---

## 12. 校验与交付流程

```bash
# 仓库根目录执行
python docs/design/tools/check_tokens.py
```

脚本会校验 5 件事，任一失败即退出码 1：

1. `tokens.css` 可解析、无重复令牌名、91 个必需令牌齐全、颜色取值合法
2. WCAG 对比度：状态色 `-text` 档在白底与自身浅底、文字/标签配对、实心块上的文字
3. 线框内联的 tokens 快照与 `tokens.css` **逐条一致**（防漂移）
4. 线框不出现裸色值，且引用的每个 `var(--x)` 都有定义
5. `assets/` 下素材文件名符合 kebab-case

> 第 3 条是本设计系统能长期不烂的关键：线框为了能在 `file://` 下独立渲染，
> 内联了一份 tokens 快照。快照与 `tokens.css` 一旦不一致，校验就会失败并指出
> 是哪个令牌漂了，逼着改色的人回来同步。

**交付约定**（`AGENTS.md` + `CONTRACT.md` §9）：每完成一步提交一次 commit，信息用
`design: 简述`；交付前校验脚本必须全绿。

---

## 13. 变更记录

| 版本 | 日期 | 变更 | 发起人 |
|---|---|---|---|
| v1.0 | 2026-09-13 | 首版。落地设计系统基线：品牌主色 + 5 档梯度、5 组语义状态色（四档模型）、车型车牌色、中性色、字体字号阶梯、圆角、4px 间距、阴影、布局骨架、Element Plus 变量映射；附 `tokens.css`、第 1 页线框、组件清单与校验脚本。**比第 0 天文档多一档橙**（`--state-caution-*`，理由见 §3.4，纯视觉增补、不改契约） | 吴和庆 |
