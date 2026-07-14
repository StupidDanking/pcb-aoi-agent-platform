<template>
  <div class="chat-page">
    <div class="message-area" ref="messageAreaRef">
      <div v-if="messages.length === 0" class="empty-state">
        <div class="empty-icon">✦</div>
        <h2>今天想分析哪块 PCB？</h2>
        <p>
          可以上传单张图片、多张图片、ZIP 或视频文件进行检测，也可以直接询问 PCB 缺陷和模型指标。
        </p>

        <div class="quick-prompts">
          <button @click="usePrompt('PCB 缺孔缺陷一般是什么原因造成的？')">
            缺孔原因分析
          </button>

          <button @click="usePrompt('如何判断 PCB 短路缺陷的严重程度？')">
            短路严重程度
          </button>

          <button @click="usePrompt('YOLOv11 的 mAP50 和 Recall 分别代表什么？')">
            模型指标解释
          </button>

          <button @click="usePrompt('请检测这个 PCB 视频')">
            视频检测
          </button>
        </div>
      </div>

      <div v-else class="message-list">
        <div
          v-for="message in messages"
          :key="message.id"
          :class="['message-row', message.role]"
        >
          <div class="message-bubble">
            <div v-if="message.files && message.files.length > 0" class="attached-files">
              <div
                v-for="(file, index) in message.files"
                :key="index"
                class="attached-file"
              >
                {{ file.name }}
              </div>
            </div>

            <div v-if="message.content" class="message-text">
              {{ message.content }}
            </div>

            <div v-if="message.statusText" class="status-line">
              {{ message.statusText }}
            </div>

            <div v-if="message.toolName" class="tool-line">
              工具调用：{{ formatToolName(message.toolName) }}
            </div>

            <DetectionResultCard
              v-if="message.detectionResult"
              :result="message.detectionResult"
              :mode="message.detectMode"
            />
          </div>
        </div>
      </div>
    </div>

    <div class="composer-shell">
      <div v-if="selectedFiles.length > 0" class="file-list">
        <div
          v-for="(file, index) in selectedFiles"
          :key="index"
          class="file-chip"
        >
          <span>{{ file.name }}</span>
          <button @click="removeFile(index)">×</button>
        </div>
      </div>

      <div class="composer">
        <label class="upload-btn">
          +
          <input
            type="file"
            multiple
            accept="image/*,video/*,.zip"
            @change="handleFileChange"
          />
        </label>

        <textarea
          v-model="inputText"
          placeholder="输入问题，或者上传 PCB 图片 / ZIP / 视频后点击发送..."
          rows="1"
          @keydown.enter.prevent="handleSend"
        />

        <div class="param-group">
          <label>
            conf
            <input
              v-model.number="conf"
              type="number"
              min="0.01"
              max="1"
              step="0.01"
            />
          </label>

          <label>
            IoU
            <input
              v-model.number="iou"
              type="number"
              min="0.01"
              max="1"
              step="0.01"
            />
          </label>
        </div>

        <div class="chat-model-select">
          <select
            v-model="modelVersion"
            :disabled="modelLoading || sending"
            @change="handleModelVersionChange"
          >
            <option
              v-for="model in modelOptions"
              :key="model.name"
              :value="model.name"
            >
              {{ model.name }}
            </option>
          </select>
        </div>

        <button
          class="send-btn"
          :disabled="sending || (!inputText.trim() && selectedFiles.length === 0)"
          @click="handleSend"
        >
          {{ sending ? '处理中...' : '发送' }}
        </button>
      </div>

      <div class="composer-tip">
        当前检测模型：{{ modelVersion || '未选择' }}。后端 Agent 会自动判断问答、单图、批量、ZIP 或视频检测。
      </div>
    </div>
  </div>
</template>

