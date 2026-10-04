<script setup lang="ts">
/**
 * AppIcon —— 官方图标集统一入口（docs/design/assets/icons/，共 18 个）。
 *
 * 为什么需要它：第 1 周允许前端全用 `@element-plus/icons-vue` 临时替代
 * （docs/design/README.md §4），第 2 周收口（`PLAN_4WEEKS.md` §3.3 任务 6.4）。
 *
 * 实现要点（两个坑都踩过，别再改回去）：
 *  1. **不用 `v-html` 内联 SVG**：`vue/no-v-html` 在 `plugin:vue/vue3-recommended`
 *     里是 warn，而本仓库 lint 带 `--max-warnings 0`，用了一律构建失败。
 *  2. **用 CSS mask 而不是 `<img>`**：`<img src="x.svg">` 会把 SVG 隔离成独立文档，
 *     文档内的 `currentColor` 取不到父级颜色，图标就永远是黑色；mask 方案下
 *     底色来自 `background-color: currentColor`，**跟随文字颜色**，这正是
 *     `README.md` §2.2 要求图标只能写 `currentColor` 的原因。
 *
 * 用法：`<AppIcon name="icon-search" :size="16" />`（name 不带 `.svg`）。
 */
import { computed } from 'vue'

// 原样收集全部图标 URL。用 glob 而不是逐个 import：18 个图标逐个写一遍，
// 以后加图标必然有人忘记同步这一处。
const modules = import.meta.glob('../../assets/icons/*.svg', {
  query: '?url',
  import: 'default',
  eager: true,
}) as Record<string, string>

const ICONS: Record<string, string> = {}
for (const [path, url] of Object.entries(modules)) {
  const name = path.split('/').pop()?.replace(/\.svg$/, '') ?? ''
  if (name) ICONS[name] = url
}

const props = withDefaults(
  defineProps<{
    /** 图标名，对应 `src/assets/icons/<name>.svg`（不含扩展名） */
    name: string
    /** 边长；数字按 px，字符串原样透传（默认 1em，跟随字号） */
    size?: string | number
    /** 无障碍标签。给了就是「有意思的图标」，没给就按装饰性图标处理 */
    label?: string
  }>(),
  // label 必须显式给默认值：`vue/require-default-prop` 在 vue3-recommended 里是
  // warning，而本仓库 lint 带 `--max-warnings 0`，不给会直接构建失败。
  { size: '1em', label: undefined },
)

const iconStyle = computed<Record<string, string>>(() => {
  const length = typeof props.size === 'number' ? `${props.size}px` : props.size
  return {
    width: length,
    height: length,
    '--icon-url': `url("${ICONS[props.name] ?? ''}")`,
  }
})
</script>

<template>
  <span
    class="app-icon"
    :style="iconStyle"
    :role="label ? 'img' : undefined"
    :aria-label="label"
    :aria-hidden="label ? undefined : 'true'"
  />
</template>

<style scoped>
.app-icon {
  display: inline-block;
  flex-shrink: 0;
  vertical-align: -0.125em;
  /* 颜色继承自父级：图标文件里只有 currentColor，没有写死色值 */
  background-color: currentColor;
  -webkit-mask-image: var(--icon-url);
  mask-image: var(--icon-url);
  -webkit-mask-repeat: no-repeat;
  mask-repeat: no-repeat;
  -webkit-mask-position: center;
  mask-position: center;
  -webkit-mask-size: contain;
  mask-size: contain;
}
</style>
