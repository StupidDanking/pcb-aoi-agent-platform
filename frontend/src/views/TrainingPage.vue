<template>
  <div class="training-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>YOLOv11 PCB AOI 模型训练监控</span>
          <el-button type="primary" @click="handleStartTraining" :loading="starting">
            启动 1 Epoch 测试训练
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
        <el-table-column prop="task_id" label="任务 ID" width="160" />
        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)">
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="epochs" label="Epochs" width="100" />
        <el-table-column prop="batch" label="Batch" width="100" />
        <el-table-column prop="device" label="Device" width="100" />
        <el-table-column prop="created_at" label="创建时间" />
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button size="small" @click="selectTask(row.task_id)">
              查看曲线
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
  </div>
</template>

<script setup>
import { nextTick, onMounted, onUnmounted, reactive, ref } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import {
  startTraining,
  getTrainingTasks,
  getTrainingStatus,
} from '@/api/training'

const starting = ref(false)
const tasks = ref([])
const currentTaskId = ref('')
const lossChartRef = ref(null)
const mapChartRef = ref(null)

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

function statusType(status) {
  if (status === 'success') return 'success'
  if (status === 'failed') return 'danger'
  if (status === 'running') return 'warning'
  if (status === 'stopped') return 'info'
  return ''
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
  await nextTick()
  await refreshCurrentTask()
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

  const res = await getTrainingStatus(currentTaskId.value)
  const task = res.data.task
  const metrics = task.metrics || []

  drawCharts(metrics)
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
  max-width: 600px;
}

.mt {
  margin-top: 20px;
}

.chart {
  width: 100%;
  height: 360px;
  margin-top: 20px;
}
</style>