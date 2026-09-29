/**
 * 应用入口。
 *
 * ⚠️ 样式引入顺序不可颠倒（docs/design/design-tokens.md §0）：
 *    1. tokens.css —— 设计令牌，**唯一色彩与尺寸来源**
 *    2. element-plus/dist/index.css —— 组件库样式
 *
 * tokens.css 内已覆盖 `--el-*` 变量，顺序颠倒会导致组件库默认色盖掉令牌。
 */

import { createPinia } from 'pinia'
import { createApp } from 'vue'

import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'

import '@/styles/tokens.css'
import 'element-plus/dist/index.css'
import '@/styles/global.css'

import App from '@/App.vue'
import router from '@/router'

const app = createApp(App)

// 图标：第 2 周已收口（PLAN_4WEEKS.md §3.3 任务 6.4）。
// 原第 1 周做法是在这里把 @element-plus/icons-vue 的**全部**图标注册成全局组件，
// 现已移除 —— 那会把上千个组件塞进产物，且与设计侧的官方图标集并存成两套风格。
// 业务图标一律走 `@/components/common/AppIcon.vue`（源：docs/design/assets/icons/）。
// Element Plus 组件自身内部用到的图标由它自己 import，不依赖这里的全局注册。
app.use(createPinia())
app.use(router)
app.use(ElementPlus, { locale: zhCn })

app.mount('#app')
