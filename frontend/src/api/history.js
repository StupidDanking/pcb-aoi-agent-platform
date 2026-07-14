import request from '@/utils/request'

export function getRecentHistories(params = {}) {
  return request.get('/api/history/recent', { params })
}

export function searchHistories(keyword, limit = 20) {
  return request.get('/api/history/search', {
    params: {
      keyword,
      limit,
    },
  })
}

export function createChatSession(data) {
  return request.post('/api/history/chat/session', data)
}

export function createChatMessage(data) {
  return request.post('/api/history/chat/message', data)
}

export function getChatSessionDetail(sessionId) {
  return request.get(`/api/history/chat/session/${sessionId}`)
}

export function createDetectionTaskHistory(data) {
  return request.post('/api/history/detection/task', data)
}

export function getDetectionTaskDetail(taskId) {
  return request.get(`/api/history/detection/task/${taskId}`)
}

export function deleteHistoryRecord(recordId) {
  return request.delete(`/api/history/${recordId}`)
}