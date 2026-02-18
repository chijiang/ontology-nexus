# 多角色系统设计文档

**创建日期:** 2025-02-18
**状态:** 已批准

## 概述

为平台添加完整的多角色功能，包括角色管理、用户审批、页面访问控制、Action权限控制、实体类型可见性控制和密码重置功能。

## 需求总结

| 需求项 | 说明 |
|--------|------|
| Admin识别 | 通过User.is_admin字段标识 |
| 用户审批 | 注册后需要admin审批才能登录 |
| 页面访问控制 | 按功能模块级别控制 |
| Action权限 | 按具体action名称控制 |
| 实体类型可见性 | 全面应用（Ontology、数据映射、数据查询） |
| 密码重置 | 重置为固定默认密码，强制用户首次登录修改 |

---

## 1. 数据库模型设计

### 1.1 User模型（修改）

```python
class User(Base):
    __tablename__ = "users"

    id: int                               # 主键
    username: str                          # 用户名（唯一）
    password_hash: str                     # 密码哈希
    email: str | None                      # 邮箱
    is_active: bool                        # 是否激活（现有）
    is_admin: bool                         # 是否管理员（新增）
    approval_status: str                   # 审批状态：pending/approved/rejected（新增）
    approval_note: str | None              # 审批备注（新增）
    approved_by: int | None                # 审批人ID（新增）
    approved_at: datetime | None           # 审批时间（新增）
    is_password_changed: bool              # 是否已修改默认密码（新增）
    created_at: datetime
    updated_at: datetime
```

### 1.2 Role模型（新增）

```python
class Role(Base):
    __tablename__ = "roles"

    id: int                               # 主键
    name: str                             # 角色名称（唯一）
    description: str | None               # 角色描述
    is_system: bool                       # 是否系统内置角色
    created_at: datetime
    updated_at: datetime
```

### 1.3 UserRole关联表（新增）

```python
class UserRole(Base):
    __tablename__ = "user_roles"

    id: int                               # 主键
    user_id: int                          # 用户ID
    role_id: int                          # 角色ID
    assigned_by: int | None               # 分配人ID
    assigned_at: datetime                 # 分配时间
```

### 1.4 RolePagePermission（新增）

```python
class RolePagePermission(Base):
    __tablename__ = "role_page_permissions"

    id: int                               # 主键
    role_id: int                          # 角色ID
    page_id: str                          # 功能模块ID
```

### 1.5 RoleActionPermission（新增）

```python
class RoleActionPermission(Base):
    __tablename__ = "role_action_permissions"

    id: int                               # 主键
    role_id: int                          # 角色ID
    entity_type: str                      # 实体类型
    action_name: str                      # Action名称
```

### 1.6 RoleEntityPermission（新增）

```python
class RoleEntityPermission(Base):
    __tablename__ = "role_entity_permissions"

    id: int                               # 主键
    role_id: int                          # 角色ID
    entity_class_name: str                # Ontology类名
```

### 1.7 功能模块枚举

| page_id | 说明 |
|---------|------|
| chat | 聊天对话 |
| rules | 规则管理 |
| actions | 动作管理 |
| data-products | 数据产品管理 |
| ontology | 本体管理 |
| admin | 系统管理（用户、角色等） |

---

## 2. API设计

### 2.1 用户管理API (`/api/users`)

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/api/users` | 获取用户列表（支持筛选、分页） | admin |
| POST | `/api/users` | 创建用户 | admin |
| PUT | `/api/users/{user_id}` | 更新用户 | admin |
| DELETE | `/api/users/{user_id}` | 删除用户 | admin |
| POST | `/api/users/{user_id}/reset-password` | 重置用户密码 | admin |
| GET | `/api/users/pending-approvals` | 获取待审批用户列表 | admin |
| POST | `/api/users/{user_id}/approve` | 审批通过 | admin |
| POST | `/api/users/{user_id}/reject` | 审批拒绝 | admin |
| POST | `/api/users/{user_id}/roles` | 分配角色 | admin |
| DELETE | `/api/users/{user_id}/roles/{role_id}` | 移除角色 | admin |
| GET | `/api/users/me/permissions` | 获取当前用户权限缓存 | 登录用户 |

### 2.2 角色管理API (`/api/roles`)

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/api/roles` | 获取所有角色 | 登录用户 |
| POST | `/api/roles` | 创建角色 | admin |
| PUT | `/api/roles/{role_id}` | 更新角色 | admin |
| DELETE | `/api/roles/{role_id}` | 删除角色 | admin |
| GET | `/api/roles/{role_id}/detail` | 获取角色详情（包含权限） | 登录用户 |

### 2.3 权限管理API

#### 页面权限

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/roles/{role_id}/permissions/pages` | 获取页面权限 |
| POST | `/api/roles/{role_id}/permissions/pages` | 添加页面权限 |
| DELETE | `/api/roles/{role_id}/permissions/pages/{page_id}` | 删除页面权限 |

#### Action权限

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/roles/{role_id}/permissions/actions` | 获取Action权限 |
| POST | `/api/roles/{role_id}/permissions/actions` | 添加Action权限 |
| DELETE | `/api/roles/{role_id}/permissions/actions/{entity_type}/{action_name}` | 删除Action权限 |

