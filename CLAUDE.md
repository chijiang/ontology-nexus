# CLAUDE.md - Project Guidelines for Ontology-Nexus

## Project Overview

Ontology-Nexus (KG-Agent) is an Ontology-First intelligent platform for semantic reasoning and automation. It uses a Knowledge Graph backed by PostgreSQL, with a FastAPI backend, Next.js frontend, and custom DSL rule engine.

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy (async), PostgreSQL (asyncpg), LangChain/LangGraph, Lark (DSL parser), gRPC, FastMCP
- **Frontend**: Next.js 16 (App Router), TypeScript 5, React 19, TailwindCSS, Shadcn UI, Zustand, Cytoscape.js, next-intl (i18n)
- **Infrastructure**: Docker Compose, PostgreSQL 17, Alembic (migrations)
- **Package Managers**: UV (backend), PNPM (frontend)

## Project Structure

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
│   │   └── main.py         # App entry point with lifespan
│   ├── alembic/            # Database migrations
│   ├── erp_emulator/       # gRPC ERP emulator for testing
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

## Key Commands

### Backend
```bash
cd backend
uv sync                          # Install dependencies
uv run uvicorn app.main:app --reload  # Start dev server (port 8000)
uv run alembic upgrade head      # Run migrations
uv run pytest                    # Run tests
uv run ruff check .              # Lint
```

### Frontend
```bash
cd frontend
pnpm install                     # Install dependencies
pnpm dev                         # Start dev server (port 3000)
pnpm build                       # Production build
pnpm lint                        # Lint
```

### Docker
```bash
cp .env.example .env             # Configure environment
docker-compose up --build        # Start all services
```

## Architecture Notes

### Authentication & Authorization
- JWT-based auth (python-jose), tokens stored in Zustand with localStorage persist
- RBAC with roles, page permissions, action permissions, entity permissions
- `get_current_user` dependency checks `is_active` and `approval_status`
- `require_admin` dependency for destructive/admin endpoints
- Password validation: min 8 chars, requires letters + digits

### Database
- Async SQLAlchemy with asyncpg driver, `pool_pre_ping=True`
- All datetime columns use `datetime.now(timezone.utc)` (not `datetime.utcnow()`)
- Foreign key columns on `Conversation.user_id` and `Message.conversation_id` are indexed
- Graph data stored in `GraphEntity` and `GraphRelationship` tables with JSONB properties

### API Patterns
- All graph ontology endpoints use Pydantic request models (not raw `dict`)
- DSL parsing errors handled via shared `handle_dsl_exception()` in `deps.py`
- SSE streaming for chat with `AbortController` on frontend
- File upload validation: 50MB max, allowed extensions (.ttl, .owl, .rdf, .xml, .n3, .nt)
- Query parameter bounds enforced via `Query(ge=, le=)`

### Frontend Patterns
- `useRef` for isMounted checks (not `useState`)
- `tokenRef` pattern for stable closure access in event handlers
- Request counter pattern (`loadRequestIdRef`) for race condition prevention
- Immutable state updates (spread operator, not mutation)
- `graphApi` functions do NOT accept token params (axios interceptor handles auth)
- `ErrorBoundary` component wraps graph viewers; `error.tsx` for page-level errors

### Rule Engine
- Custom DSL parsed by Lark grammar
- Rules and Actions stored in DB and loaded into in-memory registries at startup
- Delete operations must call `registry.unregister()` to keep in-memory state in sync
- `safe_eval()` used for property transform expressions (no `eval()`)

### Scheduler Service

The global scheduler provides automatic task execution for data synchronization and rule evaluation.

**Architecture:**
- APScheduler AsyncIOScheduler with SQLAlchemy job store for persistence
- TaskExecutor handles actual execution with watchdog mechanisms
- Tasks and executions stored in database for audit trail

**Task Types:**
- `sync`: Data product synchronization (pull data from external gRPC services)
- `rule`: Scheduled rule evaluation (execute business rules on schedule)

**Watchdog Mechanism:**
- Concurrent task limiting: Semaphore with max_concurrent limit (default: 10)
- Timeout control: asyncio.wait_for with task-specific timeout (default: 300s)
- Smart retry: Network/temporary errors retry, validation errors don't
- Error patterns in `RETRYABLE_ERROR_PATTERNS` and `NON_RETRYABLE_ERROR_PATTERNS`

**API Endpoints:**
- `/api/scheduled-tasks/` - Manage scheduled tasks
- `/api/data-products/{id}/sync-schedule` - Data product sync schedules
- `/api/rules/{id}/schedule` - Rule evaluation schedules

**Configuration:**
- `SCHEDULER_MAX_CONCURRENT` - Max concurrent tasks (default: 10)
- `SCHEDULER_DEFAULT_TIMEOUT` - Default timeout in seconds (default: 300)

### Docker
- Backend and frontend run as non-root users (`appuser`)
- Health checks configured for all services
- Frontend uses Next.js `output: "standalone"` for minimal Docker images
- `.dockerignore` files exclude `.git`, `node_modules`, `__pycache__`, etc.

## Conventions

- Backend logging: use `logger = logging.getLogger(__name__)`, never bare `except:` or silent `pass`
- No hardcoded secrets; use environment variables with `${VAR:?required}` in docker-compose
- Chinese and English i18n supported via next-intl; backend error messages use English
- Always verify Python syntax after edits: `python -c "import ast; ast.parse(open('file', encoding='utf-8').read())"`

## Update Policy
- Update `CLAUDE.md` and `README.md` after completing each major task
