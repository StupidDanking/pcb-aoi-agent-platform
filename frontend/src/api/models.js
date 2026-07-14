import request from '@/utils/request'

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export function getModelVersions() {
  return request.get('/api/models')
}

export function getModelDetail(version) {
  return request.get(`/api/models/${version}`)
}

export function getModelMetrics(version) {
  return request.get(`/api/models/${version}/metrics`)
}

export function getActiveModel() {
  return request.get('/api/models/active')
}

export function setActiveModel(version) {
  return request.post('/api/models/active', {
    version,
  })
}

export function getModelArtifactUrl(version, filename) {
  return `${API_BASE_URL}/api/models/${version}/artifact/${filename}`
}