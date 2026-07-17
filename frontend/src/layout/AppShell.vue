<template>
  <div class="app-shell">
    <aside class="sidebar">
      <div class="brand-row">
        <div class="brand-logo">AOI</div>

        <div class="brand-text">
          <div class="brand-title">PCB AOI</div>
          <div class="brand-subtitle">Agent Platform</div>
        </div>
      </div>

      <div class="quick-actions">
        <button class="quick-btn" @click="goChat">
          <span class="quick-icon">✎</span>
          <span>New chat</span>
        </button>

        <button class="quick-btn" @click="goDetection">
          <span class="quick-icon">▧</span>
          <span>New detection</span>
        </button>
      </div>

      <div class="search-box">
        <span class="search-icon">⌕</span>
        <input v-model="searchKeyword" placeholder="Search histories" />
      </div>

      <section class="recent-section">
        <div class="section-title">Recents</div>

        <div v-if="recentLoading" class="empty-text">
          正在加载...
        </div>

        <div v-else-if="filteredRecents.length === 0" class="empty-text">
          暂无历史记录
        </div>

        <template v-else>
          <div
            v-for="item in filteredRecents"
            :key="item.type + '-' + item.id"
            class="recent-item"
            @click="openRecent(item)"
          >
            <span class="recent-icon">{{ item.icon }}</span>

            <span class="recent-content">
              <span class="recent-title">{{ item.title }}</span>
              <span class="recent-meta">{{ item.meta }}</span>
            </span>

            <button
              class="recent-delete"
              title="删除"
              @click.stop="handleDeleteRecent(item)"
            >
              ×
            </button>
          </div>
        </template>
      </section>

      <nav class="nav-section">
        <div class="section-title">功能区</div>

        <router-link
          v-for="item in normalNavItems"
          :key="item.path"
          :to="item.path"
          class="nav-item"
          active-class="nav-item-active"
        >
          <span class="nav-icon">{{ item.icon }}</span>
          <span>{{ item.title }}</span>
        </router-link>
      </nav>

      <nav
        v-if="developerNavItems.length > 0"
        class="nav-section developer-section"
      >
        <div class="section-title">开发者功能</div>

        <router-link
          v-for="item in developerNavItems"
          :key="item.path"
          :to="item.path"
          class="nav-item"
          active-class="nav-item-active"
        >
          <span class="nav-icon">{{ item.icon }}</span>
          <span>{{ item.title }}</span>
        </router-link>
      </nav>

      <div class="sidebar-footer">
        <div class="user-card">
          <div class="user-avatar">{{ usernameInitial }}</div>

          <div class="user-info">
            <div class="user-name">{{ username }}</div>
            <div class="user-role">{{ roleText }}</div>
          </div>
        </div>

        <button class="logout-btn" @click="handleLogout">
          退出登录
        </button>
      </div>
    </aside>

    <main class="main-area">
      <section class="content-area">
        <router-view />
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  getRecentHistories,
  deleteHistoryRecord,
} from '@/api/history'

const route = useRoute()
const router = useRouter()

const searchKeyword = ref('')
const recents = ref([])
const recentLoading = ref(false)

let searchTimer = null

const allNavItems = [
  {
    title: '智能问答',
    path: '/chat',
    icon: '✦',
    type: 'normal',
    roles: ['user', 'developer', 'admin'],
  },
  {
    title: '图片检测',
    path: '/detection',
    icon: '▧',
    type: 'normal',
    roles: ['user', 'developer', 'admin'],
  },
  {
    title: '缺陷复核',
    path: '/review',
    icon: '✓',
    type: 'normal',
    roles: ['user', 'developer', 'admin'],
  },
  {
    title: '模型训练与评估',
    path: '/training',
    icon: '◈',
    type: 'developer',
    roles: ['developer', 'admin'],
  },
  {
    title: '模型版本管理',
    path: '/models',
    icon: '▣',
    type: 'developer',
    roles: ['developer', 'admin'],
  },
]

const userRole = computed(() => {
  return localStorage.getItem('user_role') || localStorage.getItem('role') || 'user'
})

