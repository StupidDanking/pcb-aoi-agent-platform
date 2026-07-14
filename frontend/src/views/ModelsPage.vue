<template>
  <div class="models-page">
    <div class="page-header">
      <div>
        <h2>模型版本管理</h2>
        <p>管理 PCB AOI 检测模型版本、训练指标和评估图表。</p>
      </div>

      <button class="refresh-btn" @click="loadModels">
        刷新
      </button>
    </div>

    <div v-if="loading" class="empty-card">
      正在加载模型版本...
    </div>

    <div v-else-if="models.length === 0" class="empty-card">
      暂无模型版本。请检查 backend/models 目录。
    </div>

    <div v-else class="model-grid">
      <div
        v-for="model in models"
        :key="model.name"
        class="model-card"
        :class="{ active: selectedModel && selectedModel.name === model.name }"
        @click="selectModel(model)"
      >
        <div class="model-title-row">
          <div>
            <h3>{{ model.display_name }}</h3>
            <p>{{ model.name }}</p>
          </div>

          <span v-if="model.is_default" class="default-pill">
            当前使用中
          </span>
        </div>

        <div class="metric-mini-grid">
          <div>
            <span>Precision</span>
            <strong>{{ formatMetric(model.precision) }}</strong>
          </div>

          <div>
            <span>Recall</span>
            <strong>{{ formatMetric(model.recall) }}</strong>
          </div>

          <div>
            <span>mAP50</span>
            <strong>{{ formatMetric(model.map50) }}</strong>
          </div>

          <div>
            <span>mAP50-95</span>
            <strong>{{ formatMetric(model.map50_95) }}</strong>
          </div>
        </div>

        <div class="model-meta">
          <span>{{ model.model_type }}</span>
          <span>{{ model.epochs }} epochs</span>
          <span>{{ model.best_size_mb }} MB</span>
        </div>
      </div>
    </div>

    <section v-if="selectedModel" class="detail-section">
      <div class="section-header">
        <div>
          <h3>{{ selectedModel.display_name }}</h3>
          <p>{{ selectedModel.description || '暂无描述' }}</p>
        </div>

        <button
          class="set-default-btn"
          :disabled="selectedModel.is_default || settingActive"
          @click="handleSetActiveModel"
        >
          {{ selectedModel.is_default ? '当前检测模型' : settingActive ? '设置中...' : '设为当前检测模型' }}
        </button>
      </div>

      <div class="active-tip">
        当前检测接口会自动使用标记为“当前使用中”的模型版本。
      </div>

      <div class="detail-grid">
        <div class="detail-card">
          <h4>最终指标</h4>

          <table>
            <tbody>
              <tr>
                <td>Precision</td>
                <td>{{ formatMetric(selectedModel.precision) }}</td>
              </tr>
              <tr>
                <td>Recall</td>
                <td>{{ formatMetric(selectedModel.recall) }}</td>
              </tr>
              <tr>
                <td>mAP50</td>
                <td>{{ formatMetric(selectedModel.map50) }}</td>
              </tr>
              <tr>
                <td>mAP50-95</td>
                <td>{{ formatMetric(selectedModel.map50_95) }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="detail-card">
          <h4>Loss</h4>

          <table>
            <tbody>
              <tr>
                <td>train box loss</td>
                <td>{{ formatNumber(selectedModel.train_box_loss) }}</td>
              </tr>
              <tr>
                <td>train cls loss</td>
                <td>{{ formatNumber(selectedModel.train_cls_loss) }}</td>
              </tr>
              <tr>
                <td>train dfl loss</td>
                <td>{{ formatNumber(selectedModel.train_dfl_loss) }}</td>
              </tr>
              <tr>
                <td>val box loss</td>
                <td>{{ formatNumber(selectedModel.val_box_loss) }}</td>
              </tr>
              <tr>
                <td>val cls loss</td>
                <td>{{ formatNumber(selectedModel.val_cls_loss) }}</td>
              </tr>
              <tr>
                <td>val dfl loss</td>
                <td>{{ formatNumber(selectedModel.val_dfl_loss) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="artifact-section">
        <h4>训练与评估图表</h4>

        <div class="artifact-grid">
          <div
            v-for="item in artifactImages"
            :key="item.filename"
            class="artifact-card"
          >
            <h5>{{ item.title }}</h5>
            <img
              :src="getModelArtifactUrl(selectedModel.name, item.filename)"
              :alt="item.title"
            />
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import {
  getModelVersions,
  getModelArtifactUrl,
  setActiveModel,
} from '@/api/models'

const loading = ref(false)
const settingActive = ref(false)
const models = ref([])
const selectedModel = ref(null)

const artifactImages = [
  {
    title: '训练曲线总览',
    filename: 'results.png',
  },
  {
    title: '混淆矩阵',
    filename: 'confusion_matrix.png',
  },
  {
    title: '归一化混淆矩阵',
    filename: 'confusion_matrix_normalized.png',
  },
  {
    title: 'PR 曲线',
    filename: 'BoxPR_curve.png',
  },
  {
    title: 'F1 曲线',
    filename: 'BoxF1_curve.png',
  },
  {
    title: 'Precision 曲线',
    filename: 'BoxP_curve.png',
  },
  {
    title: 'Recall 曲线',
    filename: 'BoxR_curve.png',
  },
]

async function loadModels() {
  loading.value = true

  try {
    const res = await getModelVersions()
    const payload = res?.data || res || {}
    const data = payload.data || payload

    models.value = Array.isArray(data) ? data : []

    const activeModel = models.value.find(item => item.is_default)

    if (selectedModel.value) {
      const same = models.value.find(item => item.name === selectedModel.value.name)
      selectedModel.value = same || activeModel || models.value[0] || null
    } else {
      selectedModel.value =
        activeModel ||
        models.value.find(item => item.name === 'pcb_aoi_v1.1.0') ||
        models.value[models.value.length - 1] ||
        null
    }
  } catch (error) {
    console.error('加载模型版本失败:', error)
    models.value = []
  } finally {
    loading.value = false
  }
}

function selectModel(model) {
  selectedModel.value = model
}

async function handleSetActiveModel() {
  if (!selectedModel.value || selectedModel.value.is_default || settingActive.value) {
    return
  }

  const ok = window.confirm(`确定将 ${selectedModel.value.name} 设置为当前检测模型吗？`)

  if (!ok) {
    return
  }

  settingActive.value = true

  try {
    await setActiveModel(selectedModel.value.name)
    await loadModels()
    window.alert('当前检测模型设置成功。重新检测时会使用该模型。')
  } catch (error) {
    console.error('设置当前检测模型失败:', error)
    window.alert('设置失败，请查看后端日志。')
  } finally {
    settingActive.value = false
  }
}

function formatMetric(value) {
  const numberValue = Number(value)

  if (Number.isNaN(numberValue)) {
    return '-'
  }

  return `${(numberValue * 100).toFixed(2)}%`
}

function formatNumber(value) {
  const numberValue = Number(value)

  if (Number.isNaN(numberValue)) {
    return '-'
  }

  return numberValue.toFixed(4)
}

onMounted(() => {
  loadModels()
})
</script>

<style scoped>
.models-page {
  width: 100%;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.page-header h2 {
  margin: 0;
  color: #111827;
  font-size: 22px;
}

.page-header p {
  margin: 6px 0 0;
  color: #6b7280;
  font-size: 13px;
}

.refresh-btn,
.set-default-btn {
  height: 36px;
  border: none;
  border-radius: 999px;
  background: #111827;
  color: #ffffff;
  padding: 0 18px;
  cursor: pointer;
}

.set-default-btn:disabled {
  background: #d1d5db;
  cursor: not-allowed;
}

.empty-card {
  border: 1px solid #e5e7eb;
  background: #f9fafb;
  border-radius: 16px;
  padding: 18px;
  color: #6b7280;
}

.model-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 14px;
}

.model-card {
  border: 1px solid #e5e7eb;
  background: #ffffff;
  border-radius: 16px;
  padding: 16px;
  cursor: pointer;
}

.model-card:hover,
.model-card.active {
  border-color: #111827;
}

.model-title-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.model-title-row h3 {
  margin: 0;
  color: #111827;
  font-size: 16px;
}

.model-title-row p {
  margin: 6px 0 0;
  color: #6b7280;
  font-size: 12px;
}

.default-pill {
  height: 24px;
  border-radius: 999px;
  background: #dcfce7;
  color: #166534;
  padding: 0 10px;
  display: inline-flex;
  align-items: center;
  font-size: 12px;
  flex-shrink: 0;
}

.metric-mini-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
  margin-top: 14px;
}

.metric-mini-grid div {
  border: 1px solid #e5e7eb;
  background: #f9fafb;
  border-radius: 12px;
  padding: 10px;
}

.metric-mini-grid span {
  display: block;
  color: #6b7280;
  font-size: 11px;
}

.metric-mini-grid strong {
  display: block;
  margin-top: 5px;
  color: #111827;
  font-size: 13px;
}

.model-meta {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 14px;
}

.model-meta span {
  height: 24px;
  border-radius: 999px;
  background: #f3f4f6;
  color: #374151;
  padding: 0 10px;
  display: inline-flex;
  align-items: center;
  font-size: 12px;
}

.detail-section {
  margin-top: 22px;
  border-top: 1px solid #e5e7eb;
  padding-top: 22px;
}

.section-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.section-header h3 {
  margin: 0;
  color: #111827;
  font-size: 20px;
}

.section-header p {
  margin: 6px 0 0;
  color: #6b7280;
}

.active-tip {
  margin-top: 12px;
  border: 1px solid #bfdbfe;
  background: #eff6ff;
  color: #1d4ed8;
  border-radius: 12px;
  padding: 10px 12px;
  font-size: 13px;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
  margin-top: 16px;
}

.detail-card {
  border: 1px solid #e5e7eb;
  border-radius: 16px;
  padding: 16px;
  background: #ffffff;
}

.detail-card h4,
.artifact-section h4 {
  margin: 0 0 12px;
  color: #111827;
}

.detail-card table {
  width: 100%;
  border-collapse: collapse;
}

.detail-card td {
  border-bottom: 1px solid #e5e7eb;
  padding: 9px 0;
  color: #374151;
  font-size: 13px;
}

.detail-card td:last-child {
  text-align: right;
  color: #111827;
  font-weight: 600;
}

.artifact-section {
  margin-top: 20px;
}

.artifact-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(420px, 1fr));
  gap: 16px;
}

.artifact-card {
  border: 1px solid #e5e7eb;
  border-radius: 16px;
  padding: 14px;
  background: #ffffff;
}

.artifact-card h5 {
  margin: 0 0 10px;
  color: #111827;
}

.artifact-card img {
  width: 100%;
  display: block;
  border-radius: 10px;
  background: #f9fafb;
}

@media (max-width: 900px) {
  .section-header {
    flex-direction: column;
  }

  .detail-grid {
    grid-template-columns: 1fr;
  }

  .artifact-grid {
    grid-template-columns: 1fr;
  }

  .metric-mini-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>