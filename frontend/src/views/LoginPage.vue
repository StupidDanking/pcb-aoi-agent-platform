<template>
  <div class="guest-page">
    <!-- 左侧极简边栏 -->
    <aside class="guest-sidebar">
      <div class="sidebar-logo">AOI</div>

      <div class="sidebar-icons">
        <button class="icon-btn">✎</button>
        <button class="icon-btn">⌕</button>
        <button class="icon-btn">☰</button>
        <button class="icon-btn">?</button>
      </div>
    </aside>

    <!-- 主区域 -->
    <main class="guest-main">
      <header class="guest-header">
        <div class="brand-inline">
          <span class="brand-name">PCB AOI Agent Platform</span>
        </div>

        <div class="header-actions">
          <button class="header-login-btn" @click="openLogin">Log in</button>
          <button class="header-signup-btn" @click="openRegister">Sign up for free</button>
        </div>
      </header>

      <section class="hero-section">
        <div class="hero-badge">YOLOv11 · PCB Defect Detection</div>
        <h1>今天想分析哪块 PCB？</h1>
        <p>
          可以上传 PCB 图片进行缺陷检测，也可以直接询问缺陷类型、质量评估、
          模型指标和检测建议。
        </p>

        <div class="hero-input-box" @click="openLogin">
          <div class="hero-input-placeholder">
            上传 PCB 图片，或者输入你的问题...
          </div>
          <div class="hero-input-actions">
            <button class="mini-btn">图片检测</button>
            <button class="primary-mini-btn">开始问答</button>
          </div>
        </div>

        <div class="quick-actions">
          <button @click="openLogin">缺孔原因分析</button>
          <button @click="openLogin">短路严重程度</button>
          <button @click="openLogin">模型指标解释</button>
          <button @click="openLogin">上传 PCB 图片检测</button>
        </div>

        <div class="hero-tip">
          登录后可以保存问答历史、检测历史和模型实验记录。
          开发者账号可以进入模型训练、评估和版本管理。
        </div>
      </section>
    </main>

    <!-- 登录 / 注册弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :show-close="true"
      :close-on-click-modal="true"
      :destroy-on-close="false"
      width="420px"
      class="auth-dialog"
    >
      <div class="auth-card">
        <div class="auth-brand">
          <div class="auth-logo">AOI</div>
          <div class="auth-brand-text">
            <div class="auth-title">PCB AOI Agent Platform</div>
            <div class="auth-subtitle">印制电路板缺陷智能检测平台</div>
          </div>
        </div>

        <div class="auth-header">
          <h2>{{ isRegisterMode ? '创建账号' : '登录系统' }}</h2>
          <p>
            {{ isRegisterMode ? '注册一个新账号进入平台' : '请输入账号信息进入平台' }}
          </p>
        </div>

        <!-- 登录 -->
        <el-form
          v-if="!isRegisterMode"
          ref="loginFormRef"
          :model="loginForm"
          :rules="loginRules"
          label-position="top"
          class="auth-form"
        >
          <el-form-item label="用户名" prop="username">
            <el-input
              v-model="loginForm.username"
              placeholder="请输入用户名"
              size="large"
              clearable
            />
          </el-form-item>

          <el-form-item label="密码" prop="password">
            <el-input
              v-model="loginForm.password"
              placeholder="请输入密码"
              size="large"
              type="password"
              show-password
              clearable
            />
          </el-form-item>

          <el-button
            class="submit-btn"
            type="primary"
            size="large"
            :loading="loading"
            @click="handleLogin"
          >
            登录
          </el-button>

          <div class="switch-row">
            <span>还没有账号？</span>
            <button type="button" @click="switchToRegister">立即注册</button>
          </div>
        </el-form>

        <!-- 注册 -->
        <el-form
          v-else
          ref="registerFormRef"
          :model="registerForm"
          :rules="registerRules"
          label-position="top"
          class="auth-form"
        >
          <el-form-item label="用户名" prop="username">
            <el-input
              v-model="registerForm.username"
              placeholder="请输入用户名"
              size="large"
              clearable
            />
          </el-form-item>

          <el-form-item label="邮箱" prop="email">
            <el-input
              v-model="registerForm.email"
              placeholder="请输入邮箱"
              size="large"
              clearable
            />
          </el-form-item>

          <el-form-item label="密码" prop="password">
            <el-input
              v-model="registerForm.password"
              placeholder="请输入密码"
              size="large"
              type="password"
              show-password
              clearable
            />
          </el-form-item>

          <el-form-item label="确认密码" prop="confirmPassword">
            <el-input
              v-model="registerForm.confirmPassword"
              placeholder="请再次输入密码"
              size="large"
              type="password"
              show-password
              clearable
            />
          </el-form-item>

          <el-button
            class="submit-btn"
            type="primary"
            size="large"
            :loading="loading"
            @click="handleRegister"
          >
            注册
          </el-button>

          <div class="switch-row">
            <span>已有账号？</span>
            <button type="button" @click="switchToLogin">返回登录</button>
          </div>
        </el-form>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { login, register } from '@/api/auth'

