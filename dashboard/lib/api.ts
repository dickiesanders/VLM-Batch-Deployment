const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080'

export async function fetchAPI(
  endpoint: string,
  options: RequestInit = {}
) {
  const apiKey = typeof window !== 'undefined'
    ? localStorage.getItem('api_key')
    : ''

  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': apiKey || '',
      ...options.headers,
    },
  })

  if (!res.ok) {
    throw new Error(`API error: ${res.status}`)
  }

  return res.json()
}

// OCR
export const extractOCR = (data: any) =>
  fetchAPI('/ocr/extract', { method: 'POST', body: JSON.stringify(data) })

export const getJob = (jobId: string) =>
  fetchAPI(`/ocr/job/${jobId}`)

// Schemas
export const listSchemas = () => fetchAPI('/schemas')
export const createSchema = (data: any) =>
  fetchAPI('/schemas', { method: 'POST', body: JSON.stringify(data) })
export const deleteSchema = (id: string) =>
  fetchAPI(`/schemas/${id}`, { method: 'DELETE' })

// Models
export const listModels = () => fetchAPI('/models')
export const registerModel = (data: any) =>
  fetchAPI('/models', { method: 'POST', body: JSON.stringify(data) })
export const deleteModel = (id: string) =>
  fetchAPI(`/models/${id}`, { method: 'DELETE' })

// Health
export const getHealth = () => fetchAPI('/health')
