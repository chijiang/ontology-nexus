// frontend/src/lib/api.ts
import axios from 'axios'

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || '/api',
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth-storage')
  if (token) {
    const auth = JSON.parse(token)
    if (auth.state.token) {
      config.headers.Authorization = `Bearer ${auth.state.token}`
    }
  }
  return config
})

export const authApi = {
  register: (username: string, password: string, email?: string) =>
    api.post('/auth/register', { username, password, email }),

  login: (username: string, password: string) =>
    api.post('/auth/login', { username, password }),
}

export const configApi = {
  getLLM: () => api.get('/config/llm'),
  updateLLM: (data: { api_key: string; base_url: string; model: string }) =>
    api.put('/config/llm', data),
  testLLM: (data: { api_key: string; base_url: string; model: string }) =>
    api.post('/config/test/llm', data),

  getNeo4j: () => api.get('/config/neo4j'),
  updateNeo4j: (data: { uri: string; username: string; password: string; database?: string }) =>
    api.put('/config/neo4j', data),
  testNeo4j: (data: { uri: string; username: string; password: string }) =>
    api.post('/config/test/neo4j', data),
}

export const chatApi = {
  stream: (query: string, token: string) => {
    return fetch(`${process.env.NEXT_PUBLIC_API_URL || '/api'}/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ query }),
    })
  },
}

export const graphApi = {
  import: (file: File, token: string) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/graph/import', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
  },

  getNode: (uri: string, token: string) =>
    api.get(`/graph/node/${encodeURIComponent(uri)}`),
  getNeighbors: (name: string, hops: number, token: string) =>
    api.get(`/graph/neighbors?name=${encodeURIComponent(name)}&hops=${hops}`),
  findPath: (start: string, end: string, token: string) =>
    api.post('/graph/path', { start_uri: start, end_uri: end }),
  getNodesByLabel: (label: string, limit: number, token: string) =>
    api.get(`/graph/nodes?label=${encodeURIComponent(label)}&limit=${limit}`),
  getStatistics: (token: string) => api.get('/graph/statistics'),
  getSchema: (token: string) => api.get('/graph/schema'),
}
