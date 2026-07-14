import request from '@/utils/request'

export function detectSingleImage(formData) {
  return request.post('/api/detection/single', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
}

export function detectBatchImages(formData) {
  return request.post('/api/detection/batch', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
}

export function detectZipImages(formData) {
  return request.post('/api/detection/zip', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
}

export function detectVideo(formData) {
  return request.post('/api/detection/video', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    timeout: 180000,
  })
}