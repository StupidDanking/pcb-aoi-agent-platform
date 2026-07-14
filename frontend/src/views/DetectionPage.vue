<template>
  <div class="detection-page">
    <div class="page-grid">
      <section class="upload-card">
        <div class="card-header">
          <div>
            <h2>PCB 图片检测</h2>
            <p>上传 PCB 图片，选择模型版本并进行缺陷检测。</p>
          </div>

          <div class="model-select-wrap">
            <span>模型版本</span>

            <select
              v-model="modelVersion"
              class="model-select"
              :disabled="modelLoading || detecting"
              @change="handleModelVersionChange"
            >
              <option
                v-for="model in modelOptions"
                :key="model.name"
                :value="model.name"
              >
                {{ model.name }}{{ model.is_default ? '（当前）' : '' }}
              </option>
            </select>
          </div>
        </div>

        <div v-if="activeModelInfo" class="active-model-tip">
          当前检测模型：
          <strong>{{ activeModelInfo.model_name }}</strong>
        </div>

        <label class="upload-box">
          <input
            type="file"
            accept="image/*"
            @change="handleFileChange"
          />

          <template v-if="previewUrl">
            <img :src="previewUrl" alt="preview" />
          </template>

          <template v-else>
            <div class="upload-icon">▧</div>
            <h3>选择一张 PCB 图片</h3>
            <p>支持 jpg、png、jpeg 等常见格式。</p>
          </template>
        </label>

        <div v-if="selectedFile" class="file-info">
          当前文件：{{ selectedFile.name }}
        </div>

        <div class="control-row">
          <label>
            置信度阈值：
            <input
              v-model.number="conf"
              type="number"
              min="0.01"
              max="1"
              step="0.01"
            />
          </label>

          <label>
            IoU 阈值：
            <input
              v-model.number="iou"
              type="number"
              min="0.01"
              max="1"
              step="0.01"
            />
          </label>

          <button
            class="detect-btn"
            :disabled="!selectedFile || detecting"
            @click="handleDetect"
          >
            {{ detecting ? '检测中...' : '开始检测' }}
          </button>
        </div>
      </section>

      <section class="result-panel">
        <div class="panel-header">
          <div>
            <h2>检测结果</h2>
            <p>
              检测完成后会自动写入历史记录，并显示在左侧 Recents。
            </p>
          </div>

          <button
            v-if="historyId"
            class="history-pill"
          >
            历史任务 ID：{{ historyId }}
          </button>
        </div>

        <div v-if="loadingHistory" class="empty-result">
          正在加载历史检测结果...
        </div>

        <div v-else-if="historyLoaded && !resultPayload" class="empty-result">
          <strong>这条历史记录没有完整检测结果。</strong>
          <p>
            旧记录只保存了标题和缺陷数量，没有保存 result_payload。
            请重新做一次检测，新记录就可以恢复完整结果。
          </p>
        </div>

        <DetectionResultCard
          v-else-if="resultPayload"
          :result="resultPayload"
          :mode="resultMode"
        />

        <div v-else class="empty-result">
          <strong>未检测到明显 PCB 缺陷。</strong>
          <p>请在左侧上传图片并点击“开始检测”。</p>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'

import DetectionResultCard from '@/components/DetectionResultCard.vue'
import { detectSingleImage } from '@/api/detection'
import {
  createDetectionTaskHistory,
  getDetectionTaskDetail,
} from '@/api/history'
import {
  getModelVersions,
  getActiveModel,
  setActiveModel,
} from '@/api/models'

const route = useRoute()

const selectedFile = ref(null)
const previewUrl = ref('')
const conf = ref(0.25)
const iou = ref(0.45)

const modelVersion = ref('pcb_aoi_v1.0.0')
const modelOptions = ref([])
const modelLoading = ref(false)
const activeModelInfo = ref(null)

const detecting = ref(false)
const loadingHistory = ref(false)
const historyLoaded = ref(false)
const historyId = ref(null)
const resultPayload = ref(null)

const resultMode = computed(() => {
  if (!resultPayload.value) {
    return 'single'
  }

  if (resultPayload.value.type === 'video' || resultPayload.value.key_frames) {
    return 'video'
  }

  if (resultPayload.value.zip_name || resultPayload.value.type === 'zip') {
    return 'zip'
  }

  if (resultPayload.value.results || resultPayload.value.type === 'batch') {
    return 'batch'
  }

  return 'single'
})

