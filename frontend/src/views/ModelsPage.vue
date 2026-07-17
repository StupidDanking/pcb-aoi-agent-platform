<template>
  <div class="models-page">
    <div class="page-header">
      <div>
        <h1>模型版本管理</h1>
        <p>管理 PCB AOI 检测模型版本、训练指标和评估图表。</p>
      </div>

      <button class="refresh-btn" :disabled="loading" @click="loadModels">
        {{ loading ? '刷新中...' : '刷新' }}
      </button>
    </div>

    <div v-if="loading" class="empty-box">
      正在加载模型版本...
    </div>

    <div v-else-if="models.length === 0" class="empty-box">
      暂未发现模型版本，请检查 backend/models 目录。
    </div>

    <template v-else>
      <div class="model-card-list">
        <div
          v-for="model in models"
          :key="model.name"
          class="model-card"
          :class="{ selected: selectedModel?.name === model.name }"
          @click="selectModel(model)"
        >
          <div class="model-card-header">
            <div class="model-title-area">
              <h2>{{ model.name }}</h2>
              <p>{{ model.display_name || model.version || model.name }}</p>
            </div>

            <span v-if="isActiveModel(model)" class="active-badge">
              当前使用中
            </span>
          </div>

          <div class="mini-metrics">
            <div class="mini-metric">
              <span>Precision</span>
              <strong>{{ formatPercent(model.precision) }}</strong>
            </div>
            <div class="mini-metric">
              <span>Recall</span>
              <strong>{{ formatPercent(model.recall) }}</strong>
            </div>
            <div class="mini-metric">
              <span>mAP50</span>
              <strong>{{ formatPercent(model.map50) }}</strong>
            </div>
            <div class="mini-metric">
              <span>mAP50-95</span>
              <strong>{{ formatPercent(model.map50_95) }}</strong>
            </div>
          </div>

          <div class="model-tags">
            <span>{{ model.model_type || 'YOLOv11' }}</span>
            <span>{{ model.epochs || '-' }} epochs</span>
            <span v-if="model.best_size_mb">{{ model.best_size_mb }} MB</span>
          </div>
        </div>
      </div>

      <div v-if="selectedModel" class="detail-section">
        <div class="detail-header">
          <div>
            <h2>{{ selectedModel.name }}</h2>
            <p>{{ selectedModel.description || '暂无描述' }}</p>
          </div>

          <button
            class="set-active-btn"
            :disabled="switching || isActiveModel(selectedModel)"
            @click="handleSetActive"
          >
            {{ isActiveModel(selectedModel) ? '当前检测模型' : '设为当前检测模型' }}
          </button>
        </div>

        <div class="info-tip">
          当前检测接口会自动使用标记为“当前使用中”的模型版本。
        </div>

        <div class="metrics-row">
          <div class="metric-panel metric-panel-score">
            <h3>最终评估指标</h3>

            <div class="compact-table">
              <div class="compact-row">
                <span>Precision</span>
                <strong>{{ formatPercent(selectedModel.precision) }}</strong>
              </div>
              <div class="compact-row">
                <span>Recall</span>
                <strong>{{ formatPercent(selectedModel.recall) }}</strong>
              </div>
              <div class="compact-row">
                <span>mAP50</span>
                <strong>{{ formatPercent(selectedModel.map50) }}</strong>
              </div>
              <div class="compact-row">
                <span>mAP50-95</span>
                <strong>{{ formatPercent(selectedModel.map50_95) }}</strong>
              </div>
            </div>
          </div>

          <div class="metric-panel metric-panel-loss">
            <h3>Loss</h3>

            <div class="compact-table">
              <div
                v-for="row in lossRows"
                :key="row.label"
                class="compact-row"
              >
                <span>{{ row.label }}</span>
                <strong>{{ row.value }}</strong>
              </div>
            </div>
          </div>
        </div>

        <div class="charts-section">
          <h3>训练与评估图表</h3>

          <div class="artifact-grid">
            <div
              v-for="chart in charts"
              :key="chart.filename"
              class="artifact-card"
              :class="{ wide: chart.wide }"
            >
              <div class="artifact-title">
                {{ chart.title }}
              </div>

              <div class="artifact-image-wrap">
                <img
                  v-if="artifactUrls[chart.filename]"
                  :src="artifactUrls[chart.filename]"
                  :alt="chart.title"
                  class="artifact-img"
                  @click="openPreview(chart)"
                />
                <div v-else class="artifact-missing">
                  {{ artifactsLoading ? '图表加载中...' : '图表加载失败或文件不存在' }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>

    <div
      v-if="previewVisible"
      class="preview-mask"
      @click="previewVisible = false"
    >
      <div class="preview-panel" @click.stop>
        <div class="preview-header">
          <strong>{{ previewTitle }}</strong>
          <button @click="previewVisible = false">关闭</button>
        </div>

        <img :src="previewImage" class="preview-img" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import {
  getModelVersions,
  getActiveModel,
  setActiveModel,
  fetchModelArtifactObjectUrl
} from '@/api/models'

const loading = ref(false)
const switching = ref(false)
const artifactsLoading = ref(false)
const models = ref([])
const selectedModel = ref(null)
const activeModelName = ref('')
const artifactUrls = ref({})

const previewVisible = ref(false)
const previewTitle = ref('')
const previewImage = ref('')

const charts = [
  {
    title: '训练曲线总览',
    filename: 'results.png',
    wide: true
  },
  {
    title: '混淆矩阵',
    filename: 'confusion_matrix.png',
    wide: false
  },
  {
    title: '归一化混淆矩阵',
    filename: 'confusion_matrix_normalized.png',
    wide: false
  },
  {
    title: 'PR 曲线',
    filename: 'BoxPR_curve.png',
    wide: false
  },
  {
    title: 'F1 曲线',
    filename: 'BoxF1_curve.png',
    wide: false
  },
  {
    title: 'Precision 曲线',
    filename: 'BoxP_curve.png',
    wide: false
  },
  {
    title: 'Recall 曲线',
    filename: 'BoxR_curve.png',
    wide: false
  }
]

const lossRows = computed(() => {
  if (!selectedModel.value) return []

  const model = selectedModel.value

  return [
    ['train box loss', model.train_box_loss],
    ['train cls loss', model.train_cls_loss],
    ['train dfl loss', model.train_dfl_loss],
    ['val box loss', model.val_box_loss],
    ['val cls loss', model.val_cls_loss],
    ['val dfl loss', model.val_dfl_loss]
  ]
    .filter((item) => item[1] !== undefined && item[1] !== null && item[1] !== '')
    .map(([label, value]) => ({
      label,
      value: Number(value).toFixed(4)
    }))
})

const normalizeModelsResponse = (res) => {
  if (Array.isArray(res)) return res
  if (Array.isArray(res?.data)) return res.data
  if (Array.isArray(res?.models)) return res.models
  if (Array.isArray(res?.data?.models)) return res.data.models
  if (Array.isArray(res?.data?.data)) return res.data.data
  return []
}

const normalizeActiveResponse = (res) => {
  return (
    res?.model_name ||
    res?.active_model ||
    res?.data?.model_name ||
    res?.data?.active_model ||
    res?.data?.name ||
    ''
  )
}

const loadModels = async () => {
  loading.value = true

  try {
    const [modelRes, activeRes] = await Promise.all([
      getModelVersions(),
      getActiveModel().catch(() => null)
    ])

    const list = normalizeModelsResponse(modelRes)

    models.value = list.map((item) => ({
      ...item,
      name: item.name || item.model_name || `pcb_aoi_${item.version}`
    }))

    activeModelName.value = normalizeActiveResponse(activeRes)

    if (!selectedModel.value && models.value.length > 0) {
      selectedModel.value =
        models.value.find((item) => item.name === activeModelName.value) ||
        models.value[0]
    } else if (selectedModel.value) {
      const latest = models.value.find((item) => item.name === selectedModel.value.name)
      selectedModel.value = latest || models.value[0] || null
    }

    await loadArtifacts(selectedModel.value)
  } catch (error) {
    console.error('加载模型列表失败:', error)
  } finally {
    loading.value = false
  }
}

const selectModel = (model) => {
  selectedModel.value = model
  loadArtifacts(model)
}

const isActiveModel = (model) => {
  if (!model) return false
  return model.name === activeModelName.value
}

const handleSetActive = async () => {
  if (!selectedModel.value) return

  switching.value = true

  try {
    await setActiveModel(selectedModel.value.name)
    activeModelName.value = selectedModel.value.name
  } catch (error) {
    console.error('设置当前模型失败:', error)
  } finally {
    switching.value = false
  }
}

const formatPercent = (value) => {
  if (value === undefined || value === null || value === '') return '-'

  const num = Number(value)
  if (Number.isNaN(num)) return '-'

  const percent = num <= 1 ? num * 100 : num
  return `${percent.toFixed(2)}%`
}

function revokeArtifactUrls() {
  Object.values(artifactUrls.value).forEach((url) => {
    if (url) {
      URL.revokeObjectURL(url)
    }
  })
  artifactUrls.value = {}
}

async function loadArtifacts(model) {
  revokeArtifactUrls()

  if (!model?.name) {
    return
  }

  artifactsLoading.value = true
  const nextUrls = {}

  try {
    await Promise.all(
      charts.map(async (item) => {
        try {
          nextUrls[item.filename] = await fetchModelArtifactObjectUrl(
            model.name,
            item.filename
          )
        } catch (error) {
          console.warn(`加载图表失败: ${item.filename}`, error)
          nextUrls[item.filename] = ''
        }
      })
    )

    artifactUrls.value = nextUrls
  } finally {
    artifactsLoading.value = false
  }
}

const openPreview = (chart) => {
  const url = artifactUrls.value[chart.filename]
  if (!url) return

  previewTitle.value = chart.title
  previewImage.value = url
  previewVisible.value = true
}

onMounted(() => {
  loadModels()
})

onBeforeUnmount(() => {
  revokeArtifactUrls()
})
</script>

<style scoped>
.models-page {
  min-height: 100%;
  padding: 24px 28px 48px;
  background: #ffffff;
  color: #0f172a;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 24px;
}

.page-header h1 {
  margin: 0 0 6px;
  font-size: 26px;
  font-weight: 800;
  color: #0f172a;
}

.page-header p {
  margin: 0;
  font-size: 14px;
  color: #64748b;
}

.refresh-btn,
.set-active-btn {
  border: none;
  border-radius: 999px;
  background: #0f172a;
  color: #ffffff;
  padding: 10px 18px;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  transition: 0.2s ease;
  white-space: nowrap;
}

.refresh-btn:hover,
.set-active-btn:hover {
  background: #1e293b;
}

.refresh-btn:disabled,
.set-active-btn:disabled {
  background: #d1d5db;
  cursor: not-allowed;
}

.empty-box {
  padding: 48px;
  border: 1px solid #e5e7eb;
  border-radius: 18px;
  color: #64748b;
  background: #f8fafc;
  text-align: center;
}

.model-card-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(430px, 1fr));
  gap: 18px;
  margin-bottom: 28px;
}

