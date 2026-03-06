// frontend/src/lib/api.ts
import axios from 'axios'

export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || '/api',
})

api.interceptors.request.use((config) => {
  try {
    const token = localStorage.getItem('auth-storage')
    if (token) {
      const auth = JSON.parse(token)
      if (auth?.state?.token) {
        config.headers.Authorization = `Bearer ${auth.state.token}`
      }
    }
  } catch {
    localStorage.removeItem('auth-storage')
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Normalize FastAPI validation errors (array of objects) to string to prevent React rendering issues
    if (error.response?.data?.detail && Array.isArray(error.response.data.detail)) {
      try {
        error.response.data.detail = error.response.data.detail
          .map((d: any) => `${d.loc?.join('.') || 'Error'}: ${d.msg || ''}`)
          .join('; ')
      } catch (e) {
        // Fallback if parsing fails
      }
    }

    if (error.response?.status === 401) {
      const token = localStorage.getItem('auth-storage')
      if (token) {
        localStorage.removeItem('auth-storage')
        if (typeof window !== 'undefined') {
          const match = window.location.pathname.match(/^\/([a-z]{2})(\/|$)/)
          const locale = match ? match[1] : 'en'
          if (!window.location.pathname.includes('/login')) {
            window.location.href = `/${locale}/login`
          }
        }
      }
    }
    return Promise.reject(error)
  }
)

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

export interface MCPConfig {
  id: number
  name: string
  url: string
  mcp_type: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export const mcpApi = {
  list: () => api.get<MCPConfig[]>('/mcp'),
  create: (data: { name: string; url: string; mcp_type?: string; is_active?: boolean }) =>
    api.post<MCPConfig>('/mcp', data),
  update: (id: number, data: { name?: string; url?: string; mcp_type?: string; is_active?: boolean }) =>
    api.put<MCPConfig>(`/mcp/${id}`, data),
  delete: (id: number) => api.delete(`/mcp/${id}`),
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
  import: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/graph/import', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
  },

  getNode: (uri: string) =>
    api.get(`/graph/node/${encodeURIComponent(uri)}`),
  getNeighbors: (name: string, hops: number) =>
    api.get(`/graph/neighbors?name=${encodeURIComponent(name)}&hops=${hops}`),
  findPath: (start: string, end: string) =>
    api.post('/graph/path', { start_uri: start, end_uri: end }),
  getNodesByLabel: (label: string, limit: number) =>
    api.get(`/graph/nodes?label=${encodeURIComponent(label)}&limit=${limit}`),
  getStatistics: () => api.get('/graph/statistics'),
  getSchema: () => api.get('/graph/schema'),
  clear: (clearOntology: boolean = true) =>
    api.post('/graph/clear', null, { params: { clear_ontology: clearOntology } }),

  // 搜索实例
  searchInstances: (className: string, keyword: string, filters: Record<string, any>, limit: number) =>
    api.get('/graph/instances/search', {
      params: { class_name: className, keyword, limit, ...filters }
    }),

  // 获取随机实例（初始渲染）
  getRandomInstances: (limit: number = 200) =>
    api.get('/graph/instances/random', { params: { limit } }),

  // 更新实体属性
  updateEntity: (entityType: string, entityId: string, updates: Record<string, any>) =>
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

  create: (data: { name: string; entity_type: string; dsl_content: string; is_active?: boolean; description?: string }) =>
    api.post('/api/actions', data),

  update: (name: string, data: { dsl_content: string; is_active?: boolean; description?: string }) =>
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

  triggerSyncAll: () =>
    api.post<{ status: string }>('/data-products/sync-all'),

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


// ============================================================================
// Multi-Role System Types
// ============================================================================

export type ApprovalStatus = 'pending' | 'approved' | 'rejected'
export type PageId = 'chat' | 'rules' | 'actions' | 'data-products' | 'ontology' | 'admin'

export interface UserRole {
  id: number
  user_id: number
  role_id: number
  assigned_by: number | null
  assigned_at: string
}

export interface Role {
  id: number
  name: string
  description: string | null
  is_system: boolean
  role_type: 'system' | 'business'
  created_at: string
  updated_at: string
}

export interface RoleDetail extends Role {
  page_permissions: string[]
  action_permissions: Array<{ entity_type: string; action_name: string }>
  entity_permissions: string[]
}

export interface User {
  id: number
  username: string
  email: string | null
  is_admin: boolean
  approval_status: ApprovalStatus
  approval_note: string | null
  is_password_changed: boolean
  created_at: string
}

export interface UserListResponse {
  items: User[]
  total: number
}

export interface PermissionCache {
  accessible_pages: string[]
  accessible_actions: Record<string, string[]>
  accessible_entities: string[]
  is_admin: boolean
}

export interface ResetPasswordResponse {
  message: string
  default_password: string
}

// ============================================================================
// Multi-Role System API
// ============================================================================

export const usersApi = {
  // 获取用户列表
  list: (params?: { skip?: number; limit?: number; approval_status?: string; search?: string }) =>
    api.get<UserListResponse>('/api/users', { params }),

  // 创建用户
  create: (data: { username: string; password?: string; email?: string }) =>
    api.post<User>('/api/users', data),

  // 更新用户
  update: (userId: number, data: { email?: string; is_active?: boolean }) =>
    api.put<User>(`/api/users/${userId}`, data),

  // 删除用户
  delete: (userId: number) =>
    api.delete(`/api/users/${userId}`),

  // 获取待审批用户列表
  getPendingApprovals: () =>
    api.get<UserListResponse>('/api/users/pending-approvals'),

  // 审批通过
  approve: (userId: number, note?: string) =>
    api.post(`/api/users/${userId}/approve`, { note }),

  // 审批拒绝
  reject: (userId: number, reason: string) =>
    api.post(`/api/users/${userId}/reject`, { reason }),

  // 重置密码
  resetPassword: (userId: number) =>
    api.post<ResetPasswordResponse>(`/api/users/${userId}/reset-password`),

  // 分配角色
  assignRole: (userId: number, roleId: number) =>
    api.post(`/api/users/${userId}/roles`, { role_id: roleId }),

  // 移除角色
  removeRole: (userId: number, roleId: number) =>
    api.delete(`/api/users/${userId}/roles/${roleId}`),

  // 获取用户角色
  getRoles: (userId: number) =>
    api.get<Role[]>(`/api/users/${userId}/roles`),

  // 获取当前用户权限
  getMyPermissions: () =>
    api.get<PermissionCache>('/api/users/me/permissions'),

  // 修改密码
  changePassword: (oldPassword: string, newPassword: string) =>
    api.post('/auth/change-password', { old_password: oldPassword, new_password: newPassword }),
}

export const rolesApi = {
  // 获取所有角色
  list: (roleType?: 'system' | 'business') =>
    api.get<Role[]>('/api/roles', { params: roleType ? { role_type: roleType } : {} }),

  // 获取角色详情
  get: (roleId: number) =>
    api.get<RoleDetail>(`/api/roles/${roleId}`),

  // 创建角色
  create: (data: { name: string; description?: string; role_type?: 'system' | 'business' }) =>
    api.post<Role>('/api/roles', data),

  // 更新角色
  update: (roleId: number, data: { name?: string; description?: string }) =>
    api.put<Role>(`/api/roles/${roleId}`, data),

  // 删除角色
  delete: (roleId: number) =>
    api.delete(`/api/roles/${roleId}`),

  // 页面权限
  getPagePermissions: (roleId: number) =>
    api.get<string[]>(`/api/roles/${roleId}/permissions/pages`),

  addPagePermission: (roleId: number, pageId: string) =>
    api.post(`/api/roles/${roleId}/permissions/pages`, { page_id: pageId }),

  removePagePermission: (roleId: number, pageId: string) =>
    api.delete(`/api/roles/${roleId}/permissions/pages/${pageId}`),

  // Action权限
  getActionPermissions: (roleId: number) =>
    api.get<Array<{ entity_type: string; action_name: string }>>(`/api/roles/${roleId}/permissions/actions`),

  addActionPermission: (roleId: number, entityType: string, actionName: string) =>
    api.post(`/api/roles/${roleId}/permissions/actions`, { entity_type: entityType, action_name: actionName }),

  removeActionPermission: (roleId: number, entityType: string, actionName: string) =>
    api.delete(`/api/roles/${roleId}/permissions/actions/${entityType}/${actionName}`),

  // 实体类型权限
  getEntityPermissions: (roleId: number) =>
    api.get<string[]>(`/api/roles/${roleId}/permissions/entities`),

  addEntityPermission: (roleId: number, entityClassName: string) =>
    api.post(`/api/roles/${roleId}/permissions/entities`, { entity_class_name: entityClassName }),

  removeEntityPermission: (roleId: number, entityClassName: string) =>
    api.delete(`/api/roles/${roleId}/permissions/entities/${entityClassName}`),
}