const roleText = computed(() => {
  const map = {
    user: '普通用户',
    developer: '算法工程师',
    admin: '管理员',
  }

  return map[userRole.value] || '普通用户'
})

const visibleNavItems = computed(() => {
  return allNavItems.filter(item => item.roles.includes(userRole.value))
})

const normalNavItems = computed(() => {
  return visibleNavItems.value.filter(item => item.type === 'normal')
})

const developerNavItems = computed(() => {
  return visibleNavItems.value.filter(item => item.type === 'developer')
})

const filteredRecents = computed(() => {
  return recents.value
})

const username = computed(() => {
  const directUsername =
    localStorage.getItem('username') ||
    localStorage.getItem('user_name') ||
    localStorage.getItem('nickname')

  if (directUsername) {
    return directUsername
  }

  const userInfoText =
    localStorage.getItem('userInfo') ||
    localStorage.getItem('user_info') ||
    localStorage.getItem('user')

  if (userInfoText) {
    try {
      const userInfo = JSON.parse(userInfoText)

      return (
        userInfo.username ||
        userInfo.name ||
        userInfo.nickname ||
        userInfo.email ||
        '已登录用户'
      )
    } catch (error) {
      return '已登录用户'
    }
  }

  return '已登录用户'
})

const usernameInitial = computed(() => {
  return username.value ? username.value.slice(0, 1).toUpperCase() : 'U'
})

async function loadRecents(keyword = '') {
  recentLoading.value = true

  try {
    const res = await getRecentHistories({
      keyword: keyword || undefined,
      limit: 30,
    })

    if (Array.isArray(res)) {
      recents.value = res
      return
    }

    if (Array.isArray(res?.data)) {
      recents.value = res.data
      return
    }

    if (Array.isArray(res?.data?.data)) {
      recents.value = res.data.data
      return
    }

    recents.value = []
  } catch (error) {
    console.error('获取最近记录失败:', error)
    recents.value = []
  } finally {
    recentLoading.value = false
  }
}

function goChat() {
  router.push({
    path: '/chat',
    query: {
      new: Date.now().toString(),
    },
  })
}

function goDetection() {
  router.push('/detection')
}

function openRecent(item) {
  if (item.path) {
    router.push(item.path)
  }
}

async function handleDeleteRecent(item) {
  const ok = window.confirm(`确定删除这条历史记录吗？\n${item.title}`)

  if (!ok) {
    return
  }

  try {
    await deleteHistoryRecord(item.id)
    await loadRecents(searchKeyword.value.trim())

    if (item.path && route.fullPath === item.path) {
      router.push({
        path: '/chat',
        query: {
          new: Date.now().toString(),
        },
      })
    }
  } catch (error) {
    console.error('删除历史记录失败:', error)
    window.alert('删除失败，请查看后端日志')
  }
}

function handleLogout() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('token')
  localStorage.removeItem('username')
  localStorage.removeItem('user_name')
  localStorage.removeItem('nickname')
  localStorage.removeItem('userInfo')
  localStorage.removeItem('user_info')
  localStorage.removeItem('user')
  localStorage.removeItem('user_role')
  localStorage.removeItem('role')

  router.push('/')
}

function handleHistoryUpdated() {
  loadRecents(searchKeyword.value.trim())
}

watch(searchKeyword, value => {
  if (searchTimer) {
    clearTimeout(searchTimer)
  }

  searchTimer = setTimeout(() => {
    loadRecents(value.trim())
  }, 300)
})

onMounted(() => {
  loadRecents()
  window.addEventListener('history-updated', handleHistoryUpdated)
})

onBeforeUnmount(() => {
  window.removeEventListener('history-updated', handleHistoryUpdated)

  if (searchTimer) {
    clearTimeout(searchTimer)
  }
})
</script>

<style scoped>
.app-shell {
  min-height: 100vh;
  display: flex;
  background: #ffffff;
  color: #111827;
}

.sidebar {
  width: 292px;
  min-width: 292px;
  height: 100vh;
  background: #f9f9f9;
  border-right: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;
  padding: 12px;
}

