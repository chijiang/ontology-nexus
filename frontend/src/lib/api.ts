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

  // PostgreSQL configuration (future enhancement)
  // getPostgreSQL: () => api.get('/config/postgresql'),
  // updatePostgreSQL: (data: { uri: string; username: string; password: string; database?: string }) =>
  //   api.put('/config/postgresql', data),
  // testPostgreSQL: (data: { uri: string; username: string; password: string }) =>
  //   api.post('/config/test/postgresql', data),
}

export const chatApi = {
  stream: (query: string, token: string, conversationId?: number, mode: 'llm' | 'non-llm' = 'llm') => {
    return fetch(`${process.env.NEXT_PUBLIC_API_URL || '/api'}/chat/v2/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ query, conversation_id: conversationId, mode }),
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
  clear: (clearOntology: boolean = true) =>
    api.post('/graph/clear', null, { params: { clear_ontology: clearOntology } }),

  // 搜索实例
  searchInstances: (className: string, keyword: string, filters: Record<string, any>, limit: number, token: string) =>
    api.get('/graph/instances/search', {
      params: { class_name: className, keyword, limit, ...filters }
    }),

  // 获取随机实例（初始渲染）
  getRandomInstances: (limit: number = 200) =>
    api.get('/graph/instances/random', { params: { limit } }),

  // 更新实体属性
  updateEntity: (entityType: string, entityId: string, updates: Record<string, any>, token: string) =>
    api.put(`/graph/entities/${encodeURIComponent(entityType)}/${encodeURIComponent(entityId)}`, updates),

  // Ontology Schema 增删改查
  addClass: (name: string, label?: string, dataProperties?: string[], color?: string) =>
    api.post('/graph/ontology/classes', { name, label, data_properties: dataProperties, color }),
  updateClass: (name: string, label?: string, dataProperties?: string[], color?: string) =>
    api.put(`/graph/ontology/classes/${encodeURIComponent(name)}`, { label, data_properties: dataProperties, color }),
  deleteClass: (name: string) =>
    api.delete(`/graph/ontology/classes/${encodeURIComponent(name)}`),
  addRelationship: (source: string, type: string, target: string) =>
    api.post('/graph/ontology/relationships', { source, type, target }),
  deleteRelationship: (source: string, type: string, target: string) =>
    api.delete('/graph/ontology/relationships', { data: { source, type, target } }),
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

export interface ExecutionLog {
  id: number
  timestamp: string
  type: 'RULE' | 'ACTION'
  name: string
  entity_id: string | null
  actor_name: string | null
  actor_type: 'AI' | 'USER' | 'MCP' | 'SYSTEM' | null
  success: boolean
  detail: any
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
  has_call: boolean
  description?: string
}

export interface ActionInfo {
  id: number
  name: string
  entity_type: string
  is_active: boolean
  has_call?: boolean
  description?: string
  created_at: string
  updated_at: string
}

export interface ActionDetail extends ActionInfo {
  dsl_content: string
  description?: string
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

  listLogs: (limit: number = 100) =>
    api.get<{ logs: ExecutionLog[] }>('/api/rules/logs', { params: { limit } }),
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

// ============================================================================
// Data Product Types
// ============================================================================

export type ConnectionStatus = 'unknown' | 'connected' | 'disconnected' | 'error'
export type SyncDirection = 'pull' | 'push' | 'bidirectional'

export interface DataProduct {
  id: number
  name: string
  description: string | null
  grpc_host: string
  grpc_port: number
  service_name: string
  connection_status: ConnectionStatus
  last_health_check: string | null
  last_error: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface EntityMapping {
  id: number
  data_product_id: number
  ontology_class_name: string
  grpc_message_type: string
  list_method: string | null
  get_method: string | null
  create_method: string | null
  update_method: string | null
  delete_method: string | null
  sync_enabled: boolean
  sync_direction: SyncDirection
  id_field_mapping: string
  name_field_mapping: string
  created_at: string
  updated_at: string
  property_mapping_count: number
}

export interface PropertyMapping {
  id: number
  entity_mapping_id: number
  ontology_property: string
  grpc_field: string
  transform_expression: string | null
  inverse_transform: string | null
  is_required: boolean
  sync_on_update: boolean
  created_at: string
}

export interface RelationshipMapping {
  id: number
  source_entity_mapping_id: number
  target_entity_mapping_id: number
  ontology_relationship: string
  source_fk_field: string
  target_id_field: string
  sync_enabled: boolean
  created_at: string
  source_ontology_class: string | null
  target_ontology_class: string | null
}

export interface GrpcMethodInfo {
  name: string
  input_type: string
  output_type: string
  is_streaming: boolean
}

export interface GrpcServiceSchema {
  service_name: string
  methods: GrpcMethodInfo[]
  message_types: any[]
}

export interface ConnectionTestResult {
  success: boolean
  message: string
  latency_ms: number | null
}

export interface SyncResult {
  success: boolean
  records_processed: number
  records_created: number
  records_updated: number
  records_failed: number
  errors: string[]
  duration_ms: number
}

// ============================================================================
// Data Product API
// ============================================================================

export const dataProductsApi = {
  // CRUD
  list: (activeOnly = false) =>
    api.get<{ items: DataProduct[]; total: number }>('/data-products', { params: { active_only: activeOnly } }),

  get: (id: number) =>
    api.get<DataProduct>(`/data-products/${id}`),

  create: (data: {
    name: string
    description?: string
    grpc_host: string
    grpc_port: number
    service_name: string
    proto_content?: string
    is_active?: boolean
  }) => api.post<DataProduct>('/data-products', data),

  update: (id: number, data: {
    name?: string
    description?: string
    grpc_host?: string
    grpc_port?: number
    service_name?: string
    proto_content?: string
    is_active?: boolean
  }) => api.put<DataProduct>(`/data-products/${id}`, data),

  delete: (id: number) =>
    api.delete(`/data-products/${id}`),

  // Connection & Schema
  testConnection: (id: number) =>
    api.post<ConnectionTestResult>(`/data-products/${id}/test-connection`),

  getSchema: (id: number) =>
    api.get<GrpcServiceSchema>(`/data-products/${id}/schema`),

  getMethods: (id: number) =>
    api.get<{ methods: any[] }>(`/data-products/${id}/methods`),

  // Entity mappings for a product
  getEntityMappings: (id: number) =>
    api.get<{ items: EntityMapping[]; total: number }>(`/data-products/${id}/entity-mappings`),

  // Synchronization
  triggerSync: (id: number) =>
    api.post<SyncLogResponse>(`/data-products/${id}/sync`),

  getSyncLogs: (id: number, limit = 50) =>
    api.get<SyncLogResponse[]>(`/data-products/${id}/sync-logs`, { params: { limit } }),
}

export interface SyncLogResponse {
  id: number
  data_product_id: number | null
  entity_mapping_id: number | null
  sync_type: string
  direction: string
  status: string
  records_processed: number
  records_created: number
  records_updated: number
  records_failed: number
  error_message: string | null
  started_at: string
  completed_at: string | null
}


// ============================================================================
// Data Mappings API
// ============================================================================

export const dataMappingsApi = {
  // Entity Mappings
  createEntityMapping: (data: {
    data_product_id: number
    ontology_class_name: string
    grpc_message_type: string
    list_method?: string
    get_method?: string
    create_method?: string
    update_method?: string
    delete_method?: string
    sync_enabled?: boolean
    sync_direction?: SyncDirection
    id_field_mapping?: string
    name_field_mapping?: string
  }) => api.post<EntityMapping>('/data-mappings/entity-mappings', data),

  listEntityMappings: (dataProductId?: number, ontologyClassName?: string) =>
    api.get<EntityMapping[]>('/data-mappings/entity-mappings', {
      params: { data_product_id: dataProductId, ontology_class_name: ontologyClassName }
    }),

  getEntityMapping: (id: number) =>
    api.get<EntityMapping>(`/data-mappings/entity-mappings/${id}`),

  updateEntityMapping: (id: number, data: {
    grpc_message_type?: string
    list_method?: string
    get_method?: string
    create_method?: string
    update_method?: string
    delete_method?: string
    sync_enabled?: boolean
    sync_direction?: SyncDirection
    id_field_mapping?: string
    name_field_mapping?: string
  }) => api.put<EntityMapping>(`/data-mappings/entity-mappings/${id}`, data),

  deleteEntityMapping: (id: number) =>
    api.delete(`/data-mappings/entity-mappings/${id}`),

  // Property Mappings
  createPropertyMapping: (entityMappingId: number, data: {
    ontology_property: string
    grpc_field: string
    transform_expression?: string
    inverse_transform?: string
    is_required?: boolean
    sync_on_update?: boolean
  }) => api.post<PropertyMapping>(`/data-mappings/entity-mappings/${entityMappingId}/properties`, data),

  listPropertyMappings: (entityMappingId: number) =>
    api.get<PropertyMapping[]>(`/data-mappings/entity-mappings/${entityMappingId}/properties`),

  updatePropertyMapping: (propId: number, data: {
    grpc_field?: string
    transform_expression?: string
    inverse_transform?: string
    is_required?: boolean
    sync_on_update?: boolean
  }) => api.put<PropertyMapping>(`/data-mappings/property-mappings/${propId}`, data),

  deletePropertyMapping: (propId: number) =>
    api.delete(`/data-mappings/property-mappings/${propId}`),

  // Relationship Mappings
  createRelationshipMapping: (data: {
    source_entity_mapping_id: number
    target_entity_mapping_id: number
    ontology_relationship: string
    source_fk_field: string
    target_id_field?: string
    sync_enabled?: boolean
  }) => api.post<RelationshipMapping>('/data-mappings/relationship-mappings', data),

  listRelationshipMappings: (sourceId?: number, targetId?: number) =>
    api.get<RelationshipMapping[]>('/data-mappings/relationship-mappings', {
      params: { source_entity_mapping_id: sourceId, target_entity_mapping_id: targetId }
    }),

  deleteRelationshipMapping: (id: number) =>
    api.delete(`/data-mappings/relationship-mappings/${id}`),
}