.model-card {
  min-width: 0;
  border: 1px solid #e5e7eb;
  border-radius: 18px;
  padding: 18px;
  background: #ffffff;
  cursor: pointer;
  transition: 0.2s ease;
  box-sizing: border-box;
}

.model-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
}

.model-card.selected {
  border-color: #0f172a;
  box-shadow: 0 0 0 1px #0f172a;
}

.model-card-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.model-title-area {
  min-width: 0;
}

.model-card-header h2 {
  margin: 0 0 4px;
  font-size: 19px;
  font-weight: 800;
  word-break: break-word;
}

.model-card-header p {
  margin: 0;
  font-size: 13px;
  color: #64748b;
  word-break: break-word;
}

.active-badge {
  height: 24px;
  padding: 0 12px;
  display: inline-flex;
  align-items: center;
  flex-shrink: 0;
  border-radius: 999px;
  background: #dcfce7;
  color: #15803d;
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
}

.mini-metrics {
  width: 100%;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.mini-metric {
  min-width: 0;
  box-sizing: border-box;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 10px 8px;
  background: #f8fafc;
  overflow: hidden;
}

.mini-metric span {
  display: block;
  margin-bottom: 5px;
  font-size: 11px;
  line-height: 1.2;
  color: #64748b;
  white-space: nowrap;
}

.mini-metric strong {
  display: block;
  font-size: 15px;
  line-height: 1.2;
  font-weight: 800;
  color: #0f172a;
  white-space: nowrap;
}

.model-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 14px;
}

