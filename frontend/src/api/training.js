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

export function validateModel(taskId, data) {
  return request({
    url: `/api/training/validate/${taskId}`,
    method: 'post',
    data,
  })
}

export function exportModel(taskId, data) {
  return request({
    url: `/api/training/export/${taskId}`,
    method: 'post',
    data,
  })
}

export function predictImage(formData) {
  return request({
    url: '/api/training/predict',
    method: 'post',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
}

export function getDownloadModelUrl(taskId) {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
  return `${baseUrl}/api/training/download/${taskId}`
}