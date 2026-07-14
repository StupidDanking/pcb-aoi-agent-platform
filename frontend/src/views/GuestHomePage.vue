<template>
  <div class="guest-page">
    <aside class="guest-sidebar">
      <div class="sidebar-logo">AOI</div>

      <button class="side-icon active" title="New chat">
        ✎
      </button>

      <button class="side-icon" title="Search">
        ⌕
      </button>

      <button class="side-icon" title="Detection">
        ▧
      </button>

      <button class="side-icon" title="Help">
        ?
      </button>
    </aside>

    <main class="guest-main">
      <header class="guest-header">
        <div class="brand-title">PCB AOI Agent Platform</div>

        <div class="header-actions">
          <button class="login-btn" @click="goLogin">Log in</button>
          <button class="signup-btn" @click="goRegister">Sign up for free</button>
        </div>
      </header>

      <section class="hero">
        <div class="hero-badge">YOLOv11 · PCB Defect Detection</div>

        <h1>今天想分析哪块 PCB？</h1>

        <p class="hero-subtitle">
          可以上传 PCB 图片进行缺陷检测，也可以直接询问缺陷类型、质量评估、模型指标和检测建议。
        </p>

        <div class="input-card">
          <textarea
            v-model="question"
            placeholder="上传 PCB 图片，或者输入你的问题..."
            rows="1"
          />

          <div class="input-actions">
            <button class="plus-btn" @click="goDetection">+</button>

            <div class="right-actions">
              <button @click="goDetection">图片检测</button>
              <button class="primary-action" @click="goChat">开始问答</button>
            </div>
          </div>
        </div>

        <div class="quick-prompts">
          <button @click="fillPrompt('PCB 图像中缺孔缺陷一般是什么原因造成的？')">
            缺孔原因分析
          </button>

          <button @click="fillPrompt('如何判断 PCB 短路缺陷的严重程度？')">
            短路严重程度
          </button>

          <button @click="fillPrompt('YOLOv11 模型 mAP50 和 Recall 分别代表什么？')">
            模型指标解释
          </button>

          <button @click="goDetection">
            上传 PCB 图片检测
          </button>
        </div>

        <div class="login-tip">
          登录后可以保存问答历史、检测历史和模型实验记录。
          开发者账号可以进入模型训练、评估和版本管理。
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const question = ref('')

function goLogin() {
  router.push('/login')
}

function goRegister() {
  router.push('/register')
}

function goChat() {
  localStorage.setItem('guest_pending_question', question.value || '')
  router.push('/login')
}

function goDetection() {
  router.push('/login')
}

function fillPrompt(text) {
  question.value = text
}
</script>

<style scoped>
.guest-page {
  min-height: 100vh;
  display: flex;
  background: #ffffff;
  color: #111827;
}

.guest-sidebar {
  width: 58px;
  border-right: 1px solid #e5e7eb;
  background: #f9fafb;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 14px 8px;
  gap: 12px;
}

.sidebar-logo {
  width: 32px;
  height: 32px;
  border-radius: 10px;
  background: linear-gradient(135deg, #22c55e, #3b82f6);
  color: #ffffff;
  font-size: 12px;
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
}

.side-icon {
  width: 36px;
  height: 36px;
  border: none;
  background: transparent;
  border-radius: 10px;
  cursor: pointer;
  color: #111827;
  font-size: 17px;
}

.side-icon:hover,
.side-icon.active {
  background: #ececec;
}

.guest-main {
  flex: 1;
  min-width: 0;
  position: relative;
}

.guest-header {
  height: 58px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
}

.brand-title {
  font-size: 15px;
  font-weight: 600;
  color: #111827;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.login-btn {
  height: 34px;
  padding: 0 16px;
  border-radius: 999px;
  border: none;
  background: #111827;
  color: #ffffff;
  cursor: pointer;
  font-size: 13px;
}

.signup-btn {
  height: 34px;
  padding: 0 16px;
  border-radius: 999px;
  border: 1px solid #d1d5db;
  background: #ffffff;
  color: #111827;
  cursor: pointer;
  font-size: 13px;
}

.hero {
  min-height: calc(100vh - 58px);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  transform: translateY(-30px);
  padding: 24px;
}

.hero-badge {
  height: 32px;
  padding: 0 14px;
  border-radius: 999px;
  background: #f3f4f6;
  border: 1px solid #e5e7eb;
  color: #4b5563;
  display: flex;
  align-items: center;
  font-size: 13px;
  margin-bottom: 24px;
}

.hero h1 {
  margin: 0;
  font-size: 30px;
  font-weight: 700;
  color: #111827;
}

.hero-subtitle {
  margin: 14px 0 28px;
  max-width: 720px;
  text-align: center;
  color: #6b7280;
  font-size: 15px;
  line-height: 1.8;
}

.input-card {
  width: min(760px, 92vw);
  min-height: 58px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  box-shadow: 0 16px 40px rgba(15, 23, 42, 0.08);
  border-radius: 28px;
  padding: 10px 12px 10px 16px;
}

.input-card textarea {
  width: 100%;
  border: none;
  outline: none;
  resize: none;
  font-size: 15px;
  line-height: 1.6;
  color: #111827;
  font-family: inherit;
  background: transparent;
  padding: 4px 4px 8px;
}

.input-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.plus-btn {
  width: 32px;
  height: 32px;
  border-radius: 999px;
  border: 1px solid #e5e7eb;
  background: #ffffff;
  color: #111827;
  cursor: pointer;
  font-size: 20px;
}

.right-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.right-actions button {
  height: 32px;
  border: none;
  background: #f3f4f6;
  color: #374151;
  border-radius: 999px;
  padding: 0 14px;
  cursor: pointer;
  font-size: 13px;
}

.right-actions .primary-action {
  background: #111827;
  color: #ffffff;
}

.quick-prompts {
  width: min(760px, 92vw);
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
  margin-top: 22px;
}

.quick-prompts button {
  min-height: 54px;
  border-radius: 14px;
  border: 1px solid #e5e7eb;
  background: #ffffff;
  color: #374151;
  cursor: pointer;
  font-size: 13px;
  text-align: left;
  padding: 10px 12px;
}

.quick-prompts button:hover {
  background: #f9fafb;
}

.login-tip {
  margin-top: 24px;
  color: #9ca3af;
  font-size: 13px;
  text-align: center;
}

@media (max-width: 900px) {
  .quick-prompts {
    grid-template-columns: 1fr 1fr;
  }

  .hero h1 {
    font-size: 24px;
  }
}
</style>