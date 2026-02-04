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
  stream: (query: string, token: string, conversationId?: number) => {
    return fetch(`${process.env.NEXT_PUBLIC_API_URL || '/api'}/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ query, conversation_id: conversationId }),
    })
  },
}

export interface Conversation {
  id: number
  title: string
  created_at: string
  updated_at: string
}

export interface Message {
  id: number
  role: 'user' | 'assistant'
  content: string
  extra_metadata?: {
    thinking?: string
    graph_data?: {
      nodes: any[]
      edges: any[]
    }
  }
  created_at: string
}

export interface ConversationWithMessages extends Conversation {
  messages: Message[]
}

export const conversationApi = {
  list: () => api.get<Conversation[]>('/conversations'),

  create: (title?: string) =>
    api.post<Conversation>('/conversations', { title }),

  get: (id: number) =>
    api.get<ConversationWithMessages>(`/conversations/${id}`),

  delete: (id: number) =>
    api.delete(`/conversations/${id}`),

  addMessage: (id: number, role: string, content: string, extra_metadata?: any) =>
    api.post(`/conversations/${id}/messages`, { role, content, extra_metadata }),

  generateTitle: (id: number) =>
    api.post<{ title: string }>(`/conversations/${id}/generate-title`),
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
  clear: () => api.post('/graph/clear'),

  // 搜索实例
  searchInstances: (className: string, keyword: string, filters: Record<string, any>, limit: number, token: string) =>
    api.get('/graph/instances/search', {
      params: { class_name: className, keyword, limit, ...filters }
    }),

  // 更新实体属性
  updateEntity: (entityType: string, entityId: string, updates: Record<string, any>, token: string) =>
    api.put(`/graph/entities/${encodeURIComponent(entityType)}/${encodeURIComponent(entityId)}`, updates),
}

// Rule and Action Types
export interface RuleInfo {
  id: number
  name: string
  priority: number
  trigger: {
    type: string
    entity: string
    property: string | null
  }
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface RuleDetail extends RuleInfo {
  dsl_content: string
}

export interface ActionParameter {
  name: string
  type: string
  optional: boolean
}

export interface ActionRuntimeInfo {
  entity_type: string
  action_name: string
  parameters: ActionParameter[]
  precondition_count: number
  has_effect: boolean
}

export interface ActionInfo {
  id: number
  name: string
  entity_type: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface ActionDetail extends ActionInfo {
  dsl_content: string
}

export const rulesApi = {
  list: () => api.get<{ rules: RuleInfo[]; count: number }>('/api/rules'),

  get: (name: string) =>
    api.get<RuleDetail>(`/api/rules/${encodeURIComponent(name)}`),

  create: (data: { name: string; dsl_content: string; priority?: number; is_active?: boolean }) =>
    api.post('/api/rules', data),

  update: (name: string, data: { dsl_content: string; priority?: number; is_active?: boolean }) =>
    api.put(`/api/rules/${encodeURIComponent(name)}`, data),

  delete: (name: string) =>
    api.delete(`/api/rules/${encodeURIComponent(name)}`),

  validate: (dsl_content: string) =>
    api.post('/api/rules', { name: '__validate__', dsl_content }).catch((e) => {
      // Extract validation error from response
      throw e
    }),
}

export const actionsApi = {
  list: () => api.get<{ actions: ActionInfo[]; count: number }>('/api/actions/definitions'),

  get: (name: string) =>
    api.get<ActionDetail>(`/api/actions/definitions/${encodeURIComponent(name)}`),

  create: (data: { name: string; entity_type: string; dsl_content: string; is_active?: boolean }) =>
    api.post('/api/actions', data),

  update: (name: string, data: { dsl_content: string; is_active?: boolean }) =>
    api.put(`/api/actions/definitions/${encodeURIComponent(name)}`, data),

  delete: (name: string) =>
    api.delete(`/api/actions/definitions/${encodeURIComponent(name)}`),

  listByEntityType: (entityType: string) =>
    api.get<{ actions: ActionRuntimeInfo[]; entity_type: string }>(`/api/actions/${encodeURIComponent(entityType)}`),

  execute: (entityType: string, actionName: string, entityId: string, entityData: any, params: any = {}) =>
    api.post(`/api/actions/${encodeURIComponent(entityType)}/${encodeURIComponent(actionName)}`, {
      entity_id: entityId,
      entity_data: entityData,
      params: params
    }),
}