async function loadModelOptions() {
  modelLoading.value = true

  try {
    const res = await getModelVersions()
    const payload = res?.data || res || {}
    const data = payload.data || payload

    modelOptions.value = Array.isArray(data) ? data : []

    const activeModel = modelOptions.value.find(item => item.is_default)

    if (activeModel) {
      modelVersion.value = activeModel.name
    } else if (modelOptions.value.length > 0) {
      modelVersion.value = modelOptions.value[0].name
    }

    await loadActiveModel()
  } catch (error) {
    console.error('加载模型版本失败:', error)

    modelOptions.value = [
      {
        name: 'pcb_aoi_v1.0.0',
        display_name: 'pcb_aoi_v1.0.0',
        is_default: true,
      },
    ]

    modelVersion.value = 'pcb_aoi_v1.0.0'
  } finally {
    modelLoading.value = false
  }
}

async function loadActiveModel() {
  try {
    const res = await getActiveModel()
    const payload = res?.data || res || {}
    const data = payload.data || payload

    activeModelInfo.value = data || null

    if (data?.model_name) {
      modelVersion.value = data.model_name
    }
  } catch (error) {
    console.error('获取当前模型失败:', error)
    activeModelInfo.value = null
  }
}

async function handleModelVersionChange() {
  if (!modelVersion.value) {
    return
  }

  try {
    await setActiveModel(modelVersion.value)
    await loadModelOptions()

    ElMessage.success(`当前检测模型已切换为 ${modelVersion.value}`)
  } catch (error) {
    console.error('切换模型版本失败:', error)
    ElMessage.error('切换模型版本失败，请查看后端日志')
  }
}

function handleFileChange(event) {
  const file = event.target.files?.[0]

  if (!file) {
    return
  }

  selectedFile.value = file

  if (previewUrl.value) {
    URL.revokeObjectURL(previewUrl.value)
  }

  previewUrl.value = URL.createObjectURL(file)

  resultPayload.value = null
  historyLoaded.value = false
  historyId.value = null

  event.target.value = ''
}

function getResultCount(result) {
  if (!result) {
    return 0
  }

  if (result.total_objects !== undefined) {
    return result.total_objects
  }

  if (Array.isArray(result.detections)) {
    return result.detections.length
  }

  return 0
}

function buildSummary(result) {
  const total = result?.total_objects || 0
  const stats = result?.class_stats || []

  if (total === 0) {
    return '未检测到明显 PCB 缺陷。'
  }

  const statsText = stats
    .map(item => `${item.class_name} × ${item.count}`)
    .join('，')

  return `检测到 ${total} 个疑似缺陷。${statsText}`
}

async function handleDetect() {
  if (!selectedFile.value || detecting.value) {
    return
  }

  detecting.value = true

  try {
    /*
      这里不需要把 modelVersion 放到检测接口里。
      因为 handleModelVersionChange 已经调用 /api/models/active，
      后端 DetectionService 会自动读取 active_model.json。
    */
    const formData = new FormData()
    formData.append('file', selectedFile.value)
    formData.append('conf', String(conf.value))
    formData.append('iou', String(iou.value))
    formData.append('device', '0')

    const res = await detectSingleImage(formData)
    const payload = res?.data || res || {}
    const result = payload.data || payload

    resultPayload.value = result
    historyLoaded.value = false

    const historyRes = await createDetectionTaskHistory({
      title: selectedFile.value.name,
      image_name: selectedFile.value.name,
      model_version: modelVersion.value,
      status: 'completed',
      result_count: getResultCount(result),
      summary: buildSummary(result),
      result_payload: {
        ...result,
        model_version: modelVersion.value,
      },
    })

    const historyPayload = historyRes?.data || historyRes || {}
    const raw = historyPayload.data || historyPayload

    historyId.value = raw.task_id || raw.id || null

    window.dispatchEvent(new Event('history-updated'))

    ElMessage.success('检测完成，已保存到历史记录')
  } catch (error) {
    console.error('检测失败:', error)
    ElMessage.error('检测失败，请查看后端日志')
  } finally {
    detecting.value = false
  }
}

