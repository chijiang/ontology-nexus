# CLAUDE.md - Ontology-Nexus 项目开发指南 / Project Development Guide

[中文](#中文) | [English](#english)

---

<a name="中文"></a>
## 中文版

### 项目概述

Ontology-Nexus（KG-Agent）是一个本体优先的智能平台，用于语义推理和自动化。基于 PostgreSQL 知识图谱，采用 FastAPI 后端、Next.js 前端和自定义 DSL 规则引擎。

### 技术栈

- **后端**: Python 3.11+, FastAPI, SQLAlchemy (async), PostgreSQL (asyncpg), LangChain/LangGraph, Lark (DSL 解析器), gRPC, FastMCP
- **前端**: Next.js 16 (App Router), TypeScript 5, React 19, TailwindCSS, Shadcn UI, Zustand, Cytoscape.js, next-intl (国际化)
- **基础设施**: Docker Compose, PostgreSQL 17, Alembic (数据库迁移)
- **包管理**: UV (后端), PNPM (前端)

### 项目结构

```
ontology-nexus/
├── backend/
│   ├── app/
│   │   ├── api/            # REST API 路由 (auth, chat, graph, rules, actions 等)
│   │   ├── core/           # 配置、安全、数据库
│   │   ├── models/         # SQLAlchemy ORM 模型
│   │   ├── schemas/        # Pydantic 请求/响应模型
│   │   ├── services/       # 业务逻辑 (agent, sync, grpc, graph storage)
│   │   ├── repositories/   # 数据访问层
│   │   ├── rule_engine/    # 自定义 DSL 解析器、规则/动作注册表、执行器
│   │   ├── mcp/            # MCP 服务实现
│   │   └── main.py         # 应用入口（lifespan 生命周期）
│   ├── alembic/            # 数据库迁移
│   ├── erp_emulator/       # gRPC ERP 模拟器（测试用）
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── app/[locale]/   # 国际化页面 (dashboard, graph, rules, admin 等)
│   │   ├── components/     # React 组件 (chat, graph viewers, panels)
│   │   ├── lib/            # API 客户端、认证 store、工具函数
│   │   ├── i18n/           # 国际化配置
│   │   └── messages/       # 翻译文件 (en, zh)
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
└── .env.example
```

### 常用命令

#### 后端
```bash
cd backend
uv sync                          # 安装依赖
uv run uvicorn app.main:app --reload  # 启动开发服务器 (端口 8000)
uv run alembic upgrade head      # 运行数据库迁移
uv run pytest                    # 运行测试
uv run ruff check .              # 代码检查
```

#### 前端
```bash
cd frontend
pnpm install                     # 安装依赖
pnpm dev                         # 启动开发服务器 (端口 3000)
pnpm build                       # 生产构建
pnpm lint                        # 代码检查
```

#### Docker
```bash
cp .env.example .env             # 配置环境变量
docker-compose up --build        # 启动所有服务
```

### 架构说明

#### 认证与授权
- 基于 JWT 认证 (python-jose)，Token 存储在 Zustand + localStorage
- RBAC 角色权限：页面权限、动作权限、实体权限
- `get_current_user` 依赖检查 `is_active` 和 `approval_status`
- `require_admin` 依赖用于破坏性/管理端点
- 密码验证：至少 8 位，需包含字母和数字

#### 数据库
- 异步 SQLAlchemy + asyncpg 驱动，启用 `pool_pre_ping=True`
- 所有 datetime 列使用 `datetime.now(timezone.utc)`（不用 `datetime.utcnow()`）
- `Conversation.user_id` 和 `Message.conversation_id` 外键列已建索引
- 图数据存储在 `GraphEntity` 和 `GraphRelationship` 表，属性使用 JSONB

#### API 模式
- 所有图谱本体端点使用 Pydantic 请求模型（不用原始 `dict`）
- DSL 解析错误通过 `deps.py` 中的 `handle_dsl_exception()` 统一处理
- 聊天使用 SSE 流式传输，前端配合 `AbortController`
- 文件上传验证：50MB 大小限制，允许扩展名 (.ttl, .owl, .rdf, .xml, .n3, .nt)
- 查询参数通过 `Query(ge=, le=)` 限制边界

#### 前端模式
- 使用 `useRef` 做 isMounted 检查（不用 `useState`）
- `tokenRef` 模式确保事件处理器中的闭包稳定性
- 请求计数器模式（`loadRequestIdRef`）防止竞态条件
- 不可变状态更新（展开运算符，不直接修改）
- `graphApi` 函数不接受 token 参数（axios 拦截器自动处理认证）
- `ErrorBoundary` 组件包裹图谱查看器；`error.tsx` 用于页面级错误

#### 规则引擎
- 自定义 DSL 由 Lark 语法解析
- 规则和动作存储在数据库，启动时加载到内存注册表
- 删除操作必须调用 `registry.unregister()` 保持内存状态同步
- 属性转换表达式使用 `safe_eval()`（禁止使用 `eval()`）

#### Docker
- 后端和前端以非 root 用户 (`appuser`) 运行
- 所有服务配置了健康检查
- 前端使用 Next.js `output: "standalone"` 最小化镜像
- `.dockerignore` 文件排除 `.git`、`node_modules`、`__pycache__` 等

### 编码规范

- 后端日志：使用 `logger = logging.getLogger(__name__)`，禁止裸 `except:` 或静默 `pass`
- 不硬编码密钥；docker-compose 中使用 `${VAR:?required}` 环境变量
- 前端支持中英文国际化 (next-intl)；后端错误消息使用英文
- 编辑 Python 文件后始终验证语法：`python -c "import ast; ast.parse(open('file', encoding='utf-8').read())"`

### 项目特殊规则（未经用户明确同意，禁止修改以下内容）

- **默认管理员密码**: `init_db.py` 使用硬编码 `admin123` 作为开发便利。禁止替换为随机密码生成。
- **端点授权范围**: `config.py`（LLM 配置）和 `data_products.py`（数据产品 CRUD）使用 `get_current_user`，不使用 `require_admin`。这些端点有意允许所有已认证用户访问，禁止添加 `require_admin`。
- **`require_admin` 仅适用于**: 图谱本体 CRUD、图谱导入/清除、规则/动作上传/更新/删除、用户管理端点。

### 更新策略
- 每完成一项重大任务后更新 `CLAUDE.md` 和 `README.md`

---

<a name="english"></a>
## English Version

### Project Overview

Ontology-Nexus (KG-Agent) is an Ontology-First intelligent platform for semantic reasoning and automation. It uses a Knowledge Graph backed by PostgreSQL, with a FastAPI backend, Next.js frontend, and custom DSL rule engine.

### Tech Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy (async), PostgreSQL (asyncpg), LangChain/LangGraph, Lark (DSL parser), gRPC, FastMCP
- **Frontend**: Next.js 16 (App Router), TypeScript 5, React 19, TailwindCSS, Shadcn UI, Zustand, Cytoscape.js, next-intl (i18n)
- **Infrastructure**: Docker Compose, PostgreSQL 17, Alembic (migrations)
- **Package Managers**: UV (backend), PNPM (frontend)

### Project Structure

```
ontology-nexus/
├── backend/
│   ├── app/
│   │   ├── api/            # REST API routes (auth, chat, graph, rules, actions, etc.)
│   │   ├── core/           # Config, security, database
│   │   ├── models/         # SQLAlchemy ORM models
│   │   ├── schemas/        # Pydantic request/response schemas
│   │   ├── services/       # Business logic (agent, sync, grpc, graph storage)
│   │   ├── repositories/   # Data access layer
│   │   ├── rule_engine/    # Custom DSL parser, rule/action registries, executor
│   │   ├── mcp/            # MCP server implementations
│   │   └── main.py         # App entry point (lifespan lifecycle)
│   ├── alembic/            # Database migrations
│   ├── erp_emulator/       # gRPC ERP emulator (for testing)
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── app/[locale]/   # i18n pages (dashboard, graph, rules, admin, etc.)
│   │   ├── components/     # React components (chat, graph viewers, panels)
│   │   ├── lib/            # API client, auth store, utilities
│   │   ├── i18n/           # Internationalization config
│   │   └── messages/       # Translation files (en, zh)
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
└── .env.example
```

### Key Commands

#### Backend
```bash
cd backend
uv sync                          # Install dependencies
uv run uvicorn app.main:app --reload  # Start dev server (port 8000)
uv run alembic upgrade head      # Run migrations
uv run pytest                    # Run tests
uv run ruff check .              # Lint
```

#### Frontend
```bash
cd frontend
pnpm install                     # Install dependencies
pnpm dev                         # Start dev server (port 3000)
pnpm build                       # Production build
pnpm lint                        # Lint
```

#### Docker
```bash
cp .env.example .env             # Configure environment variables
docker-compose up --build        # Start all services
```

### Architecture Notes

#### Authentication & Authorization
- JWT-based auth (python-jose), tokens stored in Zustand + localStorage
- RBAC with roles: page permissions, action permissions, entity permissions
- `get_current_user` dependency checks `is_active` and `approval_status`
- `require_admin` dependency for destructive/admin endpoints
- Password validation: min 8 chars, requires letters + digits

#### Database
- Async SQLAlchemy + asyncpg driver, `pool_pre_ping=True` enabled
- All datetime columns use `datetime.now(timezone.utc)` (not `datetime.utcnow()`)
- Foreign key columns `Conversation.user_id` and `Message.conversation_id` are indexed
- Graph data stored in `GraphEntity` and `GraphRelationship` tables with JSONB properties

#### API Patterns
- All graph ontology endpoints use Pydantic request models (not raw `dict`)
- DSL parsing errors handled via shared `handle_dsl_exception()` in `deps.py`
- SSE streaming for chat with `AbortController` on frontend
- File upload validation: 50MB max, allowed extensions (.ttl, .owl, .rdf, .xml, .n3, .nt)
- Query parameter bounds enforced via `Query(ge=, le=)`

#### Frontend Patterns
- `useRef` for isMounted checks (not `useState`)
- `tokenRef` pattern for stable closure access in event handlers
- Request counter pattern (`loadRequestIdRef`) for race condition prevention
- Immutable state updates (spread operator, not mutation)
- `graphApi` functions do NOT accept token params (axios interceptor handles auth)
- `ErrorBoundary` component wraps graph viewers; `error.tsx` for page-level errors

#### Rule Engine
- Custom DSL parsed by Lark grammar
- Rules and Actions stored in DB and loaded into in-memory registries at startup
- Delete operations must call `registry.unregister()` to keep in-memory state in sync
- `safe_eval()` used for property transform expressions (no `eval()`)

#### Docker
- Backend and frontend run as non-root users (`appuser`)
- Health checks configured for all services
- Frontend uses Next.js `output: "standalone"` for minimal Docker images
- `.dockerignore` files exclude `.git`, `node_modules`, `__pycache__`, etc.

### Coding Conventions

- Backend logging: use `logger = logging.getLogger(__name__)`, never bare `except:` or silent `pass`
- No hardcoded secrets; use environment variables with `${VAR:?required}` in docker-compose
- Chinese and English i18n supported via next-intl; backend error messages use English
- Always verify Python syntax after edits: `python -c "import ast; ast.parse(open('file', encoding='utf-8').read())"`

### Project-Specific Rules (DO NOT change without explicit user approval)

- **Default admin password**: `init_db.py` uses hardcoded `admin123` for development convenience. Do NOT replace with random password generation.
- **Endpoint authorization scope**: `config.py` (LLM config) and `data_products.py` (data product CRUD) use `get_current_user`, NOT `require_admin`. These endpoints are intentionally accessible to all authenticated users. Do NOT add `require_admin` to them.
- **`require_admin` only applies to**: graph ontology CRUD, graph import/clear, rule/action upload/update/delete, user management endpoints.

### Update Policy
- Update `CLAUDE.md` and `README.md` after completing each major task
