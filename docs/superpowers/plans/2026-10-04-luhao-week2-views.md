# 吕浩第二周三页前端实施计划

目标：完成 4.2–4.4 的界面和交互，后端及 C1–C3 契约由汤瑾睿交付。
范围已由吕浩于 2026-10-04 确认：只做前端与集成。沿用吴和庆线框，不新增接口契约。

## 设计与边界

Vue 页面通过可注入的前端数据源调用读取与保存函数。它是前端领域接口，**不是 HTTP 响应结构**；
正式契约发布后，由 API 适配器转换服务端响应。当前应用不注册数据源，不发送未定义 API 请求，
显示「待接入」；测试注入受控数据源以验证真实组件和异步交互，不在产品中放演示假数据。

桩页使用已有 ChargingPile 字段，显示三类计数、状态筛选和卡片/表格切换；加载、无数据、失败、
未接入分别展示。统计页按前端领域模型生成柱/折线/环形图，使用 ECharts 按需组件和 autoresize，
颜色读取 CSS 令牌，配套可读统计文本。参数页使用已有 SystemConfig 字段，只有两个已知阈值可编辑；
正整数校验、撤销、差异确认、失败保留输入、成功重读，未连接时无默认值且禁止保存。

## 顺序与验证

1. 新增 `src/data/week2.ts`、`src/composables/useAsyncSource.ts` 及其测试：请求乱序、失败、空数组、
   未连接不调用、卸载后结果失效；测试先失败，再实现。
2. 实现 `PilesView.vue`，三类状态使用已有 `pileStatusTokens`，全字段表格和卡片同源；
   组件测试注入桩数据并触发视图切换和筛选，验证 unavailable 不显示假计数。
3. 新增 `charts/week2.ts` 与 `StatisticsView.vue`。图表配置测试先验证配色、规则顺序、
   三类序列和无数据；组件验证请求天数、空态和数据源缺失。
4. 新增 `composables/useConfigEditor.ts` 及 `ConfigView.vue`。回归覆盖缺失阈值、非整数、
   取消确认、重复保存、保存失败保留草稿、成功重读与重读失败提示；只编辑既有键。
5. 每项完成运行相关测试、TypeScript、ESLint，创建对应 commit。
6. 集成：全部前端测试、令牌同步、生产构建、设计两套检查与打靶；浏览器核验三条路由的
   待接入状态及既有车辆/记录页。实际 HTTP 仍只验已有端点，不能将页面 HTML 200 算作业务联调。
7. 更新进度及数据源接入说明，区分「前端完成」和「端到端待验证」，提交最终验证记录。

```ts
// 后续契约确认后唯一的接入位置示意；本次不注册生产数据源。
// app.provide(WEEK2_DATA_SOURCE, confirmedApiAdapter)
// adapter.loadPiles(status) -> ChargingPile[]
// adapter.loadStatistics(days) -> 前端统计领域模型
// adapter.loadConfig() -> SystemConfig[]
// adapter.saveConfig(changes) -> Promise<void>，HTTP 请求结构由正式 C3 决定
```

验证命令（frontend 下）：`node node_modules/vitest/vitest.mjs run`、
`node node_modules/vue-tsc/bin/vue-tsc.js --noEmit`、
`node node_modules/eslint/bin/eslint.js . --ext .ts,.vue --max-warnings 0`、
`node scripts/copy-tokens.mjs`、`node node_modules/vite/bin/vite.js build`。
预期均 exit 0；构建现有大包提示记录为后续优化。
