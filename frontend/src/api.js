async function request(url, options = {}) {
  const res = await fetch(url, options)
  const contentType = res.headers.get('content-type') || ''
  const data = contentType.includes('json') ? await res.json() : await res.text()
  if (!res.ok) {
    const detail = (data && data.detail) ? data.detail : res.statusText
    throw new Error(detail)
  }
  return data
}

export function predict(text, model) {
  return request('/predict', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, model }),
  })
}

export function fetchModels() {
  return request('/models')
}

export function fetchDemo() {
  return request('/api/demo')
}

export function downloadTemplate() {
  window.location.href = '/api/template'
}

export function fetchReviews() {
  return request('/api/reviews')
}

export function fetchReview(id) {
  return request(`/api/reviews/${id}`)
}

export function createReview(text, model) {
  return request('/api/reviews', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, model }),
  })
}

export function updateReview(id, text, model) {
  return request(`/api/reviews/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, model }),
  })
}

export function deleteReview(id) {
  return request(`/api/reviews/${id}`, { method: 'DELETE' })
}

export function batchDelete(ids, all) {
  return request('/api/reviews/batch-delete', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ids, all }),
  })
}

export function exportReviews() {
  window.location.href = '/api/reviews/export'
}

// Batch predict: upload a CSV and consume the NDJSON streaming response.
export async function predictCsv(file, model, onProgress, onResult) {
  const form = new FormData()
  form.append('file', file)
  form.append('model', model)
  const res = await fetch('/api/predict-csv', { method: 'POST', body: form })
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error(data.detail || res.statusText)
  }
  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    let idx
    while ((idx = buffer.indexOf('\n')) >= 0) {
      const line = buffer.slice(0, idx).trim()
      buffer = buffer.slice(idx + 1)
      if (!line) continue
      const msg = JSON.parse(line)
      if (msg.type === 'progress') onProgress(msg)
      else if (msg.type === 'result') onResult(msg)
      else if (msg.type === 'error') throw new Error(msg.detail)
    }
  }
}
