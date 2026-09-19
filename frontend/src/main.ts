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
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

import '@/styles/tokens.css'
import 'element-plus/dist/index.css'
import '@/styles/global.css'

import App from '@/App.vue'
import router from '@/router'

const app = createApp(App)

// 图标：第 1 周允许全用 @element-plus/icons-vue（docs/design/README.md §4 已明确允许）
for (const [name, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(name, component)
}

app.use(createPinia())
app.use(router)
app.use(ElementPlus, { locale: zhCn })

app.mount('#app')
