const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export async function streamChat({
  message = '',
  files = [],
  conf = 0.25,
  iou = 0.45,
  device = '0',
  onEvent,
}) {
  const token =
    localStorage.getItem('access_token') ||
    localStorage.getItem('token')

  const formData = new FormData()

  formData.append('message', message || '')
  formData.append('conf', String(conf))
  formData.append('iou', String(iou))
  formData.append('device', String(device))

  files.forEach(file => {
    formData.append('files', file)
  })

  const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: formData,
  })

  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(errorText || `请求失败：${response.status}`)
  }

  if (!response.body) {
    throw new Error('浏览器不支持流式响应')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8')

  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()

    if (done) {
      break
    }

    buffer += decoder.decode(value, { stream: true })

    const parts = buffer.split('\n\n')
    buffer = parts.pop() || ''

    for (const part of parts) {
      const dataLines = part
        .split('\n')
        .filter(line => line.startsWith('data:'))

      if (dataLines.length === 0) {
        continue
      }

      const dataText = dataLines
        .map(line => line.replace(/^data:\s?/, ''))
        .join('\n')

      if (!dataText.trim()) {
        continue
      }

      try {
        const event = JSON.parse(dataText)

        if (onEvent) {
          await onEvent(event)
        }
      } catch (error) {
        console.error('SSE 事件解析失败:', error, dataText)
      }
    }
  }

  if (buffer.trim()) {
    const dataLines = buffer
      .split('\n')
      .filter(line => line.startsWith('data:'))

    const dataText = dataLines
      .map(line => line.replace(/^data:\s?/, ''))
      .join('\n')

    if (dataText.trim()) {
      try {
        const event = JSON.parse(dataText)

        if (onEvent) {
          await onEvent(event)
        }
      } catch (error) {
        console.error('SSE 最后一段解析失败:', error, dataText)
      }
    }
  }
}