async function loadHistoryDetection(taskId) {
  if (!taskId) {
    return
  }

  loadingHistory.value = true
  historyLoaded.value = false
  historyId.value = taskId
  selectedFile.value = null

  if (previewUrl.value) {
    URL.revokeObjectURL(previewUrl.value)
    previewUrl.value = ''
  }

  try {
    const res = await getDetectionTaskDetail(taskId)
    const payload = res?.data || res || {}
    const raw = payload.data || payload

    resultPayload.value = raw.result_payload || null
    historyLoaded.value = true

    if (!resultPayload.value) {
      console.warn('该历史记录没有 result_payload，无法恢复完整检测结果')
    }
  } catch (error) {
    console.error('加载检测历史失败:', error)
    ElMessage.error('加载检测历史失败')
    resultPayload.value = null
    historyLoaded.value = true
  } finally {
    loadingHistory.value = false
  }
}

watch(
  () => route.query.task_id,
  value => {
    if (value) {
      loadHistoryDetection(value)
    }
  },
)

onMounted(() => {
  loadModelOptions()

  if (route.query.task_id) {
    loadHistoryDetection(route.query.task_id)
  }
})
</script>

<style scoped>
.detection-page {
  width: 100%;
}

.page-grid {
  display: grid;
  grid-template-columns: 460px minmax(0, 1fr);
  gap: 20px;
}

.upload-card,
.result-panel {
  border: 1px solid #e5e7eb;
  background: #ffffff;
  border-radius: 18px;
  padding: 20px;
}

.card-header,
.panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 14px;
}

.card-header h2,
.panel-header h2 {
  margin: 0;
  color: #111827;
  font-size: 20px;
}

.card-header p,
.panel-header p {
  margin: 6px 0 0;
  color: #6b7280;
  font-size: 13px;
  line-height: 1.6;
}

.model-select-wrap {
  min-width: 150px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.model-select-wrap span {
  color: #6b7280;
  font-size: 12px;
}

.model-select {
  height: 34px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #ffffff;
  padding: 0 10px;
  outline: none;
  color: #111827;
  min-width: 150px;
}

.active-model-tip {
  border: 1px solid #bfdbfe;
  background: #eff6ff;
  color: #1d4ed8;
  border-radius: 12px;
  padding: 9px 12px;
  margin-bottom: 14px;
  font-size: 13px;
}

.active-model-tip strong {
  color: #111827;
}

.upload-box {
  height: 280px;
  border: 1px dashed #d1d5db;
  background: #f9fafb;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  flex-direction: column;
  cursor: pointer;
  overflow: hidden;
}

.upload-box input {
  display: none;
}

.upload-box img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  background: #ffffff;
}

.upload-icon {
  width: 46px;
  height: 46px;
  border-radius: 16px;
  background: #111827;
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
}

.upload-box h3 {
  margin: 0;
  color: #111827;
  font-size: 16px;
}

.upload-box p {
  margin: 8px 0 0;
  color: #9ca3af;
  font-size: 13px;
}

.file-info {
  margin-top: 12px;
  color: #374151;
  font-size: 13px;
  word-break: break-all;
}

.control-row {
  margin-top: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.control-row label {
  color: #374151;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.control-row input {
  width: 76px;
  height: 34px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 0 10px;
  outline: none;
}

.detect-btn {
  margin-left: auto;
  height: 38px;
  border: none;
  border-radius: 999px;
  background: #111827;
  color: #ffffff;
  padding: 0 20px;
  cursor: pointer;
}

.detect-btn:disabled {
  background: #d1d5db;
  cursor: not-allowed;
}

.history-pill {
  border: none;
  border-radius: 999px;
  background: #f3f4f6;
  color: #374151;
  height: 32px;
  padding: 0 12px;
  font-size: 13px;
}

.empty-result {
  border: 1px solid #e5e7eb;
  background: #f9fafb;
  border-radius: 14px;
  padding: 18px;
  color: #6b7280;
  font-size: 14px;
}

.empty-result strong {
  display: block;
  color: #111827;
  margin-bottom: 8px;
}

.empty-result p {
  margin: 0;
  line-height: 1.8;
}

@media (max-width: 1100px) {
  .page-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 700px) {
  .card-header,
  .panel-header {
    flex-direction: column;
  }

  .model-select-wrap,
  .model-select {
    width: 100%;
  }

  .detect-btn {
    margin-left: 0;
    width: 100%;
  }
}
</style>