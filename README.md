# Ontology-Driven Agent (KG-Agent)

[English](#english) | [中文](#中文)

---

<a name="english"></a>
## English Version

**KG-Agent** is an **Ontology-First** intelligent platform designed for complex semantic reasoning and automation. At its core, the system is defined by a rigorous **Ontology**, while the **Knowledge Graph** serves as the dynamic realization and data organization form. By prioritizing the ontological model, KG-Agent ensures that every interaction, rule, and data synchronization is governed by a consistent semantic framework.

### Core Features

- **Ontology-First Schema Management**:
  - **Core Definition**: Move beyond flat data models; define your world through classes, properties, and complex relationships.
  - **Visual Editor**: Real-time schema manipulation supporting data types (rdfs:range) and semantic aliases.
  - **Standard Support**: Seamlessly import and export **OWL/TTL** ontology files to leverage existing semantic standards.
- **Ontology-Guided Agent**:
  - **Semantic Reasoning**: Natural language interaction that understands the underlying ontology, not just keyword matching.
  - **Agentic Extensibility**: Integrated **MCP (Model Context Protocol)** servers that expose query and action tools derived directly from your ontology.
- **Semantic Rule Engine**:
  - **Relationship-Driven**: Define business logic using a custom DSL that operates on ontological patterns and event-driven graph changes.
  - **Action Orchestration**: Trigger gRPC calls and asynchronous actions based on semantic triggers within the graph.
- **Semantic Data Synchronization**:
  - **Ontology Alignment**: Automatically map and sync external data products (ERP, CRM) to your central ontological model.
  - **Conflict Resolution**: Intelligent merging based on semantic identity (source_id).
- **Interactive Visualization**:
  - **Structural Insight**: High-performance rendering with **Cytoscape.js** to explore the graph realization of your ontology.
  - **Path Analysis**: Highlight multi-hop relationships and semantic paths.
- **RBAC Access Control**:
  - **Role-Based Permissions**: Fine-grained control over pages, actions, and entity types per role.
  - **User Approval Workflow**: Registration with admin approval and account activation.

### Tech Stack

- **Frontend**: Next.js 16 (App Router), TypeScript 5, React 19, TailwindCSS, Shadcn UI, Zustand, Cytoscape.js, next-intl (i18n)
- **Backend**: FastAPI, Python 3.11+, SQLAlchemy (async), PostgreSQL (asyncpg), LangChain/LangGraph
- **Graph Storage**: PostgreSQL with JSONB properties
- **Rule Engine**: Custom DSL (Lark parser), event-driven triggers, gRPC action execution
- **Infrastructure**: Docker Compose, Alembic (migrations)
- **Package Management**: **UV** (Backend), **PNPM** (Frontend)

### Project Structure

```text
ontology-nexus/
├── backend/                  # FastAPI Backend
│   ├── app/
│   │   ├── api/              # REST API routes
│   │   ├── core/             # Config, security, database
│   │   ├── models/           # SQLAlchemy ORM models
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── services/         # Business logic (agent, sync, graph, gRPC)
│   │   ├── repositories/     # Data access layer
│   │   ├── rule_engine/      # Custom DSL parser, registries, executor
│   │   ├── mcp/              # MCP server implementations
│   │   └── main.py           # App entry point
│   ├── alembic/              # Database migrations
│   ├── erp_emulator/         # gRPC ERP emulator for testing
│   └── Dockerfile
├── frontend/                 # Next.js Frontend
│   ├── src/
│   │   ├── app/[locale]/     # i18n pages (dashboard, graph, rules, admin)
│   │   ├── components/       # UI components (chat, graph viewers, panels)
│   │   ├── lib/              # API client, auth store
│   │   ├── i18n/             # Internationalization
│   │   └── messages/         # en/zh translations
│   └── Dockerfile
├── docker-compose.yml        # Container orchestration
└── .env.example              # Environment variable template
```

### Quick Start

#### Using Docker Compose (Recommended)

1.  **Environment Setup**:
    ```bash
    cp .env.example .env
    ```
    Edit `.env` and set required values: `SECRET_KEY`, `POSTGRES_PASSWORD`, and optionally LLM API keys.

2.  **Start Services**:
    ```bash
    docker-compose up --build
    ```

3.  **Access**:
    - Web UI: [http://localhost:3000](http://localhost:3000)
    - API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
    - Health Check: [http://localhost:8000/health](http://localhost:8000/health)

#### Local Development

**Backend** (Requires `uv`)
```bash
cd backend
uv sync
uv run alembic upgrade head    # Run database migrations
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend** (Requires `pnpm`)
```bash
cd frontend
pnpm install
pnpm dev
```

### Security

- JWT authentication with token expiration
- RBAC with role-based page, action, and entity permissions
- Password complexity enforcement (min 8 chars, letters + digits)
- SQL injection prevention with parameterized queries and input validation
- File upload size (50MB) and type validation
- Query parameter bounds to prevent resource exhaustion
- Non-root Docker containers with health checks
- CORS restricted to configured origins with explicit methods/headers

---

<a name="中文"></a>
## 中文版本

**KG-Agent** 是一个**本体驱动**（Ontology-Driven）的智能平台，专为复杂的语义推理和自动化设计。系统的核心由严谨的**本体论**（Ontology）定义，而**知识图谱**（Knowledge Graph）则是其动态的实现与数据组织形式。通过坚持"本体优先"原则，KG-Agent 确保每一次交互、规则执行和数据同步都受统一的语义框架约束。

### 核心功能

- **本体优先的模式管理**:
  - **核心定义**: 超越扁平化数据模型；通过类、属性和复杂关系定义您的业务世界。
  - **可视化编辑器**: 实时 Schema 操作，支持数据类型（rdfs:range）与语义别名。
  - **标准支持**: 无缝导入/导出 **OWL/TTL** 本体文件。
- **本体引导的智能 Agent**:
  - **语义推理**: 基于本体结构的自然语言交互，理解底层逻辑而非简单的关键词匹配。
  - **能力扩展**: 集成 **MCP (Model Context Protocol)** 服务，提供直接源自本体定义的查询与动作工具。
- **语义规则引擎**:
  - **关系驱动**: 使用自定义 DSL 定义业务逻辑，基于本体模式和图数据变更进行实时触发。
  - **动作编排**: 基于图谱中的语义触发器，自动执行 gRPC 调用和异步操作。
- **语义数据同步**:
  - **本体对齐**: 将外部数据产品（如 ERP, CRM）自动映射并同步至核心本体模型。
  - **语义冲突解决**: 基于语义标识（source_id）的智能数据合并。
- **交互式可视化分析**:
  - **结构洞察**: 使用 **Cytoscape.js** 高性能渲染，直观展示本体模型在图谱中的具体实现。
  - **路径分析**: 高亮显示多跳关系与语义路径。
- **RBAC 访问控制**:
  - **基于角色的权限**: 对页面、动作和实体类型进行细粒度的角色控制。
  - **用户审批流程**: 注册需管理员审批和账户激活。

### 技术栈

- **前端**: Next.js 16 (App Router), TypeScript 5, React 19, TailwindCSS, Shadcn UI, Zustand, Cytoscape.js, next-intl (国际化)
- **后端**: FastAPI, Python 3.11+, SQLAlchemy (异步), PostgreSQL (asyncpg), LangChain/LangGraph
- **图存储**: PostgreSQL + JSONB 属性
- **规则引擎**: 自定义 DSL（Lark 解析器），事件驱动触发，gRPC 动作执行
- **基础设施**: Docker Compose, Alembic (数据库迁移)
- **包管理**: **UV** (后端), **PNPM** (前端)

### 项目结构

```text
ontology-nexus/
├── backend/                  # FastAPI 后端
│   ├── app/
│   │   ├── api/              # REST API 路由
│   │   ├── core/             # 配置、安全、数据库
│   │   ├── models/           # SQLAlchemy ORM 模型
│   │   ├── schemas/          # Pydantic 数据模型
│   │   ├── services/         # 业务逻辑（Agent、同步、图、gRPC）
│   │   ├── repositories/     # 数据访问层
│   │   ├── rule_engine/      # 自定义 DSL 解析器、注册表、执行器
│   │   ├── mcp/              # MCP 服务实现
│   │   └── main.py           # 应用入口
│   ├── alembic/              # 数据库迁移
│   ├── erp_emulator/         # gRPC ERP 模拟器（测试用）
│   └── Dockerfile
├── frontend/                 # Next.js 前端
│   ├── src/
│   │   ├── app/[locale]/     # 国际化页面（仪表盘、图谱、规则、管理）
│   │   ├── components/       # UI 组件（聊天、图谱查看器、面板）
│   │   ├── lib/              # API 客户端、认证 Store
│   │   ├── i18n/             # 国际化配置
│   │   └── messages/         # 中英文翻译文件
│   └── Dockerfile
├── docker-compose.yml        # 容器编排
└── .env.example              # 环境变量模板
```

### 快速开始

#### 使用 Docker Compose（推荐）

1.  **环境配置**:
    ```bash
    cp .env.example .env
    ```
    编辑 `.env`，设置必要值：`SECRET_KEY`、`POSTGRES_PASSWORD`，以及可选的 LLM API 密钥。

2.  **启动服务**:
    ```bash
    docker-compose up --build
    ```

3.  **访问**:
    - 网页端: [http://localhost:3000](http://localhost:3000)
    - API 文档: [http://localhost:8000/docs](http://localhost:8000/docs)
    - 健康检查: [http://localhost:8000/health](http://localhost:8000/health)

#### 本地开发

**后端**（需安装 `uv`）
```bash
cd backend
uv sync
uv run alembic upgrade head    # 运行数据库迁移
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**前端**（需安装 `pnpm`）
```bash
cd frontend
pnpm install
pnpm dev
```

### 安全特性

- JWT 认证，支持 Token 过期
- RBAC 角色权限：页面、动作、实体类型细粒度控制
- 密码强度验证（至少 8 位，需包含字母和数字）
- SQL 注入防护：参数化查询 + 输入验证
- 文件上传限制：50MB 大小、格式白名单
- 查询参数边界限制，防止资源耗尽
- Docker 容器以非 root 用户运行，配置健康检查
- CORS 限制为配置的源，明确指定允许的方法和头部

---

## License / 许可证

**Non-Commercial License Only** / **仅限非商业用途**

This project is licensed under a restrictive Non-Commercial License.
- **Prohibited**: Commercial use, for-profit distribution, or commercial use of derivative works.
- **Allowed**: Personal, educational, and non-commercial research use.

For detailed terms, please see the [LICENSE](./LICENSE) file.

本项目采用限制性非商业许可协议。
- **禁止**: 商业用途、营利性分发或二次开发后的商业用途。
- **允许**: 个人学习、教育及非商业性研究使用。

详细条款请参阅 [LICENSE](./LICENSE) 文件。