.model-tags span {
  padding: 5px 10px;
  border-radius: 999px;
  background: #f1f5f9;
  color: #475569;
  font-size: 12px;
  font-weight: 600;
}

.detail-section {
  border-top: 1px solid #e5e7eb;
  padding-top: 24px;
}

.detail-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 16px;
}

.detail-header h2 {
  margin: 0 0 6px;
  font-size: 24px;
  font-weight: 800;
}

.detail-header p {
  margin: 0;
  color: #64748b;
  font-size: 14px;
}

.info-tip {
  margin-bottom: 18px;
  padding: 12px 16px;
  border: 1px solid #bfdbfe;
  border-radius: 12px;
  background: #eff6ff;
  color: #2563eb;
  font-size: 13px;
}

.metrics-row {
  display: grid;
  grid-template-columns: 520px 520px;
  justify-content: start;
  align-items: stretch;
  gap: 20px;
  margin-bottom: 28px;
}

.metric-panel {
  border: 1px solid #e5e7eb;
  border-radius: 18px;
  background: #ffffff;
  padding: 22px 24px;
  min-height: 280px;
  box-sizing: border-box;
}

.metric-panel h3 {
  margin: 0 0 18px;
  font-size: 20px;
  font-weight: 800;
}

.compact-table {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.compact-row {
  display: grid;
  grid-template-columns: 150px 110px;
  justify-content: start;
  align-items: center;
  column-gap: 18px;
  min-height: 38px;
  border-bottom: 1px solid #e5e7eb;
}

.metric-panel-score .compact-row {
  min-height: 48px;
}

.metric-panel-loss .compact-row {
  min-height: 38px;
}

.compact-row:last-child {
  border-bottom: none;
}

.compact-row span {
  color: #475569;
  font-size: 16px;
}

.compact-row strong {
  color: #0f172a;
  font-size: 17px;
  font-weight: 800;
  text-align: left;
}

.charts-section {
  margin-top: 8px;
}

.charts-section h3 {
  margin: 0 0 18px;
  font-size: 18px;
  font-weight: 800;
}

.artifact-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(520px, 1fr));
  gap: 22px;
}

