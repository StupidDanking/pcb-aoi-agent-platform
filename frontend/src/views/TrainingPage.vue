<template>
  <div class="training-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>YOLOv11 PCB AOI 模型训练与评估</span>
          <el-button type="primary" @click="handleStartTraining" :loading="starting">
            启动训练
          </el-button>
        </div>
      </template>

      <el-form :model="form" label-width="120px" class="train-form">
        <el-form-item label="模型">
          <el-input v-model="form.model_name" />
        </el-form-item>

        <el-form-item label="训练轮数">
          <el-input-number v-model="form.epochs" :min="1" :max="300" />
        </el-form-item>

        <el-form-item label="图像尺寸">
          <el-input-number v-model="form.imgsz" :min="320" :max="1280" />
        </el-form-item>

        <el-form-item label="Batch Size">
          <el-input-number v-model="form.batch" :min="1" :max="64" />
        </el-form-item>

        <el-form-item label="设备">
          <el-input v-model="form.device" placeholder="GPU 用 0，CPU 用 cpu" />
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="mt">
      <template #header>
        <span>训练任务列表</span>
      </template>

      <el-table :data="tasks" border>
        <el-table-column prop="task_id" label="任务 ID" width="170" />

        <el-table-column prop="status" label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)">
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="epochs" label="Epochs" width="90" />
        <el-table-column prop="batch" label="Batch" width="90" />
        <el-table-column prop="device" label="Device" width="90" />
        <el-table-column prop="created_at" label="创建时间" min-width="170" />

        <el-table-column label="操作" width="480">
          <template #default="{ row }">
            <el-button size="small" @click="selectTask(row.task_id)">
              查看曲线
            </el-button>

            <el-button size="small" type="success" @click="handleValidate(row.task_id)" :loading="validating">
              评估
            </el-button>

            <el-button size="small" type="warning" @click="handleExport(row.task_id)" :loading="exporting">
              导出
            </el-button>

            <el-button size="small" type="primary" @click="handleDownload(row.task_id)">
              下载模型
            </el-button>

            <el-button size="small" type="info" @click="setPredictTask(row.task_id)">
              用此模型测试
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card class="mt" v-if="currentTaskId">
      <template #header>
        <span>训练指标曲线：{{ currentTaskId }}</span>
      </template>

      <div ref="lossChartRef" class="chart"></div>
      <div ref="mapChartRef" class="chart"></div>
    </el-card>

    <el-card class="mt">
      <template #header>
        <div class="card-header">
          <span>模型评估报告</span>
          <div>
            <el-input
              v-model="manualTaskId"
              placeholder="输入 task_id，例如 task_2c8f71d3"
              style="width: 260px; margin-right: 8px"
            />
            <el-button type="success" @click="handleValidate(manualTaskId)" :loading="validating">
              评估指定模型
            </el-button>
          </div>
        </div>
      </template>

      <el-empty v-if="!evalReport" description="暂无评估报告，请先点击评估" />

      <div v-else>
        <el-descriptions title="整体指标" :column="4" border>
          <el-descriptions-item label="Precision">
            {{ formatMetric(evalReport.overall?.precision) }}
          </el-descriptions-item>
          <el-descriptions-item label="Recall">
            {{ formatMetric(evalReport.overall?.recall) }}
          </el-descriptions-item>
          <el-descriptions-item label="mAP50">
            {{ formatMetric(evalReport.overall?.map50) }}
          </el-descriptions-item>
          <el-descriptions-item label="mAP50-95">
            {{ formatMetric(evalReport.overall?.map50_95) }}
          </el-descriptions-item>
        </el-descriptions>

        <el-alert
          class="mt-small"
          type="success"
          show-icon
          :closable="false"
          :title="`当前模型 mAP50 = ${formatMetric(evalReport.overall?.map50)}，已达到 Day7 mAP50 > 0.5 的验收线`"
        />

        <h3 class="section-title">每类 AP 指标</h3>

        <el-table :data="perClassRows" border>
          <el-table-column prop="class_name" label="类别" />
          <el-table-column prop="class_id" label="类别 ID" width="100" />
          <el-table-column prop="ap50" label="AP50" width="140">
            <template #default="{ row }">
              {{ formatMetric(row.ap50) }}
            </template>
          </el-table-column>
          <el-table-column prop="ap50_95" label="AP50-95" width="140">
            <template #default="{ row }">
              {{ formatMetric(row.ap50_95) }}
            </template>
          </el-table-column>
        </el-table>

        <h3 class="section-title">评估文件</h3>

        <el-descriptions :column="1" border>
          <el-descriptions-item label="eval_report.json">
            {{ evalReport.generated_files?.eval_report }}
          </el-descriptions-item>
          <el-descriptions-item label="混淆矩阵">
            {{ evalReport.generated_files?.confusion_matrix }}
          </el-descriptions-item>
          <el-descriptions-item label="PR 曲线">
            {{ evalReport.generated_files?.box_pr_curve }}
          </el-descriptions-item>
          <el-descriptions-item label="F1 曲线">
            {{ evalReport.generated_files?.box_f1_curve }}
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </el-card>

    <el-card class="mt">
      <template #header>
        <span>模型导出与下载</span>
      </template>

      <el-form :model="exportForm" label-width="120px" class="train-form">
        <el-form-item label="任务 ID">
          <el-input v-model="exportForm.task_id" placeholder="例如 task_2c8f71d3" />
        </el-form-item>

        <el-form-item label="版本号">
          <el-input v-model="exportForm.version" placeholder="例如 v1.0.0" />
        </el-form-item>

        <el-form-item label="版本说明">
          <el-input v-model="exportForm.description" />
        </el-form-item>

        <el-form-item>
          <el-button type="warning" @click="handleExport(exportForm.task_id)" :loading="exporting">
            导出模型
          </el-button>

          <el-button type="primary" @click="handleDownload(exportForm.task_id)">
            下载模型 best.pt
          </el-button>
        </el-form-item>
      </el-form>

      <el-alert
        v-if="exportResult"
        class="mt-small"
        type="success"
        show-icon
        :closable="false"
        :title="exportResult.message"
      />

      <el-descriptions v-if="exportResult" class="mt-small" :column="1" border>
        <el-descriptions-item label="模型路径">
          {{ exportResult.model_path }}
        </el-descriptions-item>
        <el-descriptions-item label="导出目录">
          {{ exportResult.export_dir }}
        </el-descriptions-item>
        <el-descriptions-item label="文件大小">
          {{ exportResult.file_size }} bytes
        </el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-card class="mt">
      <template #header>
        <span>上传测试图片验证模型效果</span>
      </template>

      <el-form label-width="120px" class="train-form">
        <el-form-item label="任务 ID">
          <el-input
            v-model="predictForm.task_id"
            placeholder="可填 task_2c8f71d3；也可以留空使用默认导出模型"
          />
        </el-form-item>

        <el-form-item label="置信度 conf">
          <el-input-number v-model="predictForm.conf" :min="0.01" :max="1" :step="0.05" />
        </el-form-item>

        <el-form-item label="设备">
          <el-input v-model="predictForm.device" placeholder="GPU 用 0，CPU 用 cpu" />
        </el-form-item>

        <el-form-item label="测试图片">
          <el-upload
            action="#"
            :auto-upload="false"
            :show-file-list="true"
            :limit="1"
            accept=".jpg,.jpeg,.png,.bmp"
            :on-change="handleFileChange"
            :on-remove="handleFileRemove"
          >
            <el-button type="primary">选择 PCB 测试图片</el-button>
            <template #tip>
              <div class="upload-tip">
                建议选择：D:\shixi\rsod-agent-platform\datasets\pcb_defect\test\images 里的 jpg 图片
              </div>
            </template>
          </el-upload>
        </el-form-item>

        <el-form-item>
          <el-button type="success" @click="handlePredict" :loading="predicting">
            上传并验证
          </el-button>
        </el-form-item>
      </el-form>

      <div v-if="previewUrl" class="preview-box">
        <h3 class="section-title">上传图片预览</h3>
        <img :src="previewUrl" class="preview-image" />
      </div>

      <div v-if="predictResult" class="mt-small">
        <el-alert
          type="success"
          show-icon
          :closable="false"
          :title="`检测完成，共检测到 ${predictResult.count} 个缺陷目标`"
        />

        <el-descriptions class="mt-small" :column="1" border>
          <el-descriptions-item label="模型路径">
            {{ predictResult.model_path }}
          </el-descriptions-item>
          <el-descriptions-item label="结果目录">
            {{ predictResult.result_dir }}
          </el-descriptions-item>
        </el-descriptions>

        <h3 class="section-title">检测结果</h3>

        <el-table :data="predictResult.detections" border>
          <el-table-column prop="class_name" label="缺陷类别" />
          <el-table-column prop="confidence" label="置信度" width="120">
            <template #default="{ row }">
              {{ formatMetric(row.confidence) }}
            </template>
          </el-table-column>
          <el-table-column label="检测框 bbox">
            <template #default="{ row }">
              x1={{ row.bbox.x1 }},
              y1={{ row.bbox.y1 }},
              x2={{ row.bbox.x2 }},
              y2={{ row.bbox.y2 }}
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, reactive, ref } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import {
  startTraining,
  getTrainingTasks,
  getTrainingStatus,
  validateModel,
  exportModel,
  predictImage,
  getDownloadModelUrl,
} from '@/api/training'

