<template>
  <div class="review-page">
    <div class="page-grid">
      <aside class="task-panel">
        <div class="panel-header">
          <div>
            <h2>缺陷复核</h2>
            <p>确认真实缺陷、标记误报，并留下备注。</p>
          </div>
          <button class="ghost-btn" :disabled="loadingTasks" @click="loadTasks">
            刷新
          </button>
        </div>

        <div v-if="stats" class="stats-row">
          <div>
            <span>已确认</span>
            <strong>{{ stats.confirmed || 0 }}</strong>
          </div>
          <div>
            <span>误报</span>
            <strong>{{ stats.false_positive || 0 }}</strong>
          </div>
          <div>
            <span>不确定</span>
            <strong>{{ stats.unsure || 0 }}</strong>
          </div>
        </div>

        <div v-if="loadingTasks" class="empty-card">正在加载任务...</div>
        <div v-else-if="tasks.length === 0" class="empty-card">
          暂无检测历史。请先在「图片检测」中完成一次检测。
        </div>

        <div v-else class="task-list">
          <button
            v-for="task in tasks"
            :key="task.history_id"
            type="button"
            class="task-item"
            :class="{ active: selectedHistoryId === task.history_id }"
            @click="openTask(task.history_id)"
          >
            <div class="task-title-row">
              <strong>{{ task.title }}</strong>
              <span class="status-pill" :class="task.status">
                {{ statusText(task.status) }}
              </span>
            </div>
            <p>{{ task.summary || '无摘要' }}</p>
            <div class="task-meta">
              <span>{{ task.reviewed_count }}/{{ task.total_defects }} 已复核</span>
              <span>{{ task.detect_mode }}</span>
            </div>
          </button>
        </div>
      </aside>

      <section class="work-panel">
        <div v-if="!selectedHistoryId" class="empty-card large">
          <strong>选择左侧检测任务开始复核</strong>
          <p>系统会列出该次检测中的每个缺陷框，供你确认或标记误报。</p>
        </div>

        <template v-else>
          <div class="panel-header">
            <div>
              <h2>{{ detail?.title || `任务 #${selectedHistoryId}` }}</h2>
              <p>
                进度：{{ detailStats.reviewed || 0 }}/{{ detailStats.total || 0 }}
                · 确认 {{ detailStats.confirmed || 0 }}
                · 误报 {{ detailStats.false_positive || 0 }}
              </p>
            </div>

            <div class="header-actions">
              <button
                class="ghost-btn"
                @click="$router.push(`/detection?task_id=${selectedHistoryId}`)"
              >
                查看原检测
              </button>
              <button
                class="primary-btn"
                :disabled="saving || !hasDraftChanges"
                @click="handleSave"
              >
                {{ saving ? '保存中...' : '保存复核' }}
              </button>
            </div>
          </div>

          <div v-if="loadingDetail" class="empty-card">正在加载缺陷列表...</div>

          <div v-else-if="items.length === 0" class="empty-card">
            该任务没有可复核的缺陷框（可能未检测到目标）。
          </div>

          <div v-else class="review-layout">
            <div class="preview-card">
              <h3>标注预览</h3>
              <img
                v-if="currentPreview"
                :src="currentPreview"
                alt="annotated preview"
              />
              <div v-else class="preview-empty">当前缺陷没有预览图</div>
              <p class="preview-caption">
                {{ currentItem?.source_label || '-' }}
                ·
                {{ currentItem?.class_name || '-' }}
              </p>
            </div>

            <div class="items-card">
              <div
                v-for="(item, index) in items"
                :key="item.detection_index"
                class="defect-item"
                :class="{
                  active: activeIndex === index,
                  reviewed: !!drafts[item.detection_index]?.verdict,
                }"
                @click="activeIndex = index"
              >
                <div class="defect-head">
                  <strong>#{{ item.detection_index + 1 }} {{ item.class_name }}</strong>
                  <span>{{ formatConfidence(item.confidence) }}</span>
                </div>

                <div class="verdict-row">
                  <label
                    v-for="option in verdictOptions"
                    :key="option.value"
                    class="verdict-option"
                    :class="{ selected: drafts[item.detection_index]?.verdict === option.value }"
                  >
                    <input
                      type="radio"
                      :name="`verdict-${item.detection_index}`"
                      :value="option.value"
                      v-model="drafts[item.detection_index].verdict"
                    />
                    {{ option.label }}
                  </label>
                </div>

                <textarea
                  v-model="drafts[item.detection_index].comment"
                  class="comment-input"
                  rows="2"
                  placeholder="备注（可选）：例如光照反光、焊盘边缘误判..."
                />
              </div>
            </div>
          </div>
        </template>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import {
  getReviewStats,
  getReviewTaskDetail,
  getReviewTasks,
  saveReviewItems,
} from '@/api/review'

