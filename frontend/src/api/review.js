import request from '@/utils/request'

export function getReviewTasks(params = {}) {
  return request.get('/api/review/tasks', { params })
}

export function getReviewTaskDetail(historyId) {
  return request.get(`/api/review/task/${historyId}`)
}

export function saveReviewItems(historyId, items) {
  return request.put(`/api/review/task/${historyId}/items`, { items })
}

export function getReviewStats() {
  return request.get('/api/review/stats')
}