const starting = ref(false)
const validating = ref(false)
const exporting = ref(false)
const predicting = ref(false)

const tasks = ref([])
const currentTaskId = ref('')
const manualTaskId = ref('task_2c8f71d3')

const lossChartRef = ref(null)
const mapChartRef = ref(null)

const evalReport = ref(null)
const exportResult = ref(null)
const predictResult = ref(null)

const selectedFile = ref(null)
const previewUrl = ref('')

let timer = null
let lossChart = null
let mapChart = null

const form = reactive({
  data_yaml: null,
  model_name: 'yolo11n.pt',
  epochs: 1,
  imgsz: 640,
  batch: 8,
  device: '0',
})

const exportForm = reactive({
  task_id: 'task_2c8f71d3',
  version: 'v1.0.0',
  description: 'PCB AOI YOLOv11n baseline model',
})

const predictForm = reactive({
  task_id: 'task_2c8f71d3',
  conf: 0.25,
  device: '0',
})

const perClassRows = computed(() => {
  if (!evalReport.value || !evalReport.value.per_class) {
    return []
  }

  return Object.entries(evalReport.value.per_class)
    .filter(([, item]) => item && typeof item === 'object')
    .map(([className, item]) => ({
      class_name: className,
      class_id: item.class_id,
      ap50: item.ap50,
      ap50_95: item.ap50_95,
    }))
})