<script setup>
import { nextTick, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'

import DetectionResultCard from '@/components/DetectionResultCard.vue'
import { streamChat } from '@/api/chat'
import {
  createChatMessage,
  getChatSessionDetail,
} from '@/api/history'
import {
  getModelVersions,
  getActiveModel,
  setActiveModel,
} from '@/api/models'

const route = useRoute()

const inputText = ref('')
const selectedFiles = ref([])
const messages = ref([])
const sending = ref(false)
const messageAreaRef = ref(null)

const conf = ref(0.25)
const iou = ref(0.45)

const currentSessionId = ref(null)

const modelVersion = ref('pcb_aoi_v1.0.0')
const modelOptions = ref([])
const modelLoading = ref(false)

const videoSuffixes = [
  '.mp4',
  '.avi',
  '.mov',
  '.mkv',
  '.wmv',
  '.flv',
]

function makeId() {
  return `${Date.now()}-${Math.random()}`
}

function usePrompt(text) {
  inputText.value = text
}

function resetChat() {
  currentSessionId.value = null
  messages.value = []
  inputText.value = ''
  selectedFiles.value = []
}

async function loadModelOptions() {
  modelLoading.value = true

  try {
    const res = await getModelVersions()
    const payload = res?.data || res || {}
    const data = payload.data || payload

    modelOptions.value = Array.isArray(data) ? data : []

    const activeRes = await getActiveModel()
    const activePayload = activeRes?.data || activeRes || {}
    const activeData = activePayload.data || activePayload

    if (activeData?.model_name) {
      modelVersion.value = activeData.model_name
      return
    }

    const activeModel = modelOptions.value.find(item => item.is_default)

    if (activeModel) {
      modelVersion.value = activeModel.name
    } else if (modelOptions.value.length > 0) {
      modelVersion.value = modelOptions.value[0].name
    }
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

async function handleModelVersionChange() {
  if (!modelVersion.value) {
    return
  }

  try {
    await setActiveModel(modelVersion.value)
    ElMessage.success(`当前检测模型已切换为 ${modelVersion.value}`)
  } catch (error) {
    console.error('切换模型版本失败:', error)
    ElMessage.error('切换模型版本失败')
  }
}

async function ensureSelectedModelActive() {
  if (!modelVersion.value) {
    return
  }

  await setActiveModel(modelVersion.value)
}

function handleFileChange(event) {
  const files = Array.from(event.target.files || [])

  if (files.length === 0) {
    return
  }

  selectedFiles.value = files
  event.target.value = ''
}

function removeFile(index) {
  selectedFiles.value.splice(index, 1)
}

function isVideoFile(file) {
  const name = file.name.toLowerCase()
  return videoSuffixes.some(suffix => name.endsWith(suffix))
}

function buildUserText() {
  const text = String(inputText.value || '').trim()

  if (text) {
    return text
  }

  if (selectedFiles.value.length > 0) {
    const hasZip = selectedFiles.value.some(file =>
      file.name.toLowerCase().endsWith('.zip'),
    )

    const hasVideo = selectedFiles.value.some(file => isVideoFile(file))

    if (hasZip) {
      return '请检测这个 ZIP 文件中的 PCB 图片。'
    }

    if (hasVideo) {
      return '请检测这个 PCB 视频。'
    }

    if (selectedFiles.value.length > 1) {
      return `请批量检测这 ${selectedFiles.value.length} 张 PCB 图片。`
    }

    return '请检测这张 PCB 图片。'
  }

  return ''
}

async function scrollToBottom() {
  await nextTick()

  if (messageAreaRef.value) {
    messageAreaRef.value.scrollTop = messageAreaRef.value.scrollHeight
  }
}

function inferDetectMode(toolName, result) {
  if (toolName === 'detect_video') {
    return 'video'
  }

  if (toolName === 'detect_zip') {
    return 'zip'
  }

  if (toolName === 'detect_batch') {
    return 'batch'
  }

  if (toolName === 'detect_single') {
    return 'single'
  }

  if (result?.type === 'video') {
    return 'video'
  }

  if (result?.zip_name || result?.type === 'zip') {
    return 'zip'
  }

  if (result?.results || result?.type === 'batch') {
    return 'batch'
  }

  return 'single'
}

function formatToolName(toolName) {
  const map = {
    chat_only: '普通问答',
    detect_single: '单图检测',
    detect_batch: '批量检测',
    detect_zip: 'ZIP 检测',
    detect_video: '视频检测',
  }

  return map[toolName] || toolName
}

async function saveUserMessage(content, title) {
  try {
    const res = await createChatMessage({
      session_id: currentSessionId.value,
      role: 'user',
      content,
      title,
    })

    const payload = res?.data || res || {}
    const raw = payload.data || payload

    if (raw.session_id) {
      currentSessionId.value = raw.session_id
    }
  } catch (error) {
    console.error('保存用户消息失败:', error)
    ElMessage.error('保存用户消息到 Recents 失败')
  }
}

async function saveAssistantMessage(
  content,
  title,
  {
    toolName = '',
    detectMode = '',
    resultPayload = null,
  } = {},
) {
  try {
    const res = await createChatMessage({
      session_id: currentSessionId.value,
      role: 'assistant',
      content,
      title,
      tool_name: toolName || null,
      detect_mode: detectMode || null,
      result_payload: resultPayload || null,
    })

    const payload = res?.data || res || {}
    const raw = payload.data || payload

    if (raw.session_id) {
      currentSessionId.value = raw.session_id
    }
  } catch (error) {
    console.error('保存助手消息失败:', error)
    ElMessage.error('保存助手消息到 Recents 失败')
  }
}

async function handleSend() {
  const userText = buildUserText()

  if (!userText || sending.value) {
    return
  }

  const filesForRequest = [...selectedFiles.value]

  const fileNames = filesForRequest.map(file => ({
    name: file.name,
  }))

  inputText.value = ''
  selectedFiles.value = []
  sending.value = true

  const title = userText.slice(0, 30)

  const userMessage = {
    id: makeId(),
    role: 'user',
    content: userText,
    files: fileNames,
  }

  const assistantMessage = {
    id: makeId(),
    role: 'assistant',
    content: '',
    statusText: '正在连接智能检测 Agent...',
    toolName: '',
    detectionResult: null,
    detectMode: 'single',
  }

  messages.value.push(userMessage)
  messages.value.push(assistantMessage)

  await scrollToBottom()
  await saveUserMessage(userText, title)

  let finalText = ''
  let latestTool = ''
  let latestResult = null

  try {
    await ensureSelectedModelActive()

    await streamChat({
      message: userText,
      files: filesForRequest,
      conf: conf.value,
      iou: iou.value,
      device: '0',
      async onEvent(event) {
        if (event.type === 'thinking') {
          assistantMessage.statusText = event.content || '正在思考...'
        }

        if (event.type === 'tool_call') {
          latestTool = event.tool
          assistantMessage.toolName = event.tool
          assistantMessage.statusText = `正在调用工具：${formatToolName(event.tool)}`
        }

        if (event.type === 'tool_result') {
          latestTool = event.tool
          latestResult = event.result

          assistantMessage.toolName = event.tool
          assistantMessage.detectionResult = event.result
          assistantMessage.detectMode = inferDetectMode(event.tool, event.result)
          assistantMessage.statusText = '检测工具已返回结果，正在生成总结...'
        }

        if (event.type === 'text_chunk') {
          assistantMessage.statusText = ''
          assistantMessage.content += event.content || ''
          finalText += event.content || ''
        }

        if (event.type === 'done') {
          assistantMessage.statusText = ''

          if (event.content && !assistantMessage.content) {
            assistantMessage.content = event.content
            finalText = event.content
          }

          if (event.result && !assistantMessage.detectionResult) {
            latestResult = event.result
            assistantMessage.detectionResult = event.result
            assistantMessage.detectMode = inferDetectMode(event.tool, event.result)
          }

          latestTool = event.tool || latestTool
        }

        if (event.type === 'error') {
          assistantMessage.statusText = ''
          assistantMessage.content = event.content || '处理失败'
          ElMessage.error('Agent 处理失败')
        }

        await scrollToBottom()
      },
    })

    const savedToolName =
      latestTool && latestTool !== 'chat_only'
        ? latestTool
        : ''

    await saveAssistantMessage(
      finalText || assistantMessage.content || '处理完成',
      title,
      {
        toolName: savedToolName,
        detectMode: savedToolName ? assistantMessage.detectMode : '',
        resultPayload: latestResult
          ? {
              ...latestResult,
              model_version: modelVersion.value,
            }
          : null,
      },
    )

    window.dispatchEvent(new Event('history-updated'))
  } catch (error) {
    console.error('流式对话失败:', error)

    assistantMessage.statusText = ''
    assistantMessage.content = `处理失败：${error.message || '请检查后端 SSE 接口'}`
    ElMessage.error('流式对话失败')
  } finally {
    sending.value = false
    await scrollToBottom()
  }
}

async function loadSession(sessionId) {
  if (!sessionId) {
    return
  }

  try {
    const res = await getChatSessionDetail(sessionId)
    const payload = res?.data || res || {}
    const raw = payload.data || payload

    currentSessionId.value = Number(sessionId)

    messages.value = (raw.messages || []).map(item => ({
      id: makeId(),
      role: item.role || 'assistant',
      content: item.content || '',
      files: [],
      statusText: '',
      toolName: item.tool_name || '',
      detectionResult: item.result_payload || null,
      detectMode: item.detect_mode || inferDetectMode(item.tool_name, item.result_payload),
    }))

    await scrollToBottom()
  } catch (error) {
    console.error('加载历史会话失败:', error)
    ElMessage.error('加载历史会话失败')
  }
}

watch(
  () => route.query.session_id,
  value => {
    if (value) {
      loadSession(value)
    }
  },
)

watch(
  () => route.query.new,
  value => {
    if (value) {
      resetChat()
    }
  },
)

onMounted(() => {
  loadModelOptions()

  const pendingQuestion = localStorage.getItem('guest_pending_question')

  if (pendingQuestion) {
    inputText.value = pendingQuestion
    localStorage.removeItem('guest_pending_question')
  }

  if (route.query.new) {
    resetChat()
    return
  }

  if (route.query.session_id) {
    loadSession(route.query.session_id)
  }
})
</script>

<style scoped>
.chat-page {
  height: calc(100vh - 118px);
  display: flex;
  flex-direction: column;
  background: #ffffff;
}

.message-area {
  flex: 1;
  overflow: auto;
  display: flex;
  justify-content: center;
}

.empty-state {
  max-width: 760px;
  text-align: center;
  margin-top: 110px;
}

.empty-icon {
  width: 46px;
  height: 46px;
  border-radius: 16px;
  background: #111827;
  color: #ffffff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 18px;
}

.empty-state h2 {
  margin: 0;
  font-size: 28px;
  color: #111827;
}

.empty-state p {
  margin: 12px 0 24px;
  color: #6b7280;
  line-height: 1.8;
}

.quick-prompts {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.quick-prompts button {
  border: 1px solid #e5e7eb;
  background: #ffffff;
  color: #374151;
  border-radius: 14px;
  padding: 13px 16px;
  text-align: left;
  cursor: pointer;
}

.quick-prompts button:hover {
  background: #f9fafb;
}

.message-list {
  width: min(980px, 100%);
  padding: 24px 0 120px;
}

.message-row {
  display: flex;
  margin-bottom: 22px;
}

.message-row.user {
  justify-content: flex-end;
}

.message-row.assistant {
  justify-content: flex-start;
}

.message-bubble {
  max-width: 78%;
  min-width: 0;
  word-break: break-word;
}

.message-row.user .message-bubble {
  background: #f3f4f6;
  color: #111827;
  border-radius: 18px;
  padding: 12px 16px;
  max-width: 68%;
}

.message-row.assistant .message-bubble {
  color: #111827;
  line-height: 1.8;
  max-width: 88%;
}

.message-text {
  color: inherit;
  line-height: 1.8;
  white-space: pre-wrap;
}

.status-line {
  display: inline-flex;
  margin-top: 4px;
  color: #6b7280;
  font-size: 13px;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 999px;
  padding: 6px 12px;
}

.tool-line {
  display: inline-flex;
  margin-top: 8px;
  color: #2563eb;
  font-size: 13px;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 999px;
  padding: 6px 12px;
}

.attached-files {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}

.attached-file {
  height: 28px;
  border-radius: 999px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  color: #374151;
  font-size: 12px;
  display: inline-flex;
  align-items: center;
  padding: 0 10px;
}

.message-row.assistant .attached-file {
  background: #f3f4f6;
}

.composer-shell {
  width: min(980px, 100%);
  margin: 0 auto;
}

.file-list {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}

.file-chip {
  height: 30px;
  border-radius: 999px;
  background: #f3f4f6;
  color: #374151;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 0 10px;
  font-size: 13px;
}

.file-chip button {
  border: none;
  background: transparent;
  cursor: pointer;
  color: #6b7280;
}

.composer {
  border: 1px solid #e5e7eb;
  background: #ffffff;
  border-radius: 26px;
  padding: 10px;
  display: flex;
  align-items: flex-end;
  gap: 10px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
}

.upload-btn {
  width: 34px;
  height: 34px;
  border: 1px solid #e5e7eb;
  border-radius: 999px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  position: relative;
  flex-shrink: 0;
}

.upload-btn input {
  display: none;
}

.composer textarea {
  flex: 1;
  min-height: 34px;
  max-height: 140px;
  border: none;
  outline: none;
  resize: none;
  font-family: inherit;
  font-size: 14px;
  line-height: 1.6;
}

.param-group {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.param-group label {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #6b7280;
  font-size: 12px;
}

.param-group input {
  width: 56px;
  height: 30px;
  border: 1px solid #e5e7eb;
  border-radius: 999px;
  padding: 0 8px;
  outline: none;
  font-size: 12px;
}

.chat-model-select {
  flex-shrink: 0;
  display: flex;
  align-items: center;
}

.chat-model-select select {
  height: 34px;
  width: 150px;
  border: 1px solid #e5e7eb;
  border-radius: 999px;
  background: #f9fafb;
  color: #374151;
  padding: 0 10px;
  outline: none;
  font-size: 13px;
  cursor: pointer;
}

.chat-model-select select:disabled {
  color: #9ca3af;
  cursor: not-allowed;
}

.send-btn {
  height: 34px;
  border: none;
  border-radius: 999px;
  background: #111827;
  color: #ffffff;
  padding: 0 18px;
  cursor: pointer;
  flex-shrink: 0;
}

.send-btn:disabled {
  background: #d1d5db;
  cursor: not-allowed;
}

.composer-tip {
  color: #9ca3af;
  font-size: 12px;
  text-align: center;
  margin: 8px 0 0;
}

@media (max-width: 900px) {
  .quick-prompts {
    grid-template-columns: 1fr;
  }

  .composer {
    flex-wrap: wrap;
  }

  .param-group {
    width: auto;
  }

  .chat-model-select {
    flex: 1;
  }

  .chat-model-select select {
    width: 100%;
  }

  .message-row.user .message-bubble,
  .message-row.assistant .message-bubble {
    max-width: 92%;
  }
}
</style>