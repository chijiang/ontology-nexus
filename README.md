# Knowledge Graph Agent (KG-Agent)

[English](#english) | [中文](#中文)

---

<a name="english"></a>
## English Version

KG-Agent is an intelligent Q&A and visualization system based on Knowledge Graphs. it allows importing ontology files (OWL/TTL), connecting to Neo4j databases, and interacting directly with the knowledge graph through natural language.

### Core Features

- **Intelligent Q&A**: RAG (Retrieval-Augmented Generation) based on LLMs and Knowledge Graphs, allowing natural language queries.
- **Graph Visualization**: Dynamic display of knowledge graph structures, supporting node clicks to view properties and relationships.
- **Ontology Import**: Supports loading OWL/TTL ontology files to quickly build graph schemas.
- **Multi-Source Support**: Integrates Neo4j graph databases and various LLM configurations (OpenAI, etc.).
- **Dashboard**: Real-time display of graph statistics.

### Tech Stack

- **Frontend**: Next.js 15+, TypeScript, Cytoscape.js, TailwindCSS, Shadcn UI
- **Backend**: FastAPI, Python 3.11+, LangChain, Neo4j, SQLAlchemy (SQLite)
- **Package Management**: UV (Backend), PNPM (Frontend)

### Quick Start

#### Using Docker Compose (Recommended)

1. **Environment Setup**:
   Copy `.env.example` to `.env` and fill in necessary API keys and configurations.

2. **Start Services**:
   ```bash
   docker-compose up --build
   ```

3. **Access Application**:
   - Frontend: [http://localhost:3000](http://localhost:3000)
   - Backend API: [http://localhost:8000](http://localhost:8000)

#### Local Development

**Backend**
1. Enter `backend` directory.
2. Install dependencies and start:
   ```bash
   uv run main.py
   ```

**Frontend**
1. Enter `frontend` directory.
2. Install dependencies: `pnpm install`
3. Start dev server: `pnpm dev`

---

<a name="中文"></a>
## 中文版本

KG-Agent 是一个基于知识图谱（Knowledge Graph）的智能问答与可视化分析系统。它能够导入本体文件（OWL/TTL），连接 Neo4j 数据库，并通过自然语言与知识图谱进行直接交互。

### 核心功能

- **智能问答**：基于 LLM 和知识图谱的 RAG（检索增强生成），通过自然语言查询图谱数据。
- **图谱可视化**：动态展示知识图谱结构，支持节点点击查看属性与链接关系。
- **本体导入**：支持载入 OWL/TTL 等格式的本体文件，快速构建图谱模式。
- **多数据源支持**：集成 Neo4j 图数据库及多种 LLM 配置（OpenAI 等）。
- **数据仪表盘**：实时展示图谱统计信息。

### 技术栈

- **前端**: Next.js 15+, TypeScript, Cytoscape.js, TailwindCSS, Shadcn UI
- **后端**: FastAPI, Python 3.11+, LangChain, Neo4j, SQLAlchemy (SQLite)
- **包管理**: UV (Backend), PNPM (Frontend)

### 快速开始

#### 使用 Docker Compose (推荐)

1. **环境配置**：
   复制 `.env.example` 并重命名为 `.env`，填入必要的 API 密钥和配置。

2. **启动服务**：
   ```bash
   docker-compose up --build
   ```

3. **访问应用**：
   - 前端：[http://localhost:3000](http://localhost:3000)
   - 后端 API：[http://localhost:8000](http://localhost:8000)

#### 本地开发运行

**后端**
1. 进入 `backend` 目录。
2. 安装依赖并启动：
   ```bash
   uv run main.py
   ```

**前端**
1. 进入 `frontend` 目录。
2. 安装依赖：`pnpm install`
3. 启动开发服务器：
   ```bash
   pnpm dev
   ```

## 项目结构 / Project Structure

```
kg_agent/
├── backend/            # FastAPI 后端代码 / Backend code
│   ├── app/            # 核心业务逻辑 / Core logic
│   ├── main.py         # 启动入口 / Entry point
│   └── Dockerfile      # 后端 Docker 定义 / Backend Docker definition
├── frontend/           # Next.js 前端代码 / Frontend code
│   ├── src/            # 源代码 / Source code
│   └── Dockerfile      # 前端 Docker 定义 / Frontend Docker definition
└── docker-compose.yml  # 全栈容器编排 / Full-stack orchestration
```

## 许可证 / License

MIT License