#### 实体类型权限

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/roles/{role_id}/permissions/entities` | 获取实体类型权限 |
| POST | `/api/roles/{role_id}/permissions/entities` | 添加实体类型权限 |
| DELETE | `/api/roles/{role_id}/permissions/entities/{entity_class_name}` | 删除实体类型权限 |

### 2.4 修改的API

**注册接口 (`POST /auth/register`)**
```python
# 新用户注册后状态为pending，不返回token
# Response: { "message": "Registration pending approval", "user_id": 123 }
```

**登录接口 (`POST /auth/login`)**
```python
# 检查approval_status和is_active
# 只有approved且active的用户才能获取token
# Error responses:
# - 403 "Registration pending approval"
# - 403 "Registration rejected: {reason}"
# - 403 "Account is inactive"
```

---

## 3. 前端设计

### 3.1 类型定义

```typescript
// 扩展 User 接口
interface User {
  id: number
  username: string
  email?: string
  is_admin: boolean
  approval_status: 'pending' | 'approved' | 'rejected'
  is_password_changed: boolean
}

interface Role {
  id: number
  name: string
  description?: string
  is_system: boolean
}

// 权限信息缓存
interface PermissionCache {
  accessible_pages: string[]
  accessible_actions: Record<string, string[]>  // { entity_type: [action_names] }
  accessible_entities: string[]
}
```

### 3.2 新增页面路由

| 路由 | 说明 | 权限 |
|------|------|------|
| `/admin/users` | 用户管理 | admin |
| `/admin/roles` | 角色管理 | admin |
| `/admin/roles/:id` | 角色详情和权限配置 | admin |

### 3.3 新增组件

| 组件 | 说明 |
|------|------|
| `UserList` | 用户列表（支持筛选、分页） |
| `UserCreateForm` | 创建用户表单 |
| `UserApprovalList` | 待审批用户列表 |
| `RoleList` | 角色列表 |
| `RoleForm` | 角色表单 |
| `RolePermissionEditor` | 角色权限编辑器（页面、Action、实体类型三个tab） |
| `ResetPasswordButton` | 重置密码按钮 |
| `ChangePasswordForm` | 修改密码表单（首次登录强制） |

### 3.4 权限控制组件

**HOC: `withPageAccess`**
```typescript
export function withPageAccess(pageId: string) {
  return function(Component: React.ComponentType) {
    return function ProtectedPage(props: Props) {
      const { accessiblePages } = usePermissions()
      if (!accessiblePages.includes(pageId)) {
        return <AccessDeniedPage />
      }
      return <Component {...props} />
    }
  }
}
```

**Hook: `usePermissions`**
```typescript
export function usePermissions() {
  // 登录后获取权限缓存
  // 提供检查函数: hasPageAccess, hasActionPermission, hasEntityAccess
  return { accessiblePages, accessibleActions, accessibleEntities, checkAccess }
}
```

### 3.5 导航菜单控制

根据用户权限动态显示菜单项，检查`accessible_pages`。

---

## 4. 数据流和权限检查

### 4.1 登录流程

```
用户登录 → 验证凭证 → 检查approval_status → 生成JWT → 返回Token
                                                        ↓
                                    前端调用/api/users/me/permissions
                                                        ↓
                                            存入Zustand开始正常使用
```

### 4.2 页面访问检查

```
前端: 检查accessible_pages → 显示页面或拒绝页面
  ↓
后端: (可选)中间件再次验证 → 返回数据或403
```

### 4.3 Action执行检查

```
前端: 检查accessible_actions → 显示/隐藏按钮
  ↓
点击执行 → 后端验证权限 → 执行或403
```

### 4.4 实体类型过滤

- **Ontology页面**: 后端过滤类列表
- **数据映射配置**: 前端下拉框过滤
- **数据查询**: 后端过滤实例数据

### 4.5 密码重置流程

```
Admin点击重置 → 确认 → 更新密码哈希 → 设置is_password_changed=false
                                                ↓
                                    用户下次登录强制修改密码
```

---

## 5. 错误处理

### 5.1 错误码

| 错误码 | 说明 |
|--------|------|
| `LOGIN_PENDING_APPROVAL` | 注册待审批 |
| `LOGIN_REJECTED` | 注册被拒绝 |
| `LOGIN_INACTIVE` | 账户被禁用 |
| `PAGE_ACCESS_DENIED` | 页面无权限 |
| `ACTION_ACCESS_DENIED` | Action无权限 |
| `ENTITY_ACCESS_DENIED` | 实体类型无权限 |
| `MUST_CHANGE_PASSWORD` | 必须修改密码 |

### 5.2 用户友好提示

- 登录被拒绝 → 显示注册被拒绝的提示和原因
- 页面无权限 → 显示友好的无权限页面
- 密码未修改 → 强制跳转到修改密码页面

---

## 6. 初始化数据

### 6.1 系统内置角色

| name | description | 初始权限 |
|------|-------------|----------|
| admin | 系统管理员 | 所有权限 |
| viewer | 查看者 | 所有页面的只读权限 |
| editor | 编辑者 | 编辑权限（不含admin） |

### 6.2 初始Admin用户

```
用户名: admin
密码: 需首次登录修改
状态: approved, is_admin=true
```

---

## 7. 测试策略

### 7.1 单元测试
- 权限检查函数
- 角色关联/解除逻辑
- 用户审批流程

### 7.2 集成测试
- 注册→审批→登录完整流程
- 权限配置→访问控制→拒绝流程
- 密码重置→修改密码流程

### 7.3 E2E测试场景
1. Admin创建角色并配置权限
2. 用户注册→Admin审批→用户登录
3. 普通用户访问受限页面被拒绝
4. Admin重置用户密码→用户登录修改密码
5. Action权限控制生效
6. 实体类型过滤生效