.artifact-card {
  border: 1px solid #e5e7eb;
  border-radius: 18px;
  padding: 16px;
  background: #ffffff;
}

.artifact-card.wide {
  grid-column: span 2;
}

.artifact-title {
  margin-bottom: 12px;
  font-size: 15px;
  font-weight: 800;
  color: #0f172a;
}

.artifact-missing {
  padding: 24px;
  color: #64748b;
  font-size: 14px;
  text-align: center;
}

.artifact-image-wrap {
  width: 100%;
  min-height: 360px;
  border-radius: 14px;
  background: #f8fafc;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.artifact-img {
  width: 100%;
  height: 420px;
  object-fit: contain;
  cursor: zoom-in;
  display: block;
}

.artifact-card.wide .artifact-image-wrap {
  min-height: 520px;
}

.artifact-card.wide .artifact-img {
  height: 540px;
}

.preview-mask {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: rgba(15, 23, 42, 0.72);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 36px;
}

.preview-panel {
  width: min(1280px, 96vw);
  max-height: 92vh;
  background: #ffffff;
  border-radius: 20px;
  padding: 18px;
  overflow: auto;
}

.preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}

.preview-header strong {
  font-size: 18px;
}

.preview-header button {
  border: none;
  border-radius: 999px;
  background: #0f172a;
  color: #ffffff;
  padding: 8px 16px;
  cursor: pointer;
}

.preview-img {
  width: 100%;
  max-height: 78vh;
  object-fit: contain;
  display: block;
}

@media (max-width: 1200px) {
  .metrics-row {
    grid-template-columns: 520px 520px;
    overflow-x: auto;
  }

  .artifact-grid {
    grid-template-columns: 1fr;
  }

  .artifact-card.wide {
    grid-column: span 1;
  }

  .artifact-img,
  .artifact-card.wide .artifact-img {
    height: 360px;
  }

  .artifact-card.wide .artifact-image-wrap {
    min-height: 380px;
  }
}

@media (max-width: 720px) {
  .models-page {
    padding: 18px;
  }

  .page-header,
  .detail-header {
    flex-direction: column;
  }

  .model-card-list {
    grid-template-columns: 1fr;
  }

  .mini-metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .metrics-row {
    grid-template-columns: 1fr;
    overflow-x: visible;
  }

  .compact-row {
    grid-template-columns: 130px 100px;
    column-gap: 14px;
  }

  .metric-panel-score .compact-row,
  .metric-panel-loss .compact-row {
    min-height: 42px;
  }

  .artifact-img,
  .artifact-card.wide .artifact-img {
    height: 280px;
  }
}
</style>