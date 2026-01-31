# 知识图谱问答应用设计文档

**日期**: 2025-02-01
**版本**: 1.0

---

## 1. 整体架构

### 系统架构概览

项目采用前后端分离的混合架构：

**前端 (frontend/)**
- Next.js 14+ (App Router) 作为主应用框架
- Tailwind CSS + shadcn/ui 提供 UI 组件
- Next.js API Routes 作为反向代理层，转发请求到 Python 后端
- React Flow 或 Cytoscape.js 实现图谱可视化

**后端 (backend/)**
- FastAPI 作为 Python Web 框架
- LangChain 构建 Agent 逻辑
- Neo4j Driver 使用连接池管理图数据库连接
- SQLite 存储用户配置（加密存储 LLM API Key 和 Neo4j 凭证）

**通信流程**
```
用户 → Next.js 前端 → Next.js API Routes (反向代理) → FastAPI → Neo4j/LLM
```

Python 服务运行在 localhost:8000，不对外暴露，所有外部请求通过 Next.js 转发。

---

## 2. 数据模型设计

### Neo4j 图数据库设计

采用**混合存储模式**，Schema 和 Instance 分层存储：

**元数据层 (__Schema 标签)**
- 存储类、对象属性、数据属性的定义
- 节点结构：
  - `(:Class:__Schema {uri, name, description, label})`
  - `(:ObjectProperty:__Schema {uri, name, domain, range, label})`
  - `(:DataProperty:__Schema {uri, name, domain, range, label})`
- 关系：`(:Class:__Schema)-[:HAS_PROPERTY]->(:Property:__Schema)`

**业务数据层**
- 使用实例的原始标签（如 `:PurchaseOrder`, `:Supplier`）
- 节点包含 `__uri` 属性关联到 Schema 类
- 属性节点包含 `__type` 属性关联到 Schema 属性

### SQLite 配置数据库

```sql
-- 用户表（支持密码认证，预留多租户扩展）
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    email TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- LLM 配置表（加密存储）
CREATE TABLE llm_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    api_key_encrypted TEXT NOT NULL,
    base_url TEXT NOT NULL,
    model TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id)
);

-- Neo4j 配置表（加密存储）
CREATE TABLE neo4j_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    uri_encrypted TEXT NOT NULL,
    username_encrypted TEXT NOT NULL,
    password_encrypted TEXT NOT NULL,
    database TEXT DEFAULT 'neo4j',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id)
);

-- 图谱导入记录
CREATE TABLE graph_imports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    filename TEXT NOT NULL,
    import_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    nodes_count INTEGER,
    edges_count INTEGER,
    schema_version TEXT
);

-- 用户会话表
CREATE TABLE user_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    token_hash TEXT NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 3. Agent 架构与查询工具

### Agent 流程
```
用户问题 → Schema 匹配层（LLM + NLP 增强）→ 意图识别 + 参数提取
→ 工具调用 → 结果整合 → LLM 生成回答
```

### 标准查询工具集

1. **fuzzy_search_entities** - 实体模糊搜索
2. **fuzzy_search_relationships** - 关系模糊搜索
3. **query_n_hop_neighbors** - N-hop 邻居查询
4. **find_path_between_nodes** - 节点间路径查询
5. **query_nodes_by_filters** - 属性过滤查询
6. **get_node_statistics** - 统计聚合
7. **get_relationship_types** - 关系类型查询

### Schema 匹配层
- 传统 NLP 预处理（分词、同义词扩展、拼写纠错）
- LLM 语义匹配
- 结果融合

---

## 4. 前端设计

### 页面结构
```
/                    → 登录页面
/dashboard           → 主控制台（聊天 + 图谱）
/config              → 配置管理
/graph/import        → OWL 文件导入
/graph/schema        → Schema 浏览器
/graph/visualize     → 图谱可视化（独立页面）
```

### 图谱可视化
- 使用 Cytoscape.js
- 功能：缩放、平移、拖拽、双击展开邻居、问答高亮

---

## 5. OWL 导入与图谱构建

### 导入流程
```
OWL/TTL → RDF 解析 → Schema/Instance 分类 → Neo4j 导入 → 建索引
```

### 模糊匹配索引
- Schema 层全文索引
- Instance 层全文索引
- 全文搜索索引

---

## 6. API 设计

### FastAPI 后端接口

**认证**: `/api/auth/register`, `/api/auth/login`, `/api/auth/refresh`

**配置**: `/api/config/llm`, `/api/config/neo4j`, `/api/config/test/*`

**图谱**: `/api/graph/import`, `/api/graph/schema`, `/api/graph/statistics`

**问答**: `/api/chat/completions`, `/api/chat/stream`, `/api/chat/history`

**可视化**: `/api/graph/query`, `/api/graph/node/{uri}`, `/api/graph/neighbors`, `/api/graph/path`

### SSE 流式响应
- thinking: Schema 匹配过程
- content: LLM 回答（流式）
- graph_data: 相关图数据
- done: 完成

---

## 7. 测试策略与验收标准

### 单元测试
- 图查询工具测试
- Schema 匹配器测试
- 加密/解密测试

### 集成测试
- 完整问答流程测试

### 端到端测试
- Playwright E2E 测试

### 验收标准
- 每个阶段有明确的验收标准
- 最终用 sample.ttl 进行端到端测试
- LLM 回答必须基于图谱数据

---

## 技术栈总结

| 层级 | 技术 |
|------|------|
| 前端框架 | Next.js 14+ (App Router) |
| UI 组件 | Tailwind CSS + shadcn/ui |
| 图谱可视化 | Cytoscape.js |
| 后端框架 | FastAPI |
| AI 框架 | LangChain |
| 图数据库 | Neo4j |
| 关系数据库 | SQLite |
| 包管理 | pnpm (frontend), uv (backend) |
| 认证 | JWT + bcrypt |
| 测试 | pytest, Playwright |
