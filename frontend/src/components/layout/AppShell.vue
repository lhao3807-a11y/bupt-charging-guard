<script setup lang="ts">
/**
 * AppShell —— 后台骨架（component-inventory.md §2）
 *
 * 侧边栏 220px + 顶栏 56px（高 40px 导航项）+ 内容区。
 * 6 项导航顺序照契约 §1.1，第 6 项（实时识别预览）第 1 周置灰预留。
 */
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import StatusPill from '@/components/common/StatusPill.vue'
import { navRoutes } from '@/router'

const route = useRoute()
const router = useRouter()

interface NavItem {
  path: string
  title: string
  icon: string
  reserved: boolean
}

const navItems: NavItem[] = navRoutes.map((r) => ({
  path: r.path,
  title: (r.meta?.title as string) ?? '',
  icon: (r.meta?.icon as string) ?? 'Menu',
  reserved: Boolean(r.meta?.reserved),
}))

const activePath = computed(() => route.path)

const currentTitle = computed(() => (route.meta?.title as string) ?? '')

function handleSelect(path: string) {
  if (path !== route.path) void router.push(path)
}
</script>

<template>
  <el-container class="app-shell">
    <!-- 侧边栏 220px -->
    <el-aside class="app-aside" width="var(--layout-sidebar-width)">
      <div class="app-brand">
        <div class="app-brand__mark" aria-hidden="true">
          <el-icon :size="18"><Lightning /></el-icon>
        </div>
        <div class="app-brand__text">
          <div class="app-brand__name">桩点北邮</div>
          <div class="app-brand__sub">充电桩车位防占系统</div>
        </div>
      </div>

      <el-menu :default-active="activePath" class="app-menu" @select="handleSelect">
        <el-menu-item
          v-for="item in navItems"
          :key="item.path"
          :index="item.path"
          :disabled="item.reserved"
        >
          <el-icon><component :is="item.icon" /></el-icon>
          <span class="app-menu__label">{{ item.title }}</span>
          <span v-if="item.reserved" class="app-menu__badge">预留</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <!-- 顶栏 56px -->
      <el-header class="app-header" height="var(--layout-header-height)">
        <el-breadcrumb separator="/" class="app-header__crumb">
          <el-breadcrumb-item>后台管理</el-breadcrumb-item>
          <el-breadcrumb-item>{{ currentTitle || '首页' }}</el-breadcrumb-item>
        </el-breadcrumb>

        <div class="app-header__right">
          <StatusPill prefix="info" text="开发期 · SQLite" />
          <el-avatar :size="28" class="app-header__avatar">吕</el-avatar>
        </div>
      </el-header>

      <el-main class="app-main">
        <router-view v-slot="{ Component }">
          <component :is="Component" />
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.app-shell {
  height: 100vh;
}

.app-aside {
  background: var(--bg-container);
  border-right: 1px solid var(--border-base);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.app-brand {
  height: var(--layout-header-height);
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: 0 var(--space-4);
  border-bottom: 1px solid var(--border-light);
  flex-shrink: 0;
}

.app-brand__mark {
  width: 30px;
  height: 30px;
  border-radius: var(--radius-sm);
  background: var(--brand-primary);
  color: var(--text-inverse);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.app-brand__text {
  min-width: 0;
}

.app-brand__name {
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
  line-height: var(--line-height-tight);
}

.app-brand__sub {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  line-height: var(--line-height-tight);
  white-space: nowrap;
}

.app-menu {
  flex: 1;
  overflow-y: auto;
  padding-top: var(--space-2);
  background: transparent;
}

.app-menu__label {
  margin-left: var(--space-1);
}

/* 预留角标：--state-info-* 中性档 */
.app-menu__badge {
  margin-left: auto;
  padding: 0 var(--space-1);
  font-size: var(--font-size-xs);
  line-height: 16px;
  border-radius: var(--radius-xs);
  background: var(--state-info-bg);
  border: 1px solid var(--state-info-border);
  color: var(--state-info-text);
}

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--bg-container);
  border-bottom: 1px solid var(--border-base);
  padding: 0 var(--layout-gutter);
}

.app-header__right {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.app-header__avatar {
  background: var(--brand-primary-light-9);
  color: var(--brand-primary);
  font-size: var(--font-size-sm);
}

.app-main {
  background: var(--bg-page);
  padding: 0;
  overflow-y: auto;
}
</style>