const route = useRoute()
const router = useRouter()

const verdictOptions = [
  { value: 'confirmed', label: '确认缺陷' },
  { value: 'false_positive', label: '误报' },
  { value: 'unsure', label: '不确定' },
]

const loadingTasks = ref(false)
const loadingDetail = ref(false)
const saving = ref(false)
const tasks = ref([])
const stats = ref(null)
const selectedHistoryId = ref(null)
const detail = ref(null)
const items = ref([])
const drafts = reactive({})
const activeIndex = ref(0)
const savedSnapshot = ref('')

const detailStats = computed(() => detail.value?.stats || {})

const currentItem = computed(() => items.value[activeIndex.value] || null)

const currentPreview = computed(() => currentItem.value?.preview_base64 || '')

const hasDraftChanges = computed(() => {
  return JSON.stringify(buildSaveItems()) !== savedSnapshot.value
})

function statusText(status) {
  const map = {
    pending: '待复核',
    partial: '部分完成',
    done: '已完成',
  }
  return map[status] || status
}

function formatConfidence(value) {
  const numberValue = Number(value)
  if (Number.isNaN(numberValue)) {
    return '-'
  }
  return `${(numberValue * 100).toFixed(1)}%`
}

function buildSaveItems() {
  return items.value
    .filter(item => drafts[item.detection_index]?.verdict)
    .map(item => ({
      detection_index: item.detection_index,
      verdict: drafts[item.detection_index].verdict,
      comment: drafts[item.detection_index].comment || '',
      class_name: item.class_name,
      confidence: item.confidence,
      bbox: item.bbox,
      source_label: item.source_label,
    }))
}

function resetDrafts(list) {
  Object.keys(drafts).forEach(key => {
    delete drafts[key]
  })

  list.forEach(item => {
    drafts[item.detection_index] = {
      verdict: item.verdict || '',
      comment: item.comment || '',
    }
  })

  savedSnapshot.value = JSON.stringify(buildSaveItems())
}

function unwrapData(res) {
  // request.js already returns response.data = { code, message, data }
  const payload = res?.data !== undefined ? res : { data: res }
  const data = payload?.data
  return data !== undefined ? data : payload
}

async function loadTasks() {
  loadingTasks.value = true
  try {
    const [taskRes, statsRes] = await Promise.all([
      getReviewTasks({ limit: 50 }),
      getReviewStats(),
    ])

    const taskData = unwrapData(taskRes)
    tasks.value = Array.isArray(taskData) ? taskData : []

    const statsData = unwrapData(statsRes)
    stats.value = statsData && !Array.isArray(statsData) ? statsData : null
  } catch (error) {
    console.error(error)
    ElMessage.error('加载复核任务失败')
  } finally {
    loadingTasks.value = false
  }
}

async function openTask(historyId) {
  selectedHistoryId.value = Number(historyId)
  activeIndex.value = 0

  if (String(route.query.task_id || '') !== String(historyId)) {
    router.replace({ path: '/review', query: { task_id: historyId } })
  }

  loadingDetail.value = true
  try {
    const res = await getReviewTaskDetail(historyId)
    const data = unwrapData(res) || {}

    detail.value = data
    items.value = Array.isArray(data.items) ? data.items : []
    resetDrafts(items.value)
  } catch (error) {
    console.error(error)
    ElMessage.error('加载复核详情失败')
    detail.value = null
    items.value = []
  } finally {
    loadingDetail.value = false
  }
}

async function handleSave() {
  const payloadItems = buildSaveItems()

  if (payloadItems.length === 0) {
    ElMessage.warning('请至少选择一个缺陷的复核结果')
    return
  }

  saving.value = true
  try {
    await saveReviewItems(selectedHistoryId.value, payloadItems)
    ElMessage.success('复核结果已保存')
    await Promise.all([loadTasks(), openTask(selectedHistoryId.value)])
  } catch (error) {
    console.error(error)
    ElMessage.error('保存失败，请查看后端日志')
  } finally {
    saving.value = false
  }
}

watch(
  () => route.query.task_id,
  value => {
    if (value && Number(value) !== selectedHistoryId.value) {
      openTask(value)
    }
  },
)

onMounted(async () => {
  await loadTasks()

  if (route.query.task_id) {
    await openTask(route.query.task_id)
  } else if (tasks.value.length > 0) {
    const pending = tasks.value.find(item => item.status !== 'done') || tasks.value[0]
    await openTask(pending.history_id)
  }
})
</script>

