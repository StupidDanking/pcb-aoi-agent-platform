import request from '@/utils/request'

export function startTraining(data) {
  return request({
    url: '/api/training/start',
    method: 'post',
    data,
  })
}

export function getTrainingTasks() {
  return request({
    url: '/api/training/tasks',
    method: 'get',
  })
}

export function getTrainingStatus(taskId) {
  return request({
    url: `/api/training/status/${taskId}`,
    method: 'get',
  })
}

export function getTrainingMetrics(taskId) {
  return request({
    url: `/api/training/metrics/${taskId}`,
    method: 'get',
  })
}

export function stopTraining(taskId) {
  return request({
    url: `/api/training/stop/${taskId}`,
    method: 'post',
  })
}