.brand-row {
  height: 46px;
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.brand-logo {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: linear-gradient(135deg, #22c55e, #3b82f6);
  color: #ffffff;
  font-size: 12px;
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.brand-text {
  min-width: 0;
}

.brand-title {
  color: #111827;
  font-size: 15px;
  font-weight: 700;
}

.brand-subtitle {
  margin-top: 2px;
  color: #9ca3af;
  font-size: 11px;
}

.quick-actions {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 12px;
}

.quick-btn {
  height: 38px;
  border-radius: 10px;
  border: none;
  background: transparent;
  color: #111827;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 10px;
  cursor: pointer;
  font-size: 14px;
  text-align: left;
}

.quick-btn:hover {
  background: #ececec;
}

.quick-icon {
  width: 20px;
  text-align: center;
  flex-shrink: 0;
}

.search-box {
  height: 38px;
  border-radius: 10px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 10px;
  margin-bottom: 14px;
}

.search-icon {
  color: #9ca3af;
  font-size: 14px;
}

.search-box input {
  flex: 1;
  min-width: 0;
  border: none;
  outline: none;
  background: transparent;
  color: #111827;
  font-size: 13px;
}

.search-box input::placeholder {
  color: #9ca3af;
}

.section-title {
  padding: 0 10px;
  margin-bottom: 6px;
  color: #9ca3af;
  font-size: 12px;
}

.recent-section {
  max-height: 260px;
  overflow: auto;
  margin-bottom: 14px;
}

.empty-text {
  padding: 10px;
  color: #9ca3af;
  font-size: 13px;
}

.recent-item {
  width: 100%;
  min-height: 46px;
  border: none;
  border-radius: 10px;
  background: transparent;
  color: #374151;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 7px 10px;
  cursor: pointer;
  text-align: left;
}

.recent-item:hover {
  background: #ececec;
}

.recent-icon {
  width: 20px;
  flex-shrink: 0;
  text-align: center;
  color: #6b7280;
}

.recent-content {
  min-width: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
}

.recent-title {
  color: #111827;
  font-size: 13px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.recent-meta {
  margin-top: 3px;
  color: #9ca3af;
  font-size: 11px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.recent-delete {
  width: 22px;
  height: 22px;
  border: none;
  border-radius: 999px;
  background: transparent;
  color: #9ca3af;
  cursor: pointer;
  flex-shrink: 0;
  font-size: 16px;
  line-height: 1;
  display: none;
  align-items: center;
  justify-content: center;
}

.recent-item:hover .recent-delete {
  display: inline-flex;
}

.recent-delete:hover {
  background: #fee2e2;
  color: #dc2626;
}

.nav-section {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 14px;
}

.developer-section {
  border-top: 1px solid #e5e7eb;
  padding-top: 12px;
}

.nav-item {
  height: 38px;
  border-radius: 10px;
  color: #374151;
  text-decoration: none;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 10px;
  font-size: 14px;
}

.nav-item:hover {
  background: #ececec;
}

.nav-item-active {
  background: #ececec;
  color: #111827;
  font-weight: 600;
}

.nav-icon {
  width: 20px;
  text-align: center;
  flex-shrink: 0;
}

.sidebar-footer {
  margin-top: auto;
  border-top: 1px solid #e5e7eb;
  padding-top: 12px;
}

.user-card {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 9px;
}

.user-avatar {
  width: 34px;
  height: 34px;
  border-radius: 999px;
  background: #111827;
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
}

.user-info {
  min-width: 0;
}

.user-name {
  color: #111827;
  font-size: 13px;
  font-weight: 600;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.user-role {
  margin-top: 2px;
  color: #9ca3af;
  font-size: 11px;
}

.logout-btn {
  width: 100%;
  height: 34px;
  border: none;
  border-radius: 10px;
  background: #ececec;
  color: #374151;
  cursor: pointer;
  font-size: 13px;
}

.logout-btn:hover {
  background: #111827;
  color: #ffffff;
}

.main-area {
  flex: 1;
  min-width: 0;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #ffffff;
}

.content-area {
  flex: 1;
  overflow: auto;
  padding: 24px 28px 36px;
  background: #ffffff;
}

@media (max-width: 900px) {
  .sidebar {
    width: 240px;
    min-width: 240px;
  }

  .content-area {
    padding: 18px;
  }
}
</style>