<style scoped>
.review-page {
  width: 100%;
}

.page-grid {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  gap: 20px;
}

.task-panel,
.work-panel {
  border: 1px solid #e5e7eb;
  background: #ffffff;
  border-radius: 18px;
  padding: 18px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  margin-bottom: 14px;
}

.panel-header h2 {
  margin: 0;
  font-size: 20px;
  color: #111827;
}

.panel-header p {
  margin: 6px 0 0;
  color: #6b7280;
  font-size: 13px;
  line-height: 1.6;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin-bottom: 14px;
}

.stats-row div {
  border: 1px solid #e5e7eb;
  background: #f9fafb;
  border-radius: 12px;
  padding: 10px;
}

.stats-row span {
  display: block;
  color: #6b7280;
  font-size: 11px;
}

.stats-row strong {
  display: block;
  margin-top: 4px;
  color: #111827;
}

.task-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: calc(100vh - 280px);
  overflow: auto;
}

.task-item {
  text-align: left;
  border: 1px solid #e5e7eb;
  background: #ffffff;
  border-radius: 14px;
  padding: 12px;
  cursor: pointer;
}

.task-item.active {
  border-color: #111827;
  background: #f9fafb;
}

.task-title-row {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  align-items: center;
}

.task-title-row strong {
  color: #111827;
  font-size: 14px;
}

.task-item p {
  margin: 8px 0 0;
  color: #6b7280;
  font-size: 12px;
  line-height: 1.5;
}

.task-meta {
  margin-top: 8px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  color: #9ca3af;
  font-size: 12px;
}

.status-pill {
  height: 22px;
  border-radius: 999px;
  padding: 0 8px;
  display: inline-flex;
  align-items: center;
  font-size: 11px;
  background: #f3f4f6;
  color: #374151;
  flex-shrink: 0;
}

.status-pill.pending {
  background: #fff7ed;
  color: #c2410c;
}

.status-pill.partial {
  background: #eff6ff;
  color: #1d4ed8;
}

.status-pill.done {
  background: #dcfce7;
  color: #166534;
}

.empty-card {
  border: 1px solid #e5e7eb;
  background: #f9fafb;
  border-radius: 14px;
  padding: 16px;
  color: #6b7280;
  font-size: 13px;
}

.empty-card.large strong {
  display: block;
  color: #111827;
  margin-bottom: 8px;
}

.header-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.ghost-btn,
.primary-btn {
  height: 36px;
  border-radius: 999px;
  padding: 0 16px;
  cursor: pointer;
  border: none;
}

.ghost-btn {
  background: #f3f4f6;
  color: #374151;
}

.primary-btn {
  background: #111827;
  color: #ffffff;
}

.primary-btn:disabled,
.ghost-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.review-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(320px, 420px);
  gap: 16px;
}

.preview-card,
.items-card {
  border: 1px solid #e5e7eb;
  border-radius: 16px;
  padding: 14px;
  background: #ffffff;
}

.preview-card h3 {
  margin: 0 0 10px;
  color: #111827;
  font-size: 15px;
}

.preview-card img {
  width: 100%;
  display: block;
  border-radius: 12px;
  background: #f9fafb;
}

.preview-empty {
  min-height: 220px;
  border-radius: 12px;
  background: #f9fafb;
  color: #9ca3af;
  display: flex;
  align-items: center;
  justify-content: center;
}

.preview-caption {
  margin: 10px 0 0;
  color: #6b7280;
  font-size: 12px;
}

.items-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: calc(100vh - 260px);
  overflow: auto;
}

.defect-item {
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  padding: 12px;
  cursor: pointer;
}

.defect-item.active {
  border-color: #111827;
}

.defect-item.reviewed {
  background: #f9fafb;
}

.defect-head {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 10px;
  color: #111827;
  font-size: 13px;
}

.verdict-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
}

.verdict-option {
  height: 30px;
  border: 1px solid #e5e7eb;
  border-radius: 999px;
  padding: 0 12px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #374151;
  cursor: pointer;
}

.verdict-option.selected {
  background: #111827;
  border-color: #111827;
  color: #ffffff;
}

.verdict-option input {
  display: none;
}

.comment-input {
  width: 100%;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 8px 10px;
  resize: vertical;
  font: inherit;
  color: #111827;
  outline: none;
}

@media (max-width: 1100px) {
  .page-grid,
  .review-layout {
    grid-template-columns: 1fr;
  }

  .task-list,
  .items-card {
    max-height: none;
  }
}
</style>