const router = useRouter()

const dialogVisible = ref(true)
const authMode = ref('login')
const loading = ref(false)

const loginFormRef = ref(null)
const registerFormRef = ref(null)

const isRegisterMode = computed(() => authMode.value === 'register')

const loginForm = reactive({
  username: '',
  password: '',
})

const registerForm = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: '',
})

const loginRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能小于 6 位', trigger: 'blur' },
  ],
}

const registerRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    {
      type: 'email',
      message: '请输入正确的邮箱格式',
      trigger: ['blur', 'change'],
    },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能小于 6 位', trigger: 'blur' },
  ],
  confirmPassword: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    {
      validator: (_, value, callback) => {
        if (value !== registerForm.password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur',
    },
  ],
}

function openLogin() {
  authMode.value = 'login'
  dialogVisible.value = true
}

function openRegister() {
  authMode.value = 'register'
  dialogVisible.value = true
}

function switchToLogin() {
  authMode.value = 'login'
}

function switchToRegister() {
  authMode.value = 'register'
}

async function handleLogin() {
  if (!loginFormRef.value) return

  try {
    await loginFormRef.value.validate()
  } catch {
    return
  }

  loading.value = true

  try {
    const res = await login({
      username: loginForm.username.trim(),
      password: loginForm.password,
    })

    const payload = res?.data || res || {}
    const rawData = payload?.data || payload

    const accessToken = rawData.access_token || rawData.token
    const username = rawData.username || loginForm.username.trim()
    const role = rawData.role || 'user'
    const id = rawData.id || ''
    const email = rawData.email || ''

    if (!accessToken) {
      ElMessage.error('登录失败：后端未返回 access_token')
      return
    }

    localStorage.setItem('access_token', accessToken)
    localStorage.setItem('username', username)
    localStorage.setItem('user_role', role)
    localStorage.setItem(
      'userInfo',
      JSON.stringify({
        id,
        username,
        email,
        role,
      }),
    )

    ElMessage.success('登录成功')
    dialogVisible.value = false
    router.push('/chat')
  } catch (error) {
    console.error('登录失败:', error)
    ElMessage.error('登录失败，请检查用户名或密码')
  } finally {
    loading.value = false
  }
}

async function handleRegister() {
  if (!registerFormRef.value) return

  try {
    await registerFormRef.value.validate()
  } catch {
    return
  }

  loading.value = true

  try {
    await register({
      username: registerForm.username.trim(),
      email: registerForm.email.trim(),
      password: registerForm.password,
    })

    ElMessage.success('注册成功，请登录')

    loginForm.username = registerForm.username
    loginForm.password = registerForm.password

    registerForm.username = ''
    registerForm.email = ''
    registerForm.password = ''
    registerForm.confirmPassword = ''

    authMode.value = 'login'

    await nextTick()
  } catch (error) {
    console.error('注册失败:', error)
    ElMessage.error('注册失败，请检查输入信息或用户名是否已存在')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  dialogVisible.value = true
})
</script>

<style scoped>
.guest-page {
  min-height: 100vh;
  background: #ffffff;
  display: flex;
  color: #111827;
}

.guest-sidebar {
  width: 64px;
  border-right: 1px solid #ececec;
  background: #f9f9f9;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 10px 0;
  gap: 18px;
}

