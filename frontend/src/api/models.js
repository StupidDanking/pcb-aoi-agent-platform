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

export function getModelArtifactUrl(version, filename, cacheKey) {
  const bust = cacheKey || Date.now()
  return `${API_BASE_URL}/api/models/${version}/artifact/${filename}?v=${version}&t=${bust}`
}

/**
 * Fetch artifact with Authorization header.
 * Plain <img src> cannot send Bearer token, so charts broke after models API required login.
 */
export async function fetchModelArtifactObjectUrl(version, filename, cacheKey) {
  const token = localStorage.getItem('access_token')
  const url = getModelArtifactUrl(version, filename, cacheKey)

  const response = await fetch(url, {
    headers: token
      ? {
          Authorization: `Bearer ${token}`,
        }
      : {},
  })

  if (!response.ok) {
    throw new Error(`artifact ${filename} failed: ${response.status}`)
  }

  const blob = await response.blob()
  return URL.createObjectURL(blob)
}