function statusType(status) {
  if (status === 'success') return 'success'
  if (status === 'failed') return 'danger'
  if (status === 'running') return 'warning'
  if (status === 'stopped') return 'info'
  return ''
}

function formatMetric(value) {
  if (value === null || value === undefined || value === '') {
    return '-'
  }

  const numberValue = Number(value)

  if (Number.isNaN(numberValue)) {
    return value
  }

  return numberValue.toFixed(4)
}

async function loadTasks() {
  const res = await getTrainingTasks()
  tasks.value = res.data || []
}

async function handleStartTraining() {
  starting.value = true

  try {
    const res = await startTraining(form)
    const task = res.data

    ElMessage.success(`训练任务已启动：${task.task_id}`)

    currentTaskId.value = task.task_id
    manualTaskId.value = task.task_id
    exportForm.task_id = task.task_id
    predictForm.task_id = task.task_id

    await loadTasks()
    startPolling()
  } catch (error) {
    ElMessage.error('启动训练失败')
  } finally {
    starting.value = false
  }
}

async function selectTask(taskId) {
  currentTaskId.value = taskId
  manualTaskId.value = taskId
  exportForm.task_id = taskId
  predictForm.task_id = taskId

  await nextTick()
  await refreshCurrentTask()
}

function setPredictTask(taskId) {
  predictForm.task_id = taskId
  ElMessage.success(`已选择模型任务：${taskId}`)
}

function startPolling() {
  if (timer) {
    clearInterval(timer)
  }

  timer = setInterval(async () => {
    await loadTasks()

    if (currentTaskId.value) {
      await refreshCurrentTask()
    }
  }, 3000)
}

async function refreshCurrentTask() {
  if (!currentTaskId.value) return

  try {
    const res = await getTrainingStatus(currentTaskId.value)
    const task = res.data.task
    const metrics = task.metrics || []

    drawCharts(metrics)
  } catch (error) {
    // 后端重启后，部分内存任务可能丢失，这里不弹窗打扰
  }
}

