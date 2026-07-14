<template>
  <div class="result-card">
    <div class="result-header">
      <div class="result-title-block">
        <h3>{{ cardTitle }}</h3>
        <p>{{ cardSubtitle }}</p>
      </div>

      <div class="result-badge">
        {{ totalObjects }} defects
      </div>
    </div>

    <div class="param-row">
      <span>检测参数</span>
      <strong>conf {{ displayConf }}</strong>
      <strong>IoU {{ displayIou }}</strong>
    </div>

    <!-- 视频检测 -->
    <div v-if="isVideoResult" class="video-layout">
      <div class="metric-grid overview-grid">
        <div class="metric-item">
          <span>视频名称</span>
          <strong>{{ result.video_name || '-' }}</strong>
        </div>

        <div class="metric-item">
          <span>总帧数</span>
          <strong>{{ result.total_frames || 0 }}</strong>
        </div>

        <div class="metric-item">
          <span>处理关键帧</span>
          <strong>{{ result.processed_frames || 0 }}</strong>
        </div>

        <div class="metric-item">
          <span>总目标数</span>
          <strong>{{ result.total_objects || 0 }}</strong>
        </div>

        <div class="metric-item">
          <span>FPS</span>
          <strong>{{ result.fps || 0 }}</strong>
        </div>

        <div class="metric-item">
          <span>视频时长</span>
          <strong>{{ result.duration_seconds || 0 }}s</strong>
        </div>
      </div>

      <div class="section-block">
        <h4>视频类别统计</h4>

        <div v-if="classStats.length === 0" class="empty-text">
          暂无缺陷类别统计
        </div>

        <table v-else class="stat-table">
          <thead>
            <tr>
              <th>类别</th>
              <th>数量</th>
            </tr>
          </thead>

          <tbody>
            <tr
              v-for="item in classStats"
              :key="item.class_name"
            >
              <td>{{ item.class_name }}</td>
              <td>{{ item.count }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="section-block">
        <h4>关键帧检测结果</h4>

        <div v-if="videoKeyFrames.length === 0" class="empty-text">
          暂无关键帧结果
        </div>

        <div v-else class="video-frame-list">
          <div
            v-for="frame in videoKeyFrames"
            :key="frame.frame_index"
            class="video-frame-card"
          >
            <img
              v-if="frame.annotated_image_base64"
              :src="frame.annotated_image_base64"
              alt="video frame"
            />

            <div v-else class="video-frame-placeholder">
              暂无关键帧图像
            </div>

            <div class="video-frame-info">
              <strong>Frame {{ frame.frame_index }}</strong>
              <span>{{ frame.timestamp }}s</span>
              <span>目标数：{{ frame.object_count || 0 }}</span>
              <span>推理耗时：{{ frame.inference_time || 0 }}ms</span>
            </div>

            <div class="video-frame-detail">
              <div v-if="!frame.detections || frame.detections.length === 0" class="empty-text small-empty">
                当前关键帧未检测到明显缺陷
              </div>

              <table v-else class="detail-table small-detail-table">
                <thead>
                  <tr>
                    <th>类别</th>
                    <th>置信度</th>
                    <th>bbox</th>
                  </tr>
                </thead>

                <tbody>
                  <tr
                    v-for="(det, detIndex) in frame.detections"
                    :key="detIndex"
                  >
                    <td>{{ det.class_name || '-' }}</td>
                    <td>{{ formatConfidence(det.confidence) }}</td>
                    <td class="bbox-cell">{{ formatBbox(det.bbox) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 单图检测 -->
    <div v-else-if="isSingleResult" class="single-layout">
      <div v-if="singleResult.annotated_image_base64" class="image-panel">
        <img
          :src="singleResult.annotated_image_base64"
          alt="annotated result"
        />
      </div>

      <div v-else class="image-panel image-placeholder">
        暂无标注图
      </div>

      <div class="detail-panel">
        <div class="info-card">
          <span>图片名称</span>
          <strong>{{ singleResult.image_name || '-' }}</strong>
        </div>

        <div class="metric-grid">
          <div class="metric-item">
            <span>目标数量</span>
            <strong>{{ singleResult.total_objects || 0 }}</strong>
          </div>

          <div class="metric-item">
            <span>类别数量</span>
            <strong>{{ classStats.length }}</strong>
          </div>
        </div>

        <div class="section-block">
          <h4>类别统计</h4>

          <div v-if="classStats.length === 0" class="empty-text">
            暂无缺陷类别统计
          </div>

          <table v-else class="stat-table">
            <thead>
              <tr>
                <th>类别</th>
                <th>数量</th>
              </tr>
            </thead>

            <tbody>
              <tr
                v-for="item in classStats"
                :key="item.class_name"
              >
                <td>{{ item.class_name }}</td>
                <td>{{ item.count }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="section-block">
          <h4>检测框详情</h4>

          <div v-if="detections.length === 0" class="empty-text">
            当前图片未检测到明显缺陷
          </div>

          <table v-else class="detail-table">
            <thead>
              <tr>
                <th>类别</th>
                <th>置信度</th>
                <th>bbox</th>
              </tr>
            </thead>

            <tbody>
              <tr
                v-for="(item, index) in detections"
                :key="index"
              >
                <td>{{ item.class_name || '-' }}</td>
                <td>{{ formatConfidence(item.confidence) }}</td>
                <td class="bbox-cell">{{ formatBbox(item.bbox) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- 批量 / ZIP 检测 -->
    <div v-else class="batch-layout">
      <div class="batch-overview">
        <div class="metric-grid overview-grid">
          <div class="metric-item">
            <span>总图片数</span>
            <strong>{{ result.total_images || 0 }}</strong>
          </div>

          <div class="metric-item">
            <span>成功图片</span>
            <strong>{{ result.success_images || 0 }}</strong>
          </div>

          <div class="metric-item">
            <span>失败图片</span>
            <strong>{{ result.failed_images || 0 }}</strong>
          </div>

          <div class="metric-item">
            <span>总目标数</span>
            <strong>{{ result.total_objects || 0 }}</strong>
          </div>
        </div>

        <div class="section-block">
          <h4>总体类别统计</h4>

          <div v-if="classStats.length === 0" class="empty-text">
            暂无总体类别统计
          </div>

          <table v-else class="stat-table">
            <thead>
              <tr>
                <th>类别</th>
                <th>数量</th>
              </tr>
            </thead>

            <tbody>
              <tr
                v-for="item in classStats"
                :key="item.class_name"
              >
                <td>{{ item.class_name }}</td>
                <td>{{ item.count }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="section-block">
        <h4>图片结果列表</h4>

        <div v-if="batchResults.length === 0" class="empty-text">
          暂无图片结果
        </div>

        <div v-else class="batch-list">
          <div
            v-for="(item, index) in batchResults"
            :key="index"
            class="batch-item"
          >
            <div class="batch-image-panel">
              <img
                v-if="item.annotated_image_base64"
                :src="item.annotated_image_base64"
                alt="batch annotated"
              />

              <div v-else class="image-placeholder">
                无标注图
              </div>
            </div>

            <div class="batch-detail-panel">
              <div class="batch-title-row">
                <div class="batch-title-main">
                  <strong>
                    {{ item.image_name || item.image_path || `图片 ${index + 1}` }}
                  </strong>

                  <p>
                    目标数：{{ item.total_objects || 0 }}
                    <template v-if="item.class_stats && item.class_stats.length > 0">
                      ｜类别：{{ formatStats(item.class_stats) }}
                    </template>
                  </p>
                </div>

                <span :class="['status-pill', item.success ? 'success' : 'failed']">
                  {{ item.success ? 'success' : 'failed' }}
                </span>
              </div>

              <template v-if="item.success">
                <div class="section-block compact-block">
                  <h4>该图类别统计</h4>

                  <div
                    v-if="!item.class_stats || item.class_stats.length === 0"
                    class="empty-text"
                  >
                    暂无缺陷类别统计
                  </div>

                  <table v-else class="stat-table">
                    <thead>
                      <tr>
                        <th>类别</th>
                        <th>数量</th>
                      </tr>
                    </thead>

                    <tbody>
                      <tr
                        v-for="stat in item.class_stats"
                        :key="stat.class_name"
                      >
                        <td>{{ stat.class_name }}</td>
                        <td>{{ stat.count }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                <div class="section-block compact-block">
                  <h4>检测框详情</h4>

                  <div
                    v-if="!item.detections || item.detections.length === 0"
                    class="empty-text"
                  >
                    当前图片未检测到明显缺陷
                  </div>

                  <table v-else class="detail-table">
                    <thead>
                      <tr>
                        <th>类别</th>
                        <th>置信度</th>
                        <th>bbox</th>
                      </tr>
                    </thead>

                    <tbody>
                      <tr
                        v-for="(det, detIndex) in item.detections"
                        :key="detIndex"
                      >
                        <td>{{ det.class_name || '-' }}</td>
                        <td>{{ formatConfidence(det.confidence) }}</td>
                        <td class="bbox-cell">{{ formatBbox(det.bbox) }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </template>

              <div v-else class="batch-error">
                {{ item.error || '检测失败' }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  result: {
    type: Object,
    required: true,
  },
  mode: {
    type: String,
    default: 'single',
  },
})

const isVideoResult = computed(() => {
  return props.mode === 'video' || props.result?.type === 'video'
})

const isSingleResult = computed(() => {
  if (isVideoResult.value) {
    return false
  }

  return props.mode === 'single' || !!props.result.detections
})

const singleResult = computed(() => {
  return props.result || {}
})

const batchResults = computed(() => {
  return props.result.results || []
})

const videoKeyFrames = computed(() => {
  return props.result.key_frames || []
})

const detections = computed(() => {
  return singleResult.value.detections || []
})

const classStats = computed(() => {
  if (props.result.class_stats) {
    return props.result.class_stats
  }

  if (props.result.class_counts) {
    return Object.entries(props.result.class_counts).map(([className, count]) => ({
      class_name: className,
      count,
    }))
  }

  return []
})

const totalObjects = computed(() => {
  if (isVideoResult.value) {
    return props.result.total_objects || 0
  }

  if (isSingleResult.value) {
    return singleResult.value.total_objects || detections.value.length || 0
  }

  return props.result.total_objects || 0
})

const displayConf = computed(() => {
  const value = props.result.conf

  if (value === undefined || value === null || value === '') {
    return '0.25'
  }

  return value
})

const displayIou = computed(() => {
  const value = props.result.iou

  if (value === undefined || value === null || value === '') {
    return '0.45'
  }

  return value
})

const cardTitle = computed(() => {
  if (props.mode === 'video' || props.result?.type === 'video') {
    return `视频检测结果：${props.result.video_name || ''}`
  }

  if (props.mode === 'zip') {
    return `ZIP 批量检测结果：${props.result.zip_name || ''}`
  }

  if (props.mode === 'batch') {
    return '批量图片检测结果'
  }

  return `单图检测结果：${singleResult.value.image_name || ''}`
})

const cardSubtitle = computed(() => {
  if (props.mode === 'video' || props.result?.type === 'video') {
    return '已完成视频关键帧采样和 PCB 缺陷检测。'
  }

  if (props.mode === 'zip') {
    return '已完成 ZIP 解压、图片筛选和批量检测。'
  }

  if (props.mode === 'batch') {
    return '已完成多张 PCB 图片批量检测。'
  }

  return '已完成单张 PCB 图片缺陷检测。'
})

function formatConfidence(value) {
  const numberValue = Number(value || 0)
  return `${(numberValue * 100).toFixed(2)}%`
}

function formatBbox(bbox) {
  if (!bbox) {
    return '-'
  }

  if (Array.isArray(bbox)) {
    return bbox.map(item => Number(item).toFixed(1)).join(', ')
  }

  if (typeof bbox === 'object') {
    return JSON.stringify(bbox)
  }

  return String(bbox)
}

function formatStats(stats) {
  if (!stats || stats.length === 0) {
    return '-'
  }

  return stats
    .map(item => `${item.class_name} × ${item.count}`)
    .join('，')
}
</script>

<style scoped>
.result-card {
  border: 1px solid #e5e7eb;
  background: #ffffff;
  border-radius: 18px;
  padding: 18px;
  margin-top: 14px;
  max-width: 100%;
  overflow: hidden;
}

.result-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 12px;
}

.result-title-block {
  min-width: 0;
}

.result-header h3 {
  margin: 0;
  color: #111827;
  font-size: 18px;
  word-break: break-all;
}

.result-header p {
  margin: 6px 0 0;
  color: #6b7280;
  font-size: 13px;
}

.result-badge {
  height: 30px;
  border-radius: 999px;
  background: #111827;
  color: #ffffff;
  padding: 0 12px;
  display: flex;
  align-items: center;
  font-size: 12px;
  flex-shrink: 0;
}

.param-row {
  display: inline-flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
  color: #6b7280;
  font-size: 12px;
}

.param-row strong {
  height: 26px;
  border-radius: 999px;
  background: #f3f4f6;
  color: #374151;
  display: inline-flex;
  align-items: center;
  padding: 0 10px;
  font-weight: 500;
}

.single-layout {
  display: grid;
  grid-template-columns: minmax(280px, 430px) minmax(0, 1fr);
  gap: 18px;
}

.image-panel,
.batch-image-panel {
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  overflow: hidden;
  background: #f9fafb;
}

.image-panel img,
.batch-image-panel img {
  width: 100%;
  display: block;
}

.image-placeholder {
  min-height: 180px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #9ca3af;
  font-size: 13px;
  background: #f9fafb;
}

.detail-panel,
.batch-detail-panel {
  min-width: 0;
}

.info-card {
  border: 1px solid #e5e7eb;
  background: #f9fafb;
  border-radius: 12px;
  padding: 12px;
  margin-bottom: 10px;
}

.info-card span {
  display: block;
  color: #6b7280;
  font-size: 12px;
  margin-bottom: 6px;
}

.info-card strong {
  color: #111827;
  font-size: 14px;
  word-break: break-all;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.overview-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.metric-item {
  border: 1px solid #e5e7eb;
  background: #f9fafb;
  border-radius: 12px;
  padding: 12px;
  min-width: 0;
}

.metric-item span {
  display: block;
  color: #6b7280;
  font-size: 12px;
  margin-bottom: 6px;
}

.metric-item strong {
  color: #111827;
  font-size: 16px;
  word-break: break-word;
}

.section-block {
  margin-top: 16px;
}

.compact-block {
  margin-top: 12px;
}

.section-block h4 {
  margin: 0 0 10px;
  color: #111827;
  font-size: 15px;
}

.empty-text {
  color: #9ca3af;
  font-size: 13px;
  padding: 10px 0;
}

.small-empty {
  padding: 6px 0 0;
}

.stat-table,
.detail-table {
  border-collapse: separate;
  border-spacing: 0;
  font-size: 13px;
}

.stat-table {
  width: auto;
  min-width: 250px;
  max-width: 360px;
  table-layout: auto;
}

.detail-table {
  width: 100%;
  table-layout: fixed;
}

.stat-table th,
.stat-table td,
.detail-table th,
.detail-table td {
  border-bottom: 1px solid #e5e7eb;
  padding: 10px 14px;
  text-align: left;
  vertical-align: top;
}

.stat-table th,
.detail-table th {
  color: #6b7280;
  font-weight: 600;
  white-space: nowrap;
}

.stat-table td,
.detail-table td {
  color: #374151;
}

.stat-table th:nth-child(1),
.stat-table td:nth-child(1) {
  min-width: 145px;
  padding-right: 34px;
}

.stat-table th:nth-child(2),
.stat-table td:nth-child(2) {
  min-width: 56px;
  padding-left: 10px;
  white-space: nowrap;
  text-align: left;
}

.detail-table th:nth-child(1),
.detail-table td:nth-child(1) {
  width: 25%;
  padding-right: 22px;
  white-space: nowrap;
}

.detail-table th:nth-child(2),
.detail-table td:nth-child(2) {
  width: 24%;
  padding-left: 22px;
  padding-right: 22px;
  white-space: nowrap;
}

.detail-table th:nth-child(3),
.detail-table td:nth-child(3) {
  width: 51%;
  padding-left: 22px;
}

.bbox-cell {
  word-break: break-word;
  white-space: normal;
  line-height: 1.7;
}

.batch-layout {
  min-width: 0;
}

.batch-overview {
  margin-bottom: 18px;
}

.batch-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.batch-item {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  gap: 16px;
  border: 1px solid #e5e7eb;
  border-radius: 16px;
  padding: 14px;
  background: #ffffff;
}

.batch-image-panel {
  min-height: 180px;
}

.batch-title-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.batch-title-main {
  min-width: 0;
}

.batch-title-row strong {
  display: block;
  color: #111827;
  font-size: 14px;
  word-break: break-all;
}

.batch-title-row p {
  margin: 6px 0 0;
  color: #6b7280;
  font-size: 13px;
}

.status-pill {
  height: 24px;
  border-radius: 999px;
  padding: 0 10px;
  display: inline-flex;
  align-items: center;
  font-size: 12px;
  flex-shrink: 0;
}

.status-pill.success {
  background: #dcfce7;
  color: #166534;
}

.status-pill.failed {
  background: #fee2e2;
  color: #991b1b;
}

.batch-error {
  color: #dc2626;
  font-size: 13px;
}

.video-layout {
  min-width: 0;
}

.video-frame-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 14px;
}

.video-frame-card {
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  overflow: hidden;
  background: #ffffff;
}

.video-frame-card img {
  width: 100%;
  height: 170px;
  object-fit: cover;
  display: block;
  background: #f9fafb;
}

.video-frame-placeholder {
  height: 170px;
  background: #f9fafb;
  color: #9ca3af;
  font-size: 13px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.video-frame-info {
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  border-bottom: 1px solid #e5e7eb;
}

.video-frame-info strong {
  color: #111827;
  font-size: 13px;
}

.video-frame-info span {
  color: #6b7280;
  font-size: 12px;
}

.video-frame-detail {
  padding: 0 10px 10px;
}

.small-detail-table {
  margin-top: 8px;
  font-size: 12px;
}

.small-detail-table th,
.small-detail-table td {
  padding: 7px 6px;
}

@media (max-width: 1200px) {
  .single-layout,
  .batch-item {
    grid-template-columns: 1fr;
  }

  .overview-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 700px) {
  .metric-grid,
  .overview-grid {
    grid-template-columns: 1fr;
  }

  .result-header {
    flex-direction: column;
  }

  .stat-table {
    min-width: 220px;
    max-width: 100%;
  }

  .stat-table th,
  .stat-table td,
  .detail-table th,
  .detail-table td {
    padding: 8px 10px;
  }

  .stat-table th:nth-child(1),
  .stat-table td:nth-child(1) {
    min-width: 130px;
    padding-right: 20px;
  }

  .stat-table th:nth-child(2),
  .stat-table td:nth-child(2) {
    min-width: 50px;
    padding-left: 8px;
  }

  .detail-table th:nth-child(1),
  .detail-table td:nth-child(1),
  .detail-table th:nth-child(2),
  .detail-table td:nth-child(2),
  .detail-table th:nth-child(3),
  .detail-table td:nth-child(3) {
    padding-left: 10px;
    padding-right: 10px;
  }

  .video-frame-list {
    grid-template-columns: 1fr;
  }
}
</style>