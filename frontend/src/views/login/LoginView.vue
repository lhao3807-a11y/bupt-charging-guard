<script setup lang="ts">
/**
 * 登录页 —— 第 2 周任务 6.6（`PLAN_4WEEKS.md` §3.3 / `docs/TASK_WU_WEEK2.md`）
 *
 * 交付物是两件：① 线框 `docs/design/wireframes/login.html`；② **前端可直接用的页面结构**（本文件）。
 * 本组件的定位是**视觉骨架**，不是鉴权实现 —— 契约尚未定义登录接口，
 * 所以这里**不发任何请求、也不模拟「登录成功」**，避免演示时把假状态当真状态。
 *
 * 四个态（线框样张已定稿）与本文件的对应关系：
 *   ① 默认态      —— 直接渲染
 *   ② 校验失败态  —— 真校验（`rules`，错误逐字段写在下方，不弹窗）。
 *                      线框口径：**空值也允许点击**（点一下才知道错在哪），按钮置灰只用于「提交中」
 *   ③ 凭据错误态  —— 顶部提示条 `notice`（`type: 'error'`），接接口后把 `catch` 分支指过来即可
 *   ④ 提交中      —— `submitting`（按钮 loading + 禁用，防重复提交）
 *
 * 布局：本页**不套后台骨架**（无侧边导航/顶栏/页脚），由 `router` 的 `meta.blank` +
 * `App.vue` 控制外层渲染。契约 §1.1 的「后台 6 页」不含本页，故：
 *   - 不进侧边导航（`navRoutes` 里没有它）
 *   - 不改 `/` 的默认跳转、不引入路由守卫 → **不影响现有 Demo 主流程**
 */
import { reactive, ref } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'

import AppIcon from '@/components/common/AppIcon.vue'
import logoFull from '@/assets/logos/logo-full.svg'

const formRef = ref<FormInstance>()

const form = reactive({
  username: '',
  password: '',
  remember: true,
})

const rules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, message: '用户名至少 3 个字符', trigger: 'blur' },
  ],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

const submitting = ref(false)

/** 顶部提示条（线框样张③「凭据错误」用的就是它；未接接口时承载骨架说明） */
const notice = ref<{ type: 'info' | 'error'; text: string } | null>(null)

/** 页脚年份取当前年，避免过年后成为一句过期文案（同 AppShell 做法） */
const year = new Date().getFullYear()

async function handleSubmit() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  notice.value = null

  // ⚠️ 这里**不发请求**：契约 §6 未定义鉴权接口。
  // `setTimeout` 仅为让线框样张④「提交中」在真机上可见；
  // 接入真实接口后，这段延时由请求本身占据，删掉即可。
  window.setTimeout(() => {
    submitting.value = false
    notice.value = {
      type: 'info',
      text: '本页为视觉骨架：契约尚未定义登录接口，提交不会发生真实登录。接入接口后，凭据错误会在此处以红色提示条呈现。',
    }
  }, 600)
}

function handleForget() {
  notice.value = {
    type: 'info',
    text: '忘记密码需联系管理员重置，本演示环境不提供自助找回。',
  }
}
</script>

<template>
  <div class="auth">
    <div class="auth__inner">
      <!-- 品牌区：完整版 LOGO（图形 + 主标题 + 副标题），与线框一致 -->
      <div class="auth-brand">
        <!-- alt 用品牌正式写法（与页脚、index.html 一致）：「桩」点北邮 带引号 -->
        <img class="auth-brand__logo" :src="logoFull" alt="「桩」点北邮 · 充电桩车位防占系统" />
        <p class="auth-brand__slogan">用视觉识别替代人工巡查，让每一度电都停在对的车位</p>
      </div>

      <div class="auth-card">
        <h1 class="auth-card__title">登录</h1>
        <p class="auth-card__sub">请使用校方分配的账号登录管理后台</p>

        <el-alert
          v-if="notice"
          :type="notice.type"
          :closable="false"
          class="auth-card__notice"
          :title="notice.text"
          show-icon
        />

        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          label-position="top"
          class="auth-form"
          @submit.prevent="handleSubmit"
        >
          <el-form-item label="用户名" prop="username">
            <el-input
              v-model="form.username"
              placeholder="请输入用户名"
              autocomplete="username"
              :disabled="submitting"
            />
          </el-form-item>

          <el-form-item label="密码" prop="password">
            <el-input
              v-model="form.password"
              type="password"
              placeholder="请输入密码"
              autocomplete="current-password"
              show-password
              :disabled="submitting"
            />
            <span class="auth-form__help">区分大小写；连续 5 次失败会锁定 10 分钟</span>
          </el-form-item>

          <div class="auth-row">
            <el-checkbox v-model="form.remember" :disabled="submitting">记住我</el-checkbox>
            <el-button link type="primary" class="auth-row__forget" @click="handleForget">
              忘记密码？
            </el-button>
          </div>

          <el-button
            type="primary"
            class="auth-form__submit"
            :loading="submitting"
            :disabled="submitting"
            native-type="submit"
            @click="handleSubmit"
          >
            登 录
          </el-button>
        </el-form>

        <div class="auth-note">
          <AppIcon name="icon-warning" :size="14" class="auth-note__icon" />
          <span>
            演示环境无真实鉴权：登录状态不落库、不跨设备同步。答辩时请说明这一点。
          </span>
        </div>
      </div>

      <p class="auth-foot">© {{ year }} 「桩」点北邮 · 北京邮电大学</p>
    </div>
  </div>
</template>

<style scoped>
.auth {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-10) var(--space-4);
  background: var(--bg-page);
}

.auth__inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-5);
  width: 400px;
  max-width: 100%;
}

/* ---------------------------------------------------------------- 品牌区 */

.auth-brand {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-3);
}

.auth-brand__logo {
  display: block;
  height: 32px;
  width: auto;
}

.auth-brand__slogan {
  margin: 0;
  font-size: var(--font-size-sm);
  line-height: var(--line-height-base);
  color: var(--text-tertiary);
  text-align: center;
}

/* ------------------------------------------------------------------ 卡片 */

.auth-card {
  width: 100%;
  background: var(--bg-container);
  border: 1px solid var(--border-base);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  padding: var(--space-8);
}

.auth-card__title {
  margin: 0;
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  line-height: var(--line-height-tight);
  color: var(--text-primary);
}

.auth-card__sub {
  margin: var(--space-2) 0 0;
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

.auth-card__notice {
  margin-top: var(--space-4);
}

/* ------------------------------------------------------------------ 表单 */

.auth-form {
  margin-top: var(--space-5);
}

.auth-form__help {
  font-size: var(--font-size-xs);
  line-height: var(--line-height-base);
  color: var(--text-tertiary);
}

.auth-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  margin-bottom: var(--space-5);
}

.auth-row__forget {
  font-size: var(--font-size-sm);
}

.auth-form__submit {
  width: 100%;
}

/* ------------------------------------------------------- 演示环境说明条 */

.auth-note {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  margin-top: var(--space-5);
  padding: var(--space-3);
  background: var(--state-info-bg);
  border: 1px solid var(--state-info-border);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-xs);
  line-height: var(--line-height-base);
  color: var(--state-info-text);
}

.auth-note__icon {
  margin-top: 3px;
}

/* ------------------------------------------------------------------ 页脚 */

.auth-foot {
  margin: 0;
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
}
</style>