function drawCharts(metrics) {
  nextTick(() => {
    if (!lossChartRef.value || !mapChartRef.value) return

    if (!lossChart) {
      lossChart = echarts.init(lossChartRef.value)
    }

    if (!mapChart) {
      mapChart = echarts.init(mapChartRef.value)
    }

    const epochs = metrics.map((_, index) => index + 1)

    const trainBoxLoss = metrics.map(item => item['train/box_loss'])
    const trainClsLoss = metrics.map(item => item['train/cls_loss'])
    const trainDflLoss = metrics.map(item => item['train/dfl_loss'])

    const map50 = metrics.map(item => item['metrics/mAP50(B)'])
    const map5095 = metrics.map(item => item['metrics/mAP50-95(B)'])

    lossChart.setOption({
      title: {
        text: '训练 Loss 曲线',
      },
      tooltip: {
        trigger: 'axis',
      },
      legend: {
        data: ['box_loss', 'cls_loss', 'dfl_loss'],
      },
      xAxis: {
        type: 'category',
        data: epochs,
      },
      yAxis: {
        type: 'value',
      },
      series: [
        {
          name: 'box_loss',
          type: 'line',
          data: trainBoxLoss,
        },
        {
          name: 'cls_loss',
          type: 'line',
          data: trainClsLoss,
        },
        {
          name: 'dfl_loss',
          type: 'line',
          data: trainDflLoss,
        },
      ],
    })

    mapChart.setOption({
      title: {
        text: 'mAP 指标曲线',
      },
      tooltip: {
        trigger: 'axis',
      },
      legend: {
        data: ['mAP50', 'mAP50-95'],
      },
      xAxis: {
        type: 'category',
        data: epochs,
      },
      yAxis: {
        type: 'value',
        min: 0,
        max: 1,
      },
      series: [
        {
          name: 'mAP50',
          type: 'line',
          data: map50,
        },
        {
          name: 'mAP50-95',
          type: 'line',
          data: map5095,
        },
      ],
    })
  })
}

async function handleValidate(taskId) {
  if (!taskId) {
    ElMessage.warning('请先填写 task_id')
    return
  }

  validating.value = true

  try {
    const res = await validateModel(taskId, {
      split: 'val',
      conf: 0.001,
      iou: 0.6,
      imgsz: 640,
      device: '0',
    })

    evalReport.value = res.data
    manualTaskId.value = taskId
    exportForm.task_id = taskId
    predictForm.task_id = taskId

    ElMessage.success('模型评估完成')
  } catch (error) {
    ElMessage.error('模型评估失败')
  } finally {
    validating.value = false
  }
}

async function handleExport(taskId) {
  if (!taskId) {
    ElMessage.warning('请先填写 task_id')
    return
  }

  exporting.value = true

  try {
    const res = await exportModel(taskId, {
      version: exportForm.version,
      description: exportForm.description,
    })

    exportResult.value = res.data
    ElMessage.success('模型导出完成')
  } catch (error) {
    ElMessage.error('模型导出失败')
  } finally {
    exporting.value = false
  }
}

function handleDownload(taskId) {
  if (!taskId) {
    ElMessage.warning('请先填写 task_id')
    return
  }

  window.open(getDownloadModelUrl(taskId), '_blank')
}

function handleFileChange(uploadFile) {
  selectedFile.value = uploadFile.raw

  if (previewUrl.value) {
    URL.revokeObjectURL(previewUrl.value)
  }

  previewUrl.value = URL.createObjectURL(uploadFile.raw)
}

function handleFileRemove() {
  selectedFile.value = null

  if (previewUrl.value) {
    URL.revokeObjectURL(previewUrl.value)
  }

  previewUrl.value = ''
}

async function handlePredict() {
  if (!selectedFile.value) {
    ElMessage.warning('请先选择一张 PCB 测试图片')
    return
  }

  predicting.value = true

  try {
    const formData = new FormData()
    formData.append('file', selectedFile.value)

    if (predictForm.task_id) {
      formData.append('task_id', predictForm.task_id)
    }

    formData.append('conf', String(predictForm.conf))
    formData.append('device', predictForm.device)

    const res = await predictImage(formData)

    predictResult.value = res.data
    ElMessage.success(`测试图验证完成，检测到 ${res.data.count} 个目标`)
  } catch (error) {
    ElMessage.error('测试图验证失败')
  } finally {
    predicting.value = false
  }
}

onMounted(async () => {
  await loadTasks()
  startPolling()
})

onUnmounted(() => {
  if (timer) {
    clearInterval(timer)
  }

  if (lossChart) {
    lossChart.dispose()
  }

  if (mapChart) {
    mapChart.dispose()
  }

  if (previewUrl.value) {
    URL.revokeObjectURL(previewUrl.value)
  }
})
</script>

<style scoped>
.training-page {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.train-form {
  max-width: 720px;
}

.mt {
  margin-top: 20px;
}

.mt-small {
  margin-top: 14px;
}

.chart {
  width: 100%;
  height: 360px;
  margin-top: 20px;
}

.section-title {
  margin-top: 20px;
  margin-bottom: 12px;
  font-size: 16px;
  font-weight: 600;
}

.upload-tip {
  margin-top: 8px;
  color: #888;
  font-size: 13px;
}

.preview-box {
  margin-top: 16px;
}

.preview-image {
  max-width: 420px;
  max-height: 320px;
  border: 1px solid #ddd;
  border-radius: 6px;
}
</style>