.sidebar-logo {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: linear-gradient(135deg, #22c55e, #3b82f6);
  color: #fff;
  font-weight: 700;
  font-size: 11px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.sidebar-icons {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 10px;
}

.icon-btn {
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 8px;
  background: transparent;
  cursor: pointer;
  color: #4b5563;
}

.icon-btn:hover {
  background: #ececec;
}

.guest-main {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.guest-header {
  height: 56px;
  border-bottom: 1px solid #ececec;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px 0 14px;
}

.brand-inline {
  display: flex;
  align-items: center;
  gap: 10px;
}

.brand-name {
  font-size: 15px;
  font-weight: 600;
  color: #111827;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.header-login-btn {
  height: 32px;
  padding: 0 16px;
  border-radius: 999px;
  border: none;
  background: #111827;
  color: #fff;
  font-size: 13px;
  cursor: pointer;
}

.header-signup-btn {
  height: 32px;
  padding: 0 16px;
  border-radius: 999px;
  border: 1px solid #d1d5db;
  background: #fff;
  color: #111827;
  font-size: 13px;
  cursor: pointer;
}

.hero-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 30px 20px 80px;
  text-align: center;
}

.hero-badge {
  display: inline-flex;
  align-items: center;
  padding: 0 14px;
  height: 30px;
  border-radius: 999px;
  background: #f3f4f6;
  color: #6b7280;
  font-size: 13px;
  margin-bottom: 18px;
}

.hero-section h1 {
  margin: 0;
  font-size: 46px;
  font-weight: 700;
  color: #111827;
}

.hero-section p {
  margin: 14px 0 0;
  max-width: 760px;
  font-size: 15px;
  line-height: 1.8;
  color: #6b7280;
}

.hero-input-box {
  width: 100%;
  max-width: 680px;
  margin-top: 24px;
  border: 1px solid #e5e7eb;
  border-radius: 24px;
  background: #fff;
  padding: 14px 16px 12px;
  box-shadow: 0 4px 18px rgba(17, 24, 39, 0.06);
  cursor: pointer;
}

.hero-input-placeholder {
  text-align: left;
  font-size: 14px;
  color: #9ca3af;
  margin-bottom: 12px;
}

.hero-input-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.mini-btn {
  height: 30px;
  padding: 0 14px;
  border-radius: 999px;
  border: 1px solid #e5e7eb;
  background: #fff;
  color: #374151;
  cursor: pointer;
}

.primary-mini-btn {
  height: 30px;
  padding: 0 14px;
  border-radius: 999px;
  border: none;
  background: #111827;
  color: #fff;
  cursor: pointer;
}

.quick-actions {
  margin-top: 16px;
  display: grid;
  grid-template-columns: repeat(4, minmax(120px, 1fr));
  gap: 12px;
  width: 100%;
  max-width: 680px;
}

.quick-actions button {
  height: 44px;
  border-radius: 14px;
  border: 1px solid #e5e7eb;
  background: #fff;
  color: #374151;
  cursor: pointer;
  font-size: 13px;
}

.quick-actions button:hover {
  background: #f9fafb;
}

.hero-tip {
  margin-top: 16px;
  font-size: 13px;
  color: #9ca3af;
}

.auth-card {
  padding: 4px 4px 10px;
}

.auth-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 26px;
}

.auth-logo {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  background: linear-gradient(135deg, #22c55e, #3b82f6);
  color: #fff;
  font-size: 13px;
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
}

.auth-title {
  font-size: 18px;
  font-weight: 700;
  color: #111827;
}

.auth-subtitle {
  margin-top: 4px;
  font-size: 12px;
  color: #6b7280;
}

.auth-header {
  margin-bottom: 18px;
}

.auth-header h2 {
  margin: 0;
  font-size: 32px;
  color: #111827;
  font-weight: 700;
}

.auth-header p {
  margin: 8px 0 0;
  font-size: 14px;
  color: #6b7280;
}

.auth-form {
  margin-top: 10px;
}

.submit-btn {
  width: 100%;
  height: 44px;
  margin-top: 6px;
  border-radius: 12px;
}

.switch-row {
  margin-top: 18px;
  text-align: center;
  font-size: 14px;
  color: #6b7280;
}

.switch-row button {
  border: none;
  background: transparent;
  color: #2563eb;
  cursor: pointer;
  font-size: 14px;
  margin-left: 6px;
}

:deep(.auth-dialog .el-dialog) {
  border-radius: 20px;
  padding: 6px;
}

:deep(.auth-dialog .el-dialog__header) {
  margin-right: 0;
  padding-bottom: 0;
}

:deep(.auth-dialog .el-dialog__body) {
  padding-top: 10px;
}

@media (max-width: 900px) {
  .hero-section h1 {
    font-size: 30px;
  }

  .quick-actions {
    grid-template-columns: repeat(2, minmax(120px, 1fr));
  }
}

@media (max-width: 640px) {
  .guest-sidebar {
    display: none;
  }

  .guest-header {
    padding: 0 12px;
  }

  .brand-name {
    font-size: 14px;
  }

  .header-actions {
    gap: 8px;
  }

  .header-login-btn,
  .header-signup-btn {
    padding: 0 12px;
    font-size: 12px;
  }

  .hero-section {
    padding: 24px 14px 60px;
  }

  .quick-actions {
    grid-template-columns: 1fr;
  }
}
</style>