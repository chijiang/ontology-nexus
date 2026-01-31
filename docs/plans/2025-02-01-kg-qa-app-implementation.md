# 知识图谱问答应用实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 构建一个基于知识图谱的问答应用，支持 OWL 导入、图谱可视化、LLM 问答。

**Architecture:** Next.js 前端 + FastAPI 后端，Next.js 反向代理，LangChain Agent，Neo4j 图数据库，SQLite 配置存储。

**Tech Stack:**
- Frontend: Next.js 14, Tailwind CSS, shadcn/ui, Cytoscape.js, pnpm
- Backend: FastAPI, LangChain, Neo4j Driver, uv
- Data: Neo4j, SQLite
- Auth: JWT + bcrypt
- Test: pytest, Playwright

---

## 第一阶段：项目初始化

### Task 1.1: 创建项目目录结构

**Files:**
- Create: `frontend/`, `backend/`, `docs/`, `tests/`
- Create: `frontend/public/`, `frontend/src/`
- Create: `backend/app/`, `backend/tests/`

**Step 1: 创建目录结构**

```bash
mkdir -p frontend/public frontend/src/app frontend/src/components frontend/src/lib
mkdir -p backend/app/api backend/app/core backend/app/models backend/app/services
mkdir -p backend/tests/unit backend/tests/integration
mkdir -p tests/e2e
```

**Step 2: 验证目录创建**

```bash
ls -la frontend/
ls -la backend/
```

Expected: 输出显示所有目录已创建

**Step 3: 创建 .gitignore**

```bash
cat > .gitignore << 'EOF'
# Dependencies
frontend/node_modules/
backend/.venv/
backend/.uv_cache/

# Environment
.env
.env.local
credentials

# IDE
.vscode/
.idea/
*.swp

# Next.js
frontend/.next/
frontend/out/

# Python
__pycache__/
*.py[cod]
*.so
.pytest_cache/

# Database
*.db
*.db-journal

# Logs
*.log
frontend/logs/
backend/logs/
EOF
```

**Step 4: Commit**

```bash
git add .
git commit -m "feat: initialize project structure"
```

---

### Task 1.2: 初始化 Python 后端 (uv)

**Files:**
- Create: `backend/pyproject.toml`

**Step 1: 创建 pyproject.toml**

```bash
cd backend
uv init --no-readme
```

**Step 2: 更新 pyproject.toml 依赖**

```toml
[project]
name = "kg-qa-backend"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "langchain>=0.3.0",
    "langchain-openai>=0.2.0",
    "langgraph>=0.2.0",
    "neo4j>=5.26.0",
    "rdflib>=7.0.0",
    "pydantic>=2.10.0",
    "pydantic-settings>=2.6.0",
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4",
    "python-multipart>=0.0.12",
    "cryptography>=44.0.0",
    "sqlalchemy>=2.0.36",
    "aiosqlite>=0.20.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=6.0.0",
    "httpx>=0.28.0",
    "ruff>=0.8.0",
]

[tool.uv]
dev-dependencies = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=6.0.0",
    "httpx>=0.28.0",
    "ruff>=0.8.0",
]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

**Step 3: 安装依赖**

```bash
cd backend
uv sync
```

Expected: 无错误，依赖安装成功

**Step 4: 验证安装**

```bash
uv run python -c "import fastapi; import neo4j; import langchain; print('OK')"
```

Expected: 输出 "OK"

**Step 5: Commit**

```bash
git add backend/
git commit -m "feat: initialize Python backend with uv"
```

---

### Task 1.3: 初始化 Next.js 前端 (pnpm)

**Files:**
- Create: `frontend/package.json`, `frontend/next.config.js`, `frontend/tsconfig.json`

**Step 1: 创建 Next.js 项目**

```bash
cd frontend
pnpm create next-app@latest . --typescript --tailwind --eslint --app --src-dir --import-alias "@/*" --no-git
```

**Step 2: 安装 shadcn/ui**

```bash
cd frontend
pnpm dlx shadcn@latest init -y -d
```

**Step 3: 安装额外依赖**

```bash
cd frontend
pnpm add cytoscape cytoscape-react-hooks zustand axios
pnpm add -D @playwright/test
```

**Step 4: 添加 shadcn 组件**

```bash
cd frontend
pnpm dlx shadcn@latest add button input card dialog tabs form toast
```

**Step 5: 验证安装**

```bash
cd frontend
pnpm build
```

Expected: 构建成功，无错误

**Step 6: Commit**

```bash
git add frontend/
git commit -m "feat: initialize Next.js frontend with shadcn/ui"
```

---

### Task 1.4: 配置开发环境

**Files:**
- Create: `frontend/.env.local`, `backend/.env`

**Step 1: 创建后端 .env**

```bash
cat > backend/.env << 'EOF'
# Server
HOST=0.0.0.0
PORT=8000
CORS_origins=["http://localhost:3000"]

# Security
SECRET_KEY=change-this-to-a-random-secret-key-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Database
DATABASE_URL=sqlite:///./kg_qa.db
EOF
```

**Step 2: 创建前端 .env.local**

```bash
cat > frontend/.env.local << 'EOF'
NEXT_PUBLIC_API_URL=http://localhost:3000/api
BACKEND_URL=http://localhost:8000
EOF
```

**Step 3: 创建环境变量示例文件**

```bash
cat > .env.example << 'EOF'
# Backend
HOST=0.0.0.0
PORT=8000
SECRET_KEY=your-secret-key-here

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:3000/api
BACKEND_URL=http://localhost:8000
EOF
```

**Step 4: Commit**

```bash
git add .env.example
git commit -m "feat: add environment configuration"
```

---

## 第二阶段：后端核心功能

### Task 2.1: 创建核心配置和工具模块

**Files:**
- Create: `backend/app/core/config.py`
- Create: `backend/app/core/security.py`
- Create: `backend/app/core/database.py`
- Create: `backend/app/core/neo4j_pool.py`

**Step 1: 写测试 - config.py**

```bash
cat > backend/tests/test_config.py << 'EOF'
from app.core.config import settings

def test_settings_loaded():
    assert settings.HOST == "0.0.0.0"
    assert settings.PORT == 8000
    assert settings.SECRET_KEY

def test_database_url():
    assert "sqlite" in settings.DATABASE_URL
EOF
```

**Step 2: 运行测试（预期失败）**

```bash
cd backend && uv run pytest tests/test_config.py -v
```

Expected: FAIL - ModuleNotFoundError

**Step 3: 实现 config.py**

```python
# backend/app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_origins: list[str] = ["http://localhost:3000"]

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Database
    DATABASE_URL: str = "sqlite:///./kg_qa.db"

    # Neo4j (default, will be overridden by user config)
    NEO4J_URI: str = ""
    NEO4J_USERNAME: str = ""
    NEO4J_PASSWORD: str = ""
    NEO4J_DATABASE: str = "neo4j"


settings = Settings()
```

**Step 4: 运行测试（预期通过）**

```bash
cd backend && uv run pytest tests/test_config.py -v
```

Expected: PASS

**Step 5: 写测试 - security.py**

```bash
cat > backend/tests/test_security.py << 'EOF'
from app.core.security import hash_password, verify_password

def test_hash_password():
    password = "test123"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed)

def test_verify_wrong_password():
    password = "test123"
    hashed = hash_password(password)
    assert not verify_password("wrong", hashed)
EOF
```

**Step 6: 运行测试（预期失败）**

```bash
cd backend && uv run pytest tests/test_security.py -v
```

Expected: FAIL

**Step 7: 实现 security.py**

```python
# backend/app/core/security.py
from passlib.context import CryptContext
from cryptography.fernet import Fernet
import base64
import os

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_encryption_key() -> bytes:
    """从 SECRET_KEY 派生加密密钥"""
    from app.core.config import settings
    # 使用 SECRET_KEY 的 SHA256 生成固定长度的密钥
    import hashlib
    key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return base64.urlsafe_b64encode(key)


def encrypt_data(data: str) -> str:
    f = Fernet(get_encryption_key())
    return f.encrypt(data.encode()).decode()


def decrypt_data(encrypted_data: str) -> str:
    f = Fernet(get_encryption_key())
    return f.decrypt(encrypted_data.encode()).decode()
```

**Step 8: 运行测试（预期通过）**

```bash
cd backend && uv run pytest tests/test_security.py -v
```

Expected: PASS

**Step 9: 实现 database.py**

```python
# backend/app/core/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://"),
    connect_args={"check_same_thread": False}
)

async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session
```

**Step 10: 实现 neo4j_pool.py**

```python
# backend/app/core/neo4j_pool.py
from neo4j import AsyncDriver, AsyncGraphDatabase
from typing import Optional
from app.core.config import settings

_pool: Optional[AsyncDriver] = None


async def get_neo4j_driver(
    uri: str = None,
    username: str = None,
    password: str = None,
    database: str = None
) -> AsyncDriver:
    """获取 Neo4j Driver（使用连接池）"""
    global _pool

    if _pool is None:
        uri = uri or settings.NEO4J_URI
        username = username or settings.NEO4J_USERNAME
        password = password or settings.NEO4J_PASSWORD
        database = database or settings.NEO4J_DATABASE

        _pool = AsyncGraphDatabase.driver(
            uri,
            auth=(username, password)
        )

    return _pool


async def close_neo4j():
    """关闭 Neo4j 连接池"""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
```

**Step 11: Commit**

```bash
git add backend/
git commit -m "feat: add core config, security, database modules"
```

---

### Task 2.2: 创建数据库模型

**Files:**
- Create: `backend/app/models/user.py`
- Create: `backend/app/models/llm_config.py`
- Create: `backend/app/models/neo4j_config.py`

**Step 1: 写测试 - user model**

```bash
cat > backend/tests/test_models.py << 'EOF'
import pytest
from app.models.user import User

def test_user_model():
    user = User(
        username="testuser",
        password_hash="hashed123",
        email="test@example.com"
    )
    assert user.username == "testuser"
    assert user.email == "test@example.com"
    assert user.is_active is True
EOF
```

**Step 2: 运行测试（预期失败）**

```bash
cd backend && uv run pytest tests/test_models.py -v
```

Expected: FAIL

**Step 3: 实现 models**

```python
# backend/app/models/user.py
from datetime import datetime
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
```

```python
# backend/app/models/llm_config.py
from datetime import datetime
from sqlalchemy import String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class LLMConfig(Base):
    __tablename__ = "llm_configs"
    __table_args__ = (UniqueConstraint("user_id", name="uq_llm_config_user"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    api_key_encrypted: Mapped[str] = mapped_column(String(500), nullable=False)
    base_url: Mapped[str] = mapped_column(String(500), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
```

```python
# backend/app/models/neo4j_config.py
from datetime import datetime
from sqlalchemy import String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class Neo4jConfig(Base):
    __tablename__ = "neo4j_configs"
    __table_args__ = (UniqueConstraint("user_id", name="uq_neo4j_config_user"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    uri_encrypted: Mapped[str] = mapped_column(String(500), nullable=False)
    username_encrypted: Mapped[str] = mapped_column(String(255), nullable=False)
    password_encrypted: Mapped[str] = mapped_column(String(255), nullable=False)
    database: Mapped[str] = mapped_column(String(100), default="neo4j")
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
```

**Step 4: 运行测试（预期通过）**

```bash
cd backend && uv run pytest tests/test_models.py -v
```

Expected: PASS

**Step 5: 创建数据库初始化脚本**

```python
# backend/app/core/init_db.py
import asyncio
from sqlalchemy import select
from app.core.database import async_session, engine
from app.core.security import hash_password
from app.models.user import User


async def init_db():
    """初始化数据库，创建表和默认用户"""
    from app.models.user import User
    from app.models.llm_config import LLMConfig
    from app.models.neo4j_config import Neo4jConfig

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        # 检查是否已有用户
        result = await session.execute(select(User).where(User.username == "admin"))
        if not result.scalar_one_or_none():
            admin = User(
                username="admin",
                password_hash=hash_password("admin123"),
                email="admin@example.com"
            )
            session.add(admin)
            await session.commit()
            print("Created default user: admin / admin123")
        else:
            print("Default admin user already exists")


if __name__ == "__main__":
    from app.core.database import Base
    asyncio.run(init_db())
```

**Step 6: Commit**

```bash
git add backend/
git commit -m "feat: add database models"
```

---

### Task 2.3: 认证 API

**Files:**
- Create: `backend/app/api/deps.py`
- Create: `backend/app/api/auth.py`

**Step 1: 写测试 - JWT**

```bash
cat > backend/tests/test_auth.py << 'EOF'
import pytest
from app.core.security import create_access_token, verify_access_token

def test_create_token():
    token = create_access_token(data={"sub": "testuser"})
    assert token
    assert isinstance(token, str)

def test_verify_token():
    token = create_access_token(data={"sub": "testuser"})
    payload = verify_access_token(token)
    assert payload["sub"] == "testuser"

def test_verify_invalid_token():
    with pytest.raises(Exception):
        verify_access_token("invalid.token.here")
EOF
```

**Step 2: 运行测试（预期失败）**

```bash
cd backend && uv run pytest tests/test_auth.py -v
```

Expected: FAIL

**Step 3: 实现 JWT 功能**

```python
# backend/app/core/security.py (添加)
from datetime import datetime, timedelta
from jose import JWTError, jwt
from app.core.config import settings

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError as e:
        raise ValueError("Invalid token") from e
```

**Step 4: 实现 deps.py**

```python
# backend/app/api/deps.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import verify_access_token
from app.models.user import User

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    token = credentials.credentials
    payload = verify_access_token(token)
    username = payload.get("sub")

    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user
```

**Step 5: 实现 auth.py**

```python
# backend/app/api/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    username: str
    password: str
    email: str | None = None


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # 检查用户是否存在
    result = await db.execute(select(User).where(User.username == req.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already exists")

    # 创建用户
    user = User(
        username=req.username,
        password_hash=hash_password(req.password),
        email=req.email
    )
    db.add(user)
    await db.commit()

    token = create_access_token(data={"sub": user.username})
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == req.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(data={"sub": user.username})
    return TokenResponse(access_token=token)
```

**Step 6: 运行测试（预期通过）**

```bash
cd backend && uv run pytest tests/test_auth.py -v
```

Expected: PASS

**Step 7: Commit**

```bash
git add backend/
git commit -m "feat: add authentication API"
```

---

### Task 2.4: 配置管理 API

**Files:**
- Create: `backend/app/api/config.py`
- Create: `backend/app/schemas/config.py`

**Step 1: 实现 schemas**

```python
# backend/app/schemas/config.py
from pydantic import BaseModel


class LLMConfigRequest(BaseModel):
    api_key: str
    base_url: str
    model: str


class LLMConfigResponse(BaseModel):
    base_url: str
    model: str
    # 不返回完整的 api_key，只返回是否已配置
    has_api_key: bool


class Neo4jConfigRequest(BaseModel):
    uri: str
    username: str
    password: str
    database: str = "neo4j"


class Neo4jConfigResponse(BaseModel):
    uri: str
    username: str
    database: str
    # 不返回完整的 password
    has_password: bool


class TestConnectionResponse(BaseModel):
    success: bool
    message: str
```

**Step 2: 实现 config.py**

```python
# backend/app/api/config.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import encrypt_data, decrypt_data
from app.core.neo4j_pool import get_neo4j_driver
from app.api.deps import get_current_user
from app.models.user import User
from app.models.llm_config import LLMConfig
from app.models.neo4j_config import Neo4jConfig
from app.schemas.config import (
    LLMConfigRequest, LLMConfigResponse,
    Neo4jConfigRequest, Neo4jConfigResponse,
    TestConnectionResponse
)
from langchain_openai import ChatOpenAI

router = APIRouter(prefix="/config", tags=["config"])


@router.get("/llm", response_model=LLMConfigResponse)
async def get_llm_config(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(LLMConfig).where(LLMConfig.user_id == current_user.id))
    config = result.scalar_one_or_none()

    if not config:
        return LLMConfigResponse(base_url="", model="", has_api_key=False)

    return LLMConfigResponse(
        base_url=config.base_url,
        model=config.model,
        has_api_key=bool(config.api_key_encrypted)
    )


@router.put("/llm")
async def update_llm_config(
    req: LLMConfigRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(LLMConfig).where(LLMConfig.user_id == current_user.id))
    config = result.scalar_one_or_none()

    encrypted_key = encrypt_data(req.api_key)

    if config:
        config.api_key_encrypted = encrypted_key
        config.base_url = req.base_url
        config.model = req.model
    else:
        config = LLMConfig(
            user_id=current_user.id,
            api_key_encrypted=encrypted_key,
            base_url=req.base_url,
            model=req.model
        )
        db.add(config)

    await db.commit()
    return {"message": "LLM config updated"}


@router.post("/test/llm", response_model=TestConnectionResponse)
async def test_llm_connection(
    req: LLMConfigRequest,
    current_user: User = Depends(get_current_user)
):
    try:
        llm = ChatOpenAI(
            api_key=req.api_key,
            base_url=req.base_url,
            model=req.model,
            max_tokens=10
        )
        await llm.ainvoke("test")
        return TestConnectionResponse(success=True, message="LLM connection successful")
    except Exception as e:
        return TestConnectionResponse(success=False, message=str(e))


@router.get("/neo4j", response_model=Neo4jConfigResponse)
async def get_neo4j_config(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Neo4jConfig).where(Neo4jConfig.user_id == current_user.id))
    config = result.scalar_one_or_none()

    if not config:
        return Neo4jConfigResponse(uri="", username="", database="neo4j", has_password=False)

    return Neo4jConfigResponse(
        uri=decrypt_data(config.uri_encrypted),
        username=decrypt_data(config.username_encrypted),
        database=config.database,
        has_password=bool(config.password_encrypted)
    )


@router.put("/neo4j")
async def update_neo4j_config(
    req: Neo4jConfigRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Neo4jConfig).where(Neo4jConfig.user_id == current_user.id))
    config = result.scalar_one_or_none()

    if config:
        config.uri_encrypted = encrypt_data(req.uri)
        config.username_encrypted = encrypt_data(req.username)
        config.password_encrypted = encrypt_data(req.password)
        config.database = req.database
    else:
        config = Neo4jConfig(
            user_id=current_user.id,
            uri_encrypted=encrypt_data(req.uri),
            username_encrypted=encrypt_data(req.username),
            password_encrypted=encrypt_data(req.password),
            database=req.database
        )
        db.add(config)

    await db.commit()
    return {"message": "Neo4j config updated"}


@router.post("/test/neo4j", response_model=TestConnectionResponse)
async def test_neo4j_connection(
    req: Neo4jConfigRequest,
    current_user: User = Depends(get_current_user)
):
    try:
        driver = await get_neo4j_driver(
            uri=req.uri,
            username=req.username,
            password=req.password,
            database=req.database
        )
        async with driver.session(database=req.database) as session:
            result = await session.run("RETURN 1 AS n")
            await result.data()
        return TestConnectionResponse(success=True, message="Neo4j connection successful")
    except Exception as e:
        return TestConnectionResponse(success=False, message=str(e))
```

**Step 3: Commit**

```bash
git add backend/
git commit -m "feat: add config management API"
```

---

### Task 2.5: OWL 解析与导入

**Files:**
- Create: `backend/app/services/owl_parser.py`
- Create: `backend/app/services/graph_importer.py`

**Step 1: 写测试 - OWL parser**

```bash
cat > backend/tests/test_owl_parser.py << 'EOF'
import pytest
from app.services.owl_parser import OWLParser
from rdflib import Graph, Namespace, RDF, RDFS, OWL

def test_classify_schema_triples():
    # 创建测试图
    g = Graph()
    ex = Namespace("http://example.com/")
    g.add((ex.ClassA, RDF.type, OWL.Class))
    g.add((ex.ClassA, RDFS.label, None))

    parser = OWLParser(g)
    schema, instances = parser.classify_triples()

    assert len(schema) > 0
    assert ex.ClassA in [s for s, _, _ in schema]
EOF
```

**Step 2: 运行测试（预期失败）**

```bash
cd backend && uv run pytest tests/test_owl_parser.py -v
```

Expected: FAIL

**Step 3: 实现 OWL parser**

```python
# backend/app/services/owl_parser.py
from rdflib import Graph, Namespace, RDF, RDFS, OWL
from typing import List, Tuple
from dataclasses import dataclass


@dataclass
class Triple:
    subject: str
    predicate: str
    obj: str


class OWLParser:
    """OWL/TTL 文件解析器"""

    SCHEMA_PREDICATES = {
        RDF.type, RDFS.subClassOf, RDFS.domain, RDFS.range,
        RDFS.subPropertyOf, OWL.equivalentClass, OWL.disjointWith,
        OWL.equivalentProperty, OWL.inverseOf
    }

    SCHEMA_TYPES = {
        OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty,
        OWL.AnnotationProperty
    }

    def __init__(self, graph: Graph | None = None):
        self.graph = graph or Graph()
        self._schema_entities = set()

    def load_from_file(self, file_path: str) -> None:
        self.graph.parse(file_path, format="turtle")

    def load_from_string(self, data: str) -> None:
        self.graph.parse(data=data, format="turtle")

    def classify_triples(self) -> tuple[List[Triple], List[Triple]]:
        """将三元组分类为 Schema 和 Instance"""
        schema_triples = []
        instance_triples = []

        # 先扫描所有 Schema 实体
        for s, p, o in self.graph:
            if self._is_schema_triple(s, p, o):
                self._schema_entities.add(s)
                if isinstance(o, (str, type(None))):
                    self._schema_entities.add(o)

        # 分类三元组
        for s, p, o in self.graph:
            s_str = str(s)
            p_str = str(p)
            o_str = str(o) if not isinstance(o, type(None)) else None

            if self._is_schema_triple(s, p, o):
                schema_triples.append(Triple(s_str, p_str, o_str))
            else:
                instance_triples.append(Triple(s_str, p_str, o_str))

        return schema_triples, instance_triples

    def _is_schema_triple(self, s, p, o) -> bool:
        """判断是否为 Schema 三元组"""
        # 检查谓词
        if p in self.SCHEMA_PREDICATES:
            return True

        # 检查类型声明
        if p == RDF.type and o in self.SCHEMA_TYPES:
            return True

        # 检查主体是否是 Schema 实体
        if s in self._schema_entities:
            return True

        return False

    def extract_classes(self) -> List[dict]:
        """提取所有类定义"""
        classes = []
        for s, _, o in self.graph.triples((None, RDF.type, OWL.Class)):
            classes.append({
                "uri": str(s),
                "name": s.split("#")[-1].split("/")[-1],
                "label": self._get_label(s)
            })
        return classes

    def extract_properties(self) -> List[dict]:
        """提取所有属性定义"""
        properties = []

        for s, _, o in self.graph.triples((None, RDF.type, OWL.ObjectProperty)):
            properties.append({
                "uri": str(s),
                "name": s.split("#")[-1].split("/")[-1],
                "label": self._get_label(s),
                "type": "object",
                "domain": self._get_domain(s),
                "range": self._get_range(s)
            })

        for s, _, o in self.graph.triples((None, RDF.type, OWL.DatatypeProperty)):
            properties.append({
                "uri": str(s),
                "name": s.split("#")[-1].split("/")[-1],
                "label": self._get_label(s),
                "type": "data",
                "domain": self._get_domain(s),
                "range": self._get_range(s)
            })

        return properties

    def _get_label(self, uri) -> str | None:
        for _, label in self.graph.triples((uri, RDFS.label, None)):
            return str(label)
        return None

    def _get_domain(self, uri) -> str | None:
        for _, domain in self.graph.triples((uri, RDFS.domain, None)):
            return str(domain)
        return None

    def _get_range(self, uri) -> str | None:
        for _, range_val in self.graph.triples((uri, RDFS.range, None)):
            return str(range_val)
        return None
```

**Step 4: 实现 graph importer**

```python
# backend/app/services/graph_importer.py
from typing import List
from neo4j import AsyncSession
from app.services.owl_parser import OWLParser, Triple


class GraphImporter:
    """将 OWL 解析结果导入 Neo4j"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def import_schema(self, parser: OWLParser) -> dict:
        """导入 Schema 层"""
        classes = parser.extract_classes()
        properties = parser.extract_properties()

        stats = {"classes": 0, "properties": 0}

        # 导入类
        for cls in classes:
            await self.session.run(
                """
                MERGE (c:Class:__Schema {uri: $uri})
                SET c.name = $name, c.label = $label
                """,
                uri=cls["uri"],
                name=cls["name"],
                label=cls.get("label")
            )
            stats["classes"] += 1

        # 导入属性
        for prop in properties:
            label_prefix = "Object" if prop["type"] == "object" else "Data"
            await self.session.run(
                f"""
                MERGE (p:{label_prefix}Property:__Schema {{uri: $uri}})
                SET p.name = $name, p.label = $label, p.domain = $domain, p.range = $range
                """,
                uri=prop["uri"],
                name=prop["name"],
                label=prop.get("label"),
                domain=prop.get("domain"),
                range=prop.get("range")
            )

            # 建立类与属性的关系
            if prop.get("domain"):
                await self.session.run(
                    """
                    MATCH (c:Class:__Schema {uri: $domain})
                    MATCH (p:Property:__Schema {uri: $uri})
                    MERGE (c)-[:HAS_PROPERTY]->(p)
                    """,
                    domain=prop["domain"],
                    uri=prop["uri"]
                )
            stats["properties"] += 1

        await self._create_schema_indexes()
        return stats

    async def import_instances(self, schema_triples: List[Triple], instance_triples: List[Triple]) -> dict:
        """导入 Instance 层"""
        stats = {"nodes": 0, "relationships": 0}

        # 首先收集所有类型声明
        type_map = {}  # {instance_uri: class_uri}
        for triple in instance_triples:
            if triple.predicate.endswith("type"):
                type_map[triple.subject] = triple.obj

        # 创建实例节点
        for subject_uri, class_uri in type_map.items():
            class_name = class_uri.split("#")[-1].split("/")[-1]
            node_name = subject_uri.split("#")[-1].split("/")[-1]

            await self.session.run(
                f"""
                MERGE (n:{class_name} {{uri: $uri}})
                SET n.name = $name, n.__type = $class_uri, n.__is_instance = true
                """,
                uri=subject_uri,
                name=node_name,
                class_uri=class_uri
            )
            stats["nodes"] += 1

        # 创建关系
        for triple in instance_triples:
            if triple.predicate.endswith("type"):
                continue  # 跳过类型声明

            # 获取关系名称
            rel_name = triple.predicate.split("#")[-1].split("/")[-1]

            await self.session.run(
                """
                MATCH (s {uri: $subject})
                MATCH (o {uri: $object})
                MERGE (s)-[r:%s]->(o)
                """ % rel_name,
                subject=triple.subject,
                object=triple.obj
            )
            stats["relationships"] += 1

        return stats

    async def _create_schema_indexes(self):
        """创建 Schema 层索引"""
        indexes = [
            "CREATE INDEX schema_class_uri IF NOT EXISTS FOR (c:Class:__Schema) ON (c.uri)",
            "CREATE INDEX schema_class_name IF NOT EXISTS FOR (c:Class:__Schema) ON (c.name)",
            "CREATE INDEX schema_prop_uri IF NOT EXISTS FOR (p:Property:__Schema) ON (p.uri)",
            "CREATE INDEX schema_prop_name IF NOT EXISTS FOR (p:Property:__Schema) ON (p.name)",
        ]

        for idx in indexes:
            await self.session.run(idx)
```

**Step 5: 运行测试（预期通过）**

```bash
cd backend && uv run pytest tests/test_owl_parser.py -v
```

Expected: PASS

**Step 6: Commit**

```bash
git add backend/
git commit -m "feat: add OWL parser and graph importer"
```

---

### Task 2.6: 图查询工具集

**Files:**
- Create: `backend/app/services/graph_tools.py`
- Create: `backend/tests/test_graph_tools.py`

**Step 1: 写测试 - fuzzy search**

```bash
cat > backend/tests/test_graph_tools.py << 'EOF'
import pytest
from app.services.graph_tools import GraphTools

@pytest.mark.asyncio
async def test_fuzzy_search_entities(neo4j_session):
    tools = GraphTools(neo4j_session)
    # 假设已有测试数据
    result = await tools.fuzzy_search_entities("Purchase", limit=5)
    assert isinstance(result, list)
    # 根据实际数据验证
EOF
```

**Step 2: 实现 graph_tools.py**

```python
# backend/app/services/graph_tools.py
from typing import List, Any
from neo4j import AsyncSession
from langchain_core.tools import tool


class GraphTools:
    """Neo4j 图查询工具集"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def fuzzy_search_entities(
        self,
        search_term: str,
        node_label: str | None = None,
        limit: int = 10
    ) -> List[dict]:
        """根据实体名称模糊搜索节点"""
        if node_label:
            query = f"""
                MATCH (n:{node_label})
                WHERE n.name CONTAINS $term OR n.label CONTAINS $term
                RETURN n.uri AS uri, n.name AS name, labels(n) AS labels
                LIMIT $limit
            """
        else:
            query = """
                MATCH (n)
                WHERE n.name CONTAINS $term OR n.label CONTAINS $term
                RETURN n.uri AS uri, n.name AS name, labels(n) AS labels
                LIMIT $limit
            """

        result = await self.session.run(query, term=search_term, limit=limit)
        return [record.data() for record in await result.data()]

    async def fuzzy_search_relationships(
        self,
        search_term: str,
        limit: int = 10
    ) -> List[dict]:
        """根据关系名称模糊搜索关系类型"""
        query = """
            MATCH ()-[r]->()
            WHERE type(r) CONTAINS $term
            RETURN DISTINCT type(r) AS relationship_type, count(r) AS count
            ORDER BY count DESC
            LIMIT $limit
        """

        result = await self.session.run(query, term=search_term, limit=limit)
        return [record.data() for record in await result.data()]

    async def query_n_hop_neighbors(
        self,
        node_uri: str,
        hops: int = 1,
        direction: str = "both",
        relationship_types: List[str] | None = None
    ) -> List[dict]:
        """查询节点的 N 跳邻居"""
        rel_pattern = ""
        if relationship_types:
            rels = "|".join(relationship_types)
            if direction == "outgoing":
                rel_pattern = f"[r:{rels}]"
            elif direction == "incoming":
                rel_pattern = f"[r:{rels}]"
            else:
                rel_pattern = f"[r:{rels}]"
        else:
            if direction == "outgoing":
                rel_pattern = "[r]->"
            elif direction == "incoming":
                rel_pattern = "[r<-]"
            else:
                rel_pattern = "[r]"

        query = f"""
            MATCH path = (start {{uri: $uri}})-{rel_pattern}*{ hops}..{ hops}(neighbor)
            RETURN DISTINCT neighbor.uri AS uri, neighbor.name AS name,
                   labels(neighbor) AS labels, [r IN relationships(path) | type(r)] AS relationships
            LIMIT 100
        """

        result = await self.session.run(query, uri=node_uri)
        return [record.data() for record in await result.data()]

    async def find_path_between_nodes(
        self,
        start_uri: str,
        end_uri: str,
        max_depth: int = 5,
        relationship_types: List[str] | None = None
    ) -> List[dict]:
        """查找两个节点之间的路径"""
        rel_pattern = ""
        if relationship_types:
            rels = "|".join(relationship_types)
            rel_pattern = f":{rels}"

        query = f"""
            MATCH path = shortestPath(
                (start {{uri: $start}})-[*1..{max_depth}{rel_pattern}]-(end {{uri: $end}})
            )
            RETURN [node IN nodes(path) | {uri: node.uri, name: node.name, labels: labels(node)}] AS nodes,
                   [rel IN relationships(path) | {type: type(rel), source: startNode(rel).uri, target: endNode(rel).uri}] AS relationships
        """

        result = await self.session.run(query, start=start_uri, end=end_uri)
        data = await result.data()
        return data[0] if data else None

    async def query_nodes_by_filters(
        self,
        node_label: str,
        filters: dict[str, Any]
    ) -> List[dict]:
        """根据属性条件过滤节点"""
        conditions = []
        params = {"label": node_label}

        for key, value in filters.items():
            conditions.append(f"n.{key} = ${key}")
            params[key] = value

        where_clause = " AND ".join(conditions) if conditions else "true"

        query = f"""
            MATCH (n:{node_label})
            WHERE {where_clause}
            RETURN n.uri AS uri, n.name AS name, n AS properties
            LIMIT 100
        """

        result = await self.session.run(query, **params)
        return [record.data() for record in await result.data()]

    async def get_node_statistics(
        self,
        node_label: str | None = None
    ) -> dict:
        """获取节点统计信息"""
        if node_label:
            query = f"""
                MATCH (n:{node_label})
                RETURN count(n) AS total_count,
                       [d IN collect(n.name) | d][0..5] AS sample_names
            """
        else:
            query = """
                MATCH (n)
                RETURN labels(n) AS labels, count(n) AS count
                ORDER BY count DESC
                LIMIT 20
            """

        result = await self.session.run(query)
        if node_label:
            data = (await result.data())[0]
            return {"total_count": data["total_count"], "sample_names": data["sample_names"]}
        else:
            return {"label_distribution": [record.data() for record in await result.data()]}

    async def get_relationship_types(
        self,
        node_label: str | None = None
    ) -> List[dict]:
        """获取可用的关系类型及其使用频率"""
        if node_label:
            query = f"""
                MATCH (:{node_label})-[r]->()
                RETURN type(r) AS relationship_type, count(r) AS count
                ORDER BY count DESC
            """
        else:
            query = """
                MATCH ()-[r]->()
                RETURN type(r) AS relationship_type, count(r) AS count
                ORDER BY count DESC
                LIMIT 50
            """

        result = await self.session.run(query)
        return [record.data() for record in await result.data()]


# LangChain 工具定义
def create_langchain_tools(get_session_func):
    """创建 LangChain 工具"""

    @tool
    async def fuzzy_search_entities(
        search_term: str,
        node_label: str | None = None,
        limit: int = 10
    ) -> str:
        """根据实体名称模糊搜索节点。

        Args:
            search_term: 搜索关键词
            node_label: 可选，限制节点类型
            limit: 返回结果数量，默认10

        Returns:
            匹配的节点列表
        """
        async with await get_session_func() as session:
            tools = GraphTools(session)
            results = await tools.fuzzy_search_entities(search_term, node_label, limit)
            return f"找到 {len(results)} 个匹配实体: " + str(results)

    @tool
    async def fuzzy_search_relationships(
        search_term: str,
        limit: int = 10
    ) -> str:
        """根据关系名称模糊搜索关系类型。

        Args:
            search_term: 搜索关键词
            limit: 返回结果数量，默认10

        Returns:
            匹配的关系类型列表
        """
        async with await get_session_func() as session:
            tools = GraphTools(session)
            results = await tools.fuzzy_search_relationships(search_term, limit)
            return f"找到 {len(results)} 种关系类型: " + str(results)

    @tool
    async def query_n_hop_neighbors(
        node_uri: str,
        hops: int = 1,
        direction: str = "both"
    ) -> str:
        """查询节点的 N 跳邻居。

        Args:
            node_uri: 节点 URI
            hops: 跳数，默认1
            direction: 方向 (outgoing/incoming/both)，默认both

        Returns:
            邻居节点列表
        """
        async with await get_session_func() as session:
            tools = GraphTools(session)
            results = await tools.query_n_hop_neighbors(node_uri, hops, direction)
            return f"找到 {len(results)} 个邻居: " + str(results)

    @tool
    async def find_path_between_nodes(
        start_uri: str,
        end_uri: str,
        max_depth: int = 5
    ) -> str:
        """查找两个节点之间的路径。

        Args:
            start_uri: 起始节点 URI
            end_uri: 目标节点 URI
            max_depth: 最大深度，默认5

        Returns:
            路径信息（节点和关系）
        """
        async with await get_session_func() as session:
            tools = GraphTools(session)
            result = await tools.find_path_between_nodes(start_uri, end_uri, max_depth)
            if result:
                return f"找到路径: {result}"
            return "未找到路径"

    @tool
    async def query_nodes_by_filters(
        node_label: str,
        filters: str  # JSON string
    ) -> str:
        """根据属性条件过滤节点。

        Args:
            node_label: 节点类型
            filters: 过滤条件的 JSON 字符串，例如 '{"status": "active"}'

        Returns:
            匹配的节点列表
        """
        import json
        filter_dict = json.loads(filters)
        async with await get_session_func() as session:
            tools = GraphTools(session)
            results = await tools.query_nodes_by_filters(node_label, filter_dict)
            return f"找到 {len(results)} 个节点: " + str(results)

    @tool
    async def get_node_statistics(
        node_label: str | None = None
    ) -> str:
        """获取节点统计信息。

        Args:
            node_label: 可选，指定节点类型

        Returns:
            统计信息
        """
        async with await get_session_func() as session:
            tools = GraphTools(session)
            result = await tools.get_node_statistics(node_label)
            return f"统计信息: {result}"

    @tool
    async def get_relationship_types(
        node_label: str | None = None
    ) -> str:
        """获取可用的关系类型及其使用频率。

        Args:
            node_label: 可选，限制节点的类型

        Returns:
            关系类型列表及使用频率
        """
        async with await get_session_func() as session:
            tools = GraphTools(session)
            results = await tools.get_relationship_types(node_label)
            return f"关系类型: {results}"

    return [
        fuzzy_search_entities,
        fuzzy_search_relationships,
        query_n_hop_neighbors,
        find_path_between_nodes,
        query_nodes_by_filters,
        get_node_statistics,
        get_relationship_types,
    ]
```

**Step 3: Commit**

```bash
git add backend/
git commit -m "feat: add graph query tools"
```

---

### Task 2.7: Schema 匹配服务

**Files:**
- Create: `backend/app/services/schema_matcher.py`
- Create: `backend/app/data/synonyms.json`

**Step 1: 创建同义词库**

```bash
cat > backend/app/data/synonyms.json << 'EOF'
{
  "PurchaseOrder": ["采购订单", "PO", "订单", "采购单"],
  "PurchaseRequisition": ["采购申请", "PR", "请购单"],
  "GoodsReceipt": ["收货单", "GR", "收货记录"],
  "Supplier": ["供应商", "卖方", "供货商"],
  "Material": ["物料", "材料", "产品"],
  "BusinessPartner": ["业务伙伴", "BP", "合作伙伴"],
  "SupplierInvoice": ["供应商发票", "发票", "供应商账单"],
  "Payment": ["付款", "支付"],
  "orderedFrom": ["订购自", "向...订购", "供应商为"],
  "fulfills": ["完成", "履行", "实现"],
  "billedFor": ["开票", "开票给"]
}
EOF
```

**Step 2: 实现 schema_matcher.py**

```python
# backend/app/services/schema_matcher.py
from typing import List, dict
import json
import jieba
from difflib import SequenceMatcher
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from app.core.security import decrypt_data
from app.models.llm_config import LLMConfig
from app.models.neo4j_config import Neo4jConfig


class SchemaMatcher:
    """Schema 匹配器 - 结合 NLP 和 LLM"""

    def __init__(
        self,
        neo4j_session,
        llm_config: dict,
        neo4j_config: dict
    ):
        self.session = neo4j_session
        self.llm = ChatOpenAI(
            api_key=llm_config["api_key"],
            base_url=llm_config["base_url"],
            model=llm_config["model"],
            temperature=0
        )
        self.neo4j_config = neo4j_config
        self._load_synonyms()
        self._load_schema()

    def _load_synonyms(self):
        """加载同义词库"""
        try:
            with open("app/data/synonyms.json", "r", encoding="utf-8") as f:
                self.synonyms = json.load(f)
        except FileNotFoundError:
            self.synonyms = {}

    async def _load_schema(self):
        """从 Neo4j 加载 Schema"""
        # 加载所有类
        result = await self.session.run("MATCH (c:Class:__Schema) RETURN c")
        classes_data = await result.data()
        self.classes = {
            record["c"]["name"]: {
                "uri": record["c"]["uri"],
                "label": record["c"].get("label")
            }
            for record in classes_data
        }

        # 加载所有属性
        result = await self.session.run("MATCH (p:Property:__Schema) RETURN p")
        props_data = await result.data()
        self.properties = {
            record["p"]["name"]: {
                "uri": record["p"]["uri"],
                "label": record["p"].get("label"),
                "type": "ObjectProperty" if "ObjectProperty" in record["p"].get("labels", []) else "DataProperty"
            }
            for record in props_data
        }

    def _tokenize(self, text: str) -> List[str]:
        """中文分词"""
        return list(jieba.cut(text))

    def _fuzzy_match(self, text: str, candidates: dict, threshold: float = 0.6) -> List[tuple]:
        """模糊匹配"""
        matches = []
        for name, info in candidates.items():
            # 直接匹配
            if name.lower() in text.lower() or text.lower() in name.lower():
                matches.append((name, 1.0, "exact"))
                continue

            # 同义词匹配
            for syn in self.synonyms.get(name, []):
                if syn.lower() in text.lower():
                    matches.append((name, 0.95, "synonym"))
                    break
            else:
                # 相似度匹配
                ratio = SequenceMatcher(None, name.lower(), text.lower()).ratio()
                if ratio >= threshold:
                    matches.append((name, ratio, "fuzzy"))

        return sorted(matches, key=lambda x: -x[1])

    async def match_entities(self, query: str) -> dict:
        """匹配查询中的实体"""
        tokens = self._tokenize(query)
        entity_matches = {}

        # 对每个分词进行匹配
        for token in tokens:
            if len(token) < 2:  # 跳过太短的词
                continue

            class_matches = self._fuzzy_match(token, self.classes)
            prop_matches = self._fuzzy_match(token, self.properties)

            if class_matches:
                entity_matches[f"class:{token}"] = {
                    "type": "class",
                    "matched": class_matches[0][0],
                    "confidence": class_matches[0][1],
                    "method": class_matches[0][2]
                }
            elif prop_matches:
                entity_matches[f"property:{token}"] = {
                    "type": "property",
                    "matched": prop_matches[0][0],
                    "confidence": prop_matches[0][1],
                    "method": prop_matches[0][2]
                }

        # LLM 增强匹配
        llm_matches = await self._llm_match(query)
        # 合并结果，LLM 结果优先级更高

        return {"entities": entity_matches, "llm_entities": llm_matches}

    async def _llm_match(self, query: str) -> dict:
        """使用 LLM 进行语义匹配"""
        schema_context = self._build_schema_context()

        prompt = ChatPromptTemplate.from_template("""
你是一个知识图谱 Schema 匹配专家。根据用户的查询，识别其中涉及的实体类型和关系。

可用的 Schema 类：
{classes}

可用的关系/属性：
{properties}

用户查询：{query}

请分析查询并返回 JSON 格式：
{{
    "detected_classes": ["类名1", "类名2"],
    "detected_properties": ["属性名1"],
    "detected_entities": ["提到的具体实体名称"],
    "query_type": "path|neighbors|search|statistics",
    "confidence": "high|medium|low"
}}
""")

        chain = prompt | self.llm
        result = await chain.ainvoke({
            "classes": json.dumps(self.classes, ensure_ascii=False, indent=2),
            "properties": json.dumps(self.properties, ensure_ascii=False, indent=2),
            "query": query
        })

        try:
            return json.loads(result.content)
        except:
            return {}

    def _build_schema_context(self) -> str:
        """构建 Schema 上下文描述"""
        lines = ["Classes:"]
        for name, info in self.classes.items():
            label = info.get("label", name)
            lines.append(f"  - {name} ({label})")

        lines.append("\nProperties:")
        for name, info in self.properties.items():
            label = info.get("label", name)
            lines.append(f"  - {name} ({label})")

        return "\n".join(lines)
```

**Step 3: Commit**

```bash
git add backend/
git commit -m "feat: add schema matcher service"
```

---

### Task 2.8: Agent 实现

**Files:**
- Create: `backend/app/services/qa_agent.py`

**Step 1: 实现 QA Agent**

```python
# backend/app/services/qa_agent.py
from typing import AsyncIterator
import json
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from app.services.schema_matcher import SchemaMatcher
from app.services.graph_tools import GraphTools, create_langchain_tools
from app.core.neo4j_pool import get_neo4j_driver


class QAAgent:
    """知识图谱问答 Agent"""

    def __init__(self, user_id: int, db_session, llm_config: dict, neo4j_config: dict):
        self.user_id = user_id
        self.db_session = db_session
        self.llm_config = llm_config
        self.neo4j_config = neo4j_config

        self.llm = ChatOpenAI(
            api_key=llm_config["api_key"],
            base_url=llm_config["base_url"],
            model=llm_config["model"],
            temperature=0
        )

    async def astream_chat(self, query: str) -> AsyncIterator[dict]:
        """流式聊天"""
        # 1. Schema 匹配
        yield {"type": "thinking", "content": "正在分析问题..."}
        driver = await get_neo4j_driver(**self.neo4j_config)
        async with driver.session(database=self.neo4j_config["database"]) as session:
            matcher = SchemaMatcher(session, self.llm_config, self.neo4j_config)
            match_result = await matcher.match_entities(query)
            yield {"type": "thinking", "content": f"识别实体: {list(match_result['entities'].keys())}"}

            # 2. 创建工具
            async def get_session():
                return driver.session(database=self.neo4j_config["database"])

            tools = create_langchain_tools(get_session)

            # 3. 创建 Agent
            prompt = ChatPromptTemplate.from_messages([
                ("system", """你是一个知识图谱问答助手。用户会问你关于知识图谱的问题。

你需要：
1. 理解用户问题的意图
2. 使用可用的工具查询图谱
3. 基于查询结果回答用户问题

不要编造数据，如果工具找不到结果，如实告诉用户。"""),
                MessagesPlaceholder(variable_name="chat_history", optional=True),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad")
            ])

            agent = create_openai_functions_agent(self.llm, tools, prompt)
            executor = AgentExecutor(
                agent=agent,
                tools=tools,
                verbose=True,
                return_intermediate_steps=True
            )

            # 4. 执行查询并流式返回
            yield {"type": "content_start"}

            async for chunk in executor.astream({"input": query}):
                if "output" in chunk:
                    yield {"type": "content", "content": chunk["output"]}
                elif "intermediate_steps" in chunk:
                    for step in chunk["intermediate_steps"]:
                        if hasattr(step[0], "tool"):
                            yield {"type": "tool_used", "tool": step[0].tool, "input": step[0].tool_input}

            # 5. 收集图数据
            graph_data = await self._extract_graph_data(match_result, session)
            if graph_data:
                yield {"type": "graph_data", **graph_data}

        yield {"type": "done"}

    async def _extract_graph_data(self, match_result: dict, session) -> dict:
        """提取相关的图数据用于可视化"""
        # 根据匹配结果提取相关节点
        nodes = set()
        edges = []

        for entity_key, entity_info in match_result.get("entities", {}).items():
            if entity_info["type"] == "class":
                # 查找该类的实例
                class_name = entity_info["matched"]
                result = await session.run(
                    f"""
                    MATCH (n:{class_name})
                    RETURN n.uri AS uri, n.name AS name, labels(n) AS labels
                    LIMIT 10
                    """
                )
                for record in await result.data():
                    nodes.add(record["uri"])
                    edges.append({
                        "source": record["uri"],
                        "target": entity_info["matched"],
                        "label": "type"
                    })

        return {
            "nodes": [{"id": n, "label": n.split("#")[-1]} for n in nodes],
            "edges": edges
        }
```

**Step 2: Commit**

```bash
git add backend/
git commit -m "feat: add QA agent service"
```

---

### Task 2.9: 问答 API 和图谱 API

**Files:**
- Create: `backend/app/api/chat.py`
- Create: `backend/app/api/graph.py`

**Step 1: 实现 chat.py**

```python
# backend/app/api/chat.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import decrypt_data
from app.api.deps import get_current_user
from app.models.user import User
from app.models.llm_config import LLMConfig
from app.models.neo4j_config import Neo4jConfig
from app.services.qa_agent import QAAgent

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/stream")
async def chat_stream(
    query: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """SSE 流式问答"""

    # 获取用户配置
    llm_result = await db.execute(select(LLMConfig).where(LLMConfig.user_id == current_user.id))
    llm_config = llm_result.scalar_one_or_none()
    if not llm_config:
        raise HTTPException(status_code=400, detail="LLM not configured")

    neo4j_result = await db.execute(select(Neo4jConfig).where(Neo4jConfig.user_id == current_user.id))
    neo4j_config = neo4j_result.scalar_one_or_none()
    if not neo4j_config:
        raise HTTPException(status_code=400, detail="Neo4j not configured")

    llm_dict = {
        "api_key": decrypt_data(llm_config.api_key_encrypted),
        "base_url": llm_config.base_url,
        "model": llm_config.model
    }
    neo4j_dict = {
        "uri": decrypt_data(neo4j_config.uri_encrypted),
        "username": decrypt_data(neo4j_config.username_encrypted),
        "password": decrypt_data(neo4j_config.password_encrypted),
        "database": neo4j_config.database
    }

    agent = QAAgent(current_user.id, db, llm_dict, neo4j_dict)

    async def event_generator():
        async for chunk in agent.astream_chat(query):
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/completions")
async def chat_completion(
    query: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """非流式问答（兼容接口）"""
    # 类似实现，收集所有流式结果后一次性返回
    pass
```

**Step 2: 实现 graph.py**

```python
# backend/app/api/graph.py
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import decrypt_data
from app.api.deps import get_current_user
from app.models.user import User
from app.models.neo4j_config import Neo4jConfig
from app.core.neo4j_pool import get_neo4j_driver
from app.services.graph_tools import GraphTools
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/graph", tags=["graph"])


@router.post("/import")
async def import_graph(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """导入 OWL 文件"""
    # 获取 Neo4j 配置
    result = await db.execute(select(Neo4jConfig).where(Neo4jConfig.user_id == current_user.id))
    neo4j_config = result.scalar_one_or_none()
    if not neo4j_config:
        raise HTTPException(status_code=400, detail="Neo4j not configured")

    content = await file.read()

    # 解析并导入
    from app.services.owl_parser import OWLParser
    from app.services.graph_importer import GraphImporter

    parser = OWLParser()
    parser.load_from_string(content.decode("utf-8"))
    schema_triples, instance_triples = parser.classify_triples()

    driver = await get_neo4j_driver(
        uri=decrypt_data(neo4j_config.uri_encrypted),
        username=decrypt_data(neo4j_config.username_encrypted),
        password=decrypt_data(neo4j_config.password_encrypted),
        database=neo4j_config.database
    )

    async with driver.session(database=neo4j_config.database) as session:
        importer = GraphImporter(session)
        schema_stats = await importer.import_schema(parser)
        instance_stats = await importer.import_instances(schema_triples, instance_triples)

    return {
        "message": "Graph imported successfully",
        "schema_stats": schema_stats,
        "instance_stats": instance_stats
    }


@router.get("/node/{uri:path}")
async def get_node(
    uri: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取节点详情"""
    # 获取配置
    result = await db.execute(select(Neo4jConfig).where(Neo4jConfig.user_id == current_user.id))
    neo4j_config = result.scalar_one_or_none()
    if not neo4j_config:
        raise HTTPException(status_code=400, detail="Neo4j not configured")

    driver = await get_neo4j_driver(
        uri=decrypt_data(neo4j_config.uri_encrypted),
        username=decrypt_data(neo4j_config.username_encrypted),
        password=decrypt_data(neo4j_config.password_encrypted),
        database=neo4j_config.database
    )

    async with driver.session(database=neo4j_config.database) as session:
        record = await session.run("MATCH (n {uri: $uri}) RETURN n", uri=uri)
        data = await record.data()
        if not data:
            raise HTTPException(status_code=404, detail="Node not found")
        return data[0]["n"]


@router.get("/neighbors")
async def get_neighbors(
    uri: str,
    hops: int = 1,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取节点邻居"""
    result = await db.execute(select(Neo4jConfig).where(Neo4jConfig.user_id == current_user.id))
    neo4j_config = result.scalar_one_or_none()
    if not neo4j_config:
        raise HTTPException(status_code=400, detail="Neo4j not configured")

    driver = await get_neo4j_driver(
        uri=decrypt_data(neo4j_config.uri_encrypted),
        username=decrypt_data(neo4j_config.username_encrypted),
        password=decrypt_data(neo4j_config.password_encrypted),
        database=neo4j_config.database
    )

    async with driver.session(database=neo4j_config.database) as session:
        tools = GraphTools(session)
        neighbors = await tools.query_n_hop_neighbors(uri, hops)
        return neighbors


@router.post("/path")
async def find_path(
    start_uri: str,
    end_uri: str,
    max_depth: int = 5,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """查找路径"""
    result = await db.execute(select(Neo4jConfig).where(Neo4jConfig.user_id == current_user.id))
    neo4j_config = result.scalar_one_or_none()
    if not neo4j_config:
        raise HTTPException(status_code=400, detail="Neo4j not configured")

    driver = await get_neo4j_driver(
        uri=decrypt_data(neo4j_config.uri_encrypted),
        username=decrypt_data(neo4j_config.username_encrypted),
        password=decrypt_data(neo4j_config.password_encrypted),
        database=neo4j_config.database
    )

    async with driver.session(database=neo4j_config.database) as session:
        tools = GraphTools(session)
        path = await tools.find_path_between_nodes(start_uri, end_uri, max_depth)
        return path


@router.get("/statistics")
async def get_statistics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取图谱统计"""
    result = await db.execute(select(Neo4jConfig).where(Neo4jConfig.user_id == current_user.id))
    neo4j_config = result.scalar_one_or_none()
    if not neo4j_config:
        raise HTTPException(status_code=400, detail="Neo4j not configured")

    driver = await get_neo4j_driver(
        uri=decrypt_data(neo4j_config.uri_encrypted),
        username=decrypt_data(neo4j_config.username_encrypted),
        password=decrypt_data(neo4j_config.password_encrypted),
        database=neo4j_config.database
    )

    async with driver.session(database=neo4j_config.database) as session:
        tools = GraphTools(session)
        stats = await tools.get_node_statistics()
        return stats
```

**Step 3: 更新 main.py**

```python
# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api import auth, config, chat, graph

app = FastAPI(title="Knowledge Graph QA API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(config.router)
app.include_router(chat.router)
app.include_router(graph.router)


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
```

**Step 4: Commit**

```bash
git add backend/
git commit -m "feat: add chat and graph API endpoints"
```

---

## 第三阶段：前端实现

### Task 3.1: 认证状态和布局

**Files:**
- Create: `frontend/src/lib/auth.ts`
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/src/components/layout.tsx`

**Step 1: 实现 auth store**

```typescript
// frontend/src/lib/auth.ts
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface User {
  id: number
  username: string
}

interface AuthState {
  user: User | null
  token: string | null
  setAuth: (user: User, token: string) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      setAuth: (user, token) => set({ user, token }),
      logout: () => set({ user: null, token: null }),
    }),
    { name: 'auth-storage' }
  )
)
```

**Step 2: 实现 API 客户端**

```typescript
// frontend/src/lib/api.ts
import axios from 'axios'

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
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
    return fetch(`${process.env.NEXT_PUBLIC_API_URL}/chat/stream`, {
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
    return axios.post('/graph/import', formData, {
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'multipart/form-data',
      },
    })
  },
  getNode: (uri: string, token: string) =>
    api.get(`/graph/node/${encodeURIComponent(uri)}`),
  getNeighbors: (uri: string, hops: number, token: string) =>
    api.get(`/graph/neighbors?uri=${encodeURIComponent(uri)}&hops=${hops}`),
  findPath: (start: string, end: string, token: string) =>
    api.post('/graph/path', { start_uri: start, end_uri: end }),
  getStatistics: (token: string) => api.get('/graph/statistics'),
}
```

**Step 3: 创建布局组件**

```tsx
// frontend/src/components/layout.tsx
'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { useAuthStore } from '@/lib/auth'

export function AppLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const router = useRouter()
  const { user, logout } = useAuthStore()

  const handleLogout = () => {
    logout()
    router.push('/')
  }

  const navItems = [
    { href: '/dashboard', label: '问答' },
    { href: '/config', label: '配置' },
    { href: '/graph/import', label: '导入图谱' },
    { href: '/graph/visualize', label: '图谱可视化' },
  ]

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <h1 className="text-xl font-bold">知识图谱问答</h1>
          <nav className="flex items-center gap-4">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={`text-sm ${
                  pathname === item.href ? 'font-bold text-blue-600' : 'text-gray-600'
                }`}
              >
                {item.label}
              </Link>
            ))}
            {user && (
              <>
                <span className="text-sm text-gray-600">欢迎, {user.username}</span>
                <Button variant="ghost" size="sm" onClick={handleLogout}>
                  登出
                </Button>
              </>
            )}
          </nav>
        </div>
      </header>
      <main className="container mx-auto px-4 py-8">{children}</main>
    </div>
  )
}
```

**Step 4: Commit**

```bash
git add frontend/
git commit -m "feat: add auth store and API client"
```

---

### Task 3.2: 登录页面

**Files:**
- Create: `frontend/src/app/page.tsx`

**Step 1: 创建登录页面**

```tsx
// frontend/src/app/page.tsx
'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { authApi } from '@/lib/api'
import { useAuthStore } from '@/lib/auth'
import { toast } from 'sonner'

export default function LoginPage() {
  const router = useRouter()
  const setAuth = useAuthStore((state) => state.setAuth)
  const [isLogin, setIsLogin] = useState(true)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)

    try {
      if (isLogin) {
        const res = await authApi.login(username, password)
        setAuth({ id: 0, username: username }, res.data.access_token)
        toast.success('登录成功')
        router.push('/dashboard')
      } else {
        await authApi.register(username, password, email)
        toast.success('注册成功，请登录')
        setIsLogin(true)
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '操作失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>{isLogin ? '登录' : '注册'}</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              placeholder="用户名"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
            {!isLogin && (
              <Input
                placeholder="邮箱（可选）"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            )}
            <Input
              placeholder="密码"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? '处理中...' : isLogin ? '登录' : '注册'}
            </Button>
          </form>
          <p className="text-sm text-center mt-4">
            {isLogin ? '还没有账号？' : '已有账号？'}
            <button
              type="button"
              onClick={() => setIsLogin(!isLogin)}
              className="text-blue-600 hover:underline"
            >
              {isLogin ? '注册' : '登录'}
            </button>
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
```

**Step 2: Commit**

```bash
git add frontend/
git commit -m "feat: add login page"
```

---

### Task 3.3: 配置页面

**Files:**
- Create: `frontend/src/app/config/page.tsx`

**Step 1: 创建配置页面**

```tsx
// frontend/src/app/config/page.tsx
'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { configApi } from '@/lib/api'
import { useAuthStore } from '@/lib/auth'
import { toast } from 'sonner'

export default function ConfigPage() {
  const router = useRouter()
  const token = useAuthStore((state) => state.token)
  const [loading, setLoading] = useState(false)

  const [llm, setLLM] = useState({ api_key: '', base_url: '', model: '' })
  const [neo4j, setNeo4j] = useState({ uri: '', username: '', password: '', database: 'neo4j' })

  useEffect(() => {
    if (!token) {
      router.push('/')
      return
    }
    loadConfigs()
  }, [token])

  const loadConfigs = async () => {
    try {
      const [llmRes, neo4jRes] = await Promise.all([
        configApi.getLLM(),
        configApi.getNeo4j(),
      ])
      setLLM({ ...llmRes.data, api_key: '' }) // 不回填 API key
      setNeo4j(neo4jRes.data)
    } catch (err) {
      console.error('Failed to load configs')
    }
  }

  const handleTestLLM = async () => {
    try {
      const res = await configApi.testLLM(llm)
      if (res.data.success) {
        toast.success('LLM 连接成功')
      } else {
        toast.error(res.data.message)
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '连接失败')
    }
  }

  const handleTestNeo4j = async () => {
    try {
      const res = await configApi.testNeo4j(neo4j)
      if (res.data.success) {
        toast.success('Neo4j 连接成功')
      } else {
        toast.error(res.data.message)
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '连接失败')
    }
  }

  const handleSaveLLM = async () => {
    setLoading(true)
    try {
      await configApi.updateLLM(llm)
      toast.success('LLM 配置已保存')
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '保存失败')
    } finally {
      setLoading(false)
    }
  }

  const handleSaveNeo4j = async () => {
    setLoading(true)
    try {
      await configApi.updateNeo4j(neo4j)
      toast.success('Neo4j 配置已保存')
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '保存失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">配置管理</h1>

      <Tabs defaultValue="llm">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="llm">LLM 配置</TabsTrigger>
          <TabsTrigger value="neo4j">Neo4j 配置</TabsTrigger>
        </TabsList>

        <TabsContent value="llm">
          <Card>
            <CardHeader>
              <CardTitle>LLM API 配置</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <Input
                placeholder="API Key"
                type="password"
                value={llm.api_key}
                onChange={(e) => setLLM({ ...llm, api_key: e.target.value })}
              />
              <Input
                placeholder="Base URL (如 https://api.openai.com/v1)"
                value={llm.base_url}
                onChange={(e) => setLLM({ ...llm, base_url: e.target.value })}
              />
              <Input
                placeholder="Model (如 gpt-4)"
                value={llm.model}
                onChange={(e) => setLLM({ ...llm, model: e.target.value })}
              />
              <div className="flex gap-2">
                <Button onClick={handleSaveLLM} disabled={loading}>
                  保存
                </Button>
                <Button variant="outline" onClick={handleTestLLM}>
                  测试连接
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="neo4j">
          <Card>
            <CardHeader>
              <CardTitle>Neo4j 配置</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <Input
                placeholder="URI (如 bolt+s://xxx.databases.neo4j.io)"
                value={neo4j.uri}
                onChange={(e) => setNeo4j({ ...neo4j, uri: e.target.value })}
              />
              <Input
                placeholder="用户名"
                value={neo4j.username}
                onChange={(e) => setNeo4j({ ...neo4j, username: e.target.value })}
              />
              <Input
                placeholder="密码"
                type="password"
                value={neo4j.password}
                onChange={(e) => setNeo4j({ ...neo4j, password: e.target.value })}
              />
              <Input
                placeholder="数据库 (默认 neo4j)"
                value={neo4j.database}
                onChange={(e) => setNeo4j({ ...neo4j, database: e.target.value })}
              />
              <div className="flex gap-2">
                <Button onClick={handleSaveNeo4j} disabled={loading}>
                  保存
                </Button>
                <Button variant="outline" onClick={handleTestNeo4j}>
                  测试连接
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
```

**Step 2: 添加 Toast 组件**

```tsx
// frontend/src/app/layout.tsx
import { Toaster } from 'sonner'

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh">
      <body>
        {children}
        <Toaster position="top-center" richColors />
      </body>
    </html>
  )
}
```

**Step 3: Commit**

```bash
git add frontend/
git commit -m "feat: add config page"
```

---

### Task 3.4: 仪表盘（聊天界面）

**Files:**
- Create: `frontend/src/app/dashboard/page.tsx`
- Create: `frontend/src/components/chat.tsx`
- Create: `frontend/src/components/graph-preview.tsx`

**Step 1: 创建聊天组件**

```tsx
// frontend/src/components/chat.tsx
'use client'

import { useState, useRef, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card } from '@/components/ui/card'
import { chatApi } from '@/lib/api'
import { useAuthStore } from '@/lib/auth'
import { Send } from 'lucide-react'

interface Message {
  role: 'user' | 'assistant'
  content: string
  thinking?: string
  graphData?: any
}

export function Chat({ onGraphData }: { onGraphData: (data: any) => void }) {
  const token = useAuthStore((state) => state.token)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || loading) return

    const userMessage = input
    setInput('')
    setMessages((prev) => [...prev, { role: 'user', content: userMessage }])
    setLoading(true)

    try {
      const response = await chatApi.stream(userMessage, token!)
      const reader = response.body!.getReader()
      const decoder = new TextDecoder()

      let assistantMessage = ''
      let thinking = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value)
        const lines = chunk.split('\n').filter(Boolean)

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const data = JSON.parse(line.slice(6))

            if (data.type === 'thinking') {
              thinking = data.content
              setMessages((prev) => {
                const newMsgs = [...prev]
                const last = newMsgs[newMsgs.length - 1]
                if (last?.role === 'assistant') {
                  last.thinking = thinking
                } else {
                  newMsgs.push({ role: 'assistant', content: '', thinking })
                }
                return newMsgs
              })
            } else if (data.type === 'content') {
              assistantMessage += data.content
              setMessages((prev) => {
                const newMsgs = [...prev]
                const last = newMsgs[newMsgs.length - 1]
                if (last?.role === 'assistant') {
                  last.content = assistantMessage
                } else {
                  newMsgs.push({ role: 'assistant', content: assistantMessage })
                }
                return newMsgs
              })
            } else if (data.type === 'graph_data') {
              onGraphData(data)
              setMessages((prev) => {
                const newMsgs = [...prev]
                const last = newMsgs[newMsgs.length - 1]
                if (last) {
                  last.graphData = data
                }
                return newMsgs
              })
            }
          } catch (e) {
            console.error('Failed to parse SSE data:', e)
          }
        }
      }
    } catch (err) {
      console.error('Chat error:', err)
      setMessages((prev) => [...prev, { role: 'assistant', content: '抱歉，发生了错误。' }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto space-y-4 mb-4">
        {messages.length === 0 && (
          <div className="text-center text-gray-400 mt-20">
            <p>开始提问吧！例如：</p>
            <p className="mt-2">"PO_2024_001 是向哪个供应商订购的？"</p>
          </div>
        )}
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <Card
              className={`max-w-[80%] p-3 ${
                msg.role === 'user' ? 'bg-blue-50' : 'bg-gray-50'
              }`}
            >
              {msg.thinking && (
                <p className="text-xs text-gray-500 mb-2">💭 {msg.thinking}</p>
              )}
              <p className="whitespace-pre-wrap">{msg.content}</p>
              {msg.graphData && (
                <p className="text-xs text-green-600 mt-2">📊 相关图谱已显示</p>
              )}
            </Card>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <Card className="bg-gray-50 p-3">
              <p className="text-gray-500">正在思考...</p>
            </Card>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSubmit} className="flex gap-2">
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="输入你的问题..."
          disabled={loading}
        />
        <Button type="submit" disabled={loading || !input.trim()}>
          <Send className="h-4 w-4" />
        </Button>
      </form>
    </div>
  )
}
```

**Step 2: 创建图谱预览组件**

```tsx
// frontend/src/components/graph-preview.tsx
'use client'

import { useEffect, useRef } from 'react'
import cytoscape, { Core } from 'cytoscape'

interface GraphData {
  nodes: Array<{ id: string; label: string }>
  edges: Array<{ source: string; target: string; label?: string }>
}

export function GraphPreview({ data }: { data: GraphData | null }) {
  const containerRef = useRef<HTMLDivElement>(null)
  const cyRef = useRef<Core | null>(null)

  useEffect(() => {
    if (!containerRef.current) return

    if (!cyRef.current) {
      cyRef.current = cytoscape({
        container: containerRef.current,
        style: [
          {
            selector: 'node',
            style: {
              'label': 'data(label)',
              'text-valign': 'center',
              'text-halign': 'center',
              'background-color': '#4F46E5',
              'color': '#fff',
              'width': '40px',
              'height': '40px',
            },
          },
          {
            selector: 'edge',
            style: {
              'width': 2,
              'line-color': '#94a3b8',
              'target-arrow-color': '#94a3b8',
              'target-arrow-shape': 'triangle',
              'curve-style': 'bezier',
            },
          },
        ],
        layout: {
          name: 'breadthfirst',
          directed: true,
        },
      })
    }

    return () => {
      cyRef.current?.destroy()
      cyRef.current = null
    }
  }, [])

  useEffect(() => {
    if (!cyRef.current || !data) return

    const elements = [
      ...data.nodes.map((n) => ({ data: { id: n.id, label: n.label } })),
      ...data.edges.map((e, i) => ({
        data: { id: `e${i}`, source: e.source, target: e.target, label: e.label },
      })),
    ]

    cyRef.current.json({ elements })
    cyRef.current.layout({ name: 'breadthfirst' }).run()
    cyRef.current.fit()
  }, [data])

  return (
    <div className="h-full bg-white rounded-lg border overflow-hidden">
      {data ? (
        <div ref={containerRef} className="w-full h-full" />
      ) : (
        <div className="flex items-center justify-center h-full text-gray-400">
          暂无图谱数据
        </div>
      )}
    </div>
  )
}
```

**Step 3: 创建仪表盘页面**

```tsx
// frontend/src/app/dashboard/page.tsx
'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { AppLayout } from '@/components/layout'
import { Chat } from '@/components/chat'
import { GraphPreview } from '@/components/graph-preview'
import { useAuthStore } from '@/lib/auth'

export default function DashboardPage() {
  const router = useRouter()
  const token = useAuthStore((state) => state.token)
  const [graphData, setGraphData] = useState<any>(null)

  if (!token) {
    router.push('/')
    return null
  }

  return (
    <AppLayout>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-[calc(100vh-200px)]">
        <div className="bg-white rounded-lg border p-4">
          <h2 className="text-lg font-semibold mb-4">问答</h2>
          <Chat onGraphData={setGraphData} />
        </div>
        <div className="bg-white rounded-lg border p-4">
          <h2 className="text-lg font-semibold mb-4">图谱预览</h2>
          <GraphPreview data={graphData} />
        </div>
      </div>
    </AppLayout>
  )
}
```

**Step 4: Commit**

```bash
git add frontend/
git commit -m "feat: add dashboard with chat and graph preview"
```

---

### Task 3.5: 图谱导入页面

**Files:**
- Create: `frontend/src/app/graph/import/page.tsx`

**Step 1: 创建导入页面**

```tsx
// frontend/src/app/graph/import/page.tsx
'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { AppLayout } from '@/components/layout'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { graphApi } from '@/lib/api'
import { useAuthStore } from '@/lib/auth'
import { toast } from 'sonner'
import { Upload } from 'lucide-react'

export default function ImportPage() {
  const router = useRouter()
  const token = useAuthStore((state) => state.token)
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<any>(null)

  if (!token) {
    router.push('/')
    return null
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0])
    }
  }

  const handleImport = async () => {
    if (!file) return

    setLoading(true)
    try {
      const res = await graphApi.import(file, token)
      setResult(res.data)
      toast.success('图谱导入成功！')
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '导入失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AppLayout>
      <div className="max-w-2xl mx-auto">
        <h1 className="text-2xl font-bold mb-6">导入 OWL 图谱</h1>

        <Card>
          <CardHeader>
            <CardTitle>上传文件</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="border-2 border-dashed rounded-lg p-8 text-center">
              <Upload className="h-12 w-12 mx-auto mb-4 text-gray-400" />
              <input
                type="file"
                accept=".ttl,.owl,.rdf"
                onChange={handleFileChange}
                className="hidden"
                id="file-upload"
              />
              <label htmlFor="file-upload" className="cursor-pointer">
                <span className="text-blue-600 hover:underline">
                  点击选择文件
                </span>
                <span className="text-gray-400 ml-2">或拖拽文件到此处</span>
              </label>
              {file && (
                <p className="mt-2 text-sm text-gray-600">已选择: {file.name}</p>
              )}
            </div>

            <Button onClick={handleImport} disabled={!file || loading} className="w-full">
              {loading ? '导入中...' : '开始导入'}
            </Button>

            {result && (
              <div className="mt-4 p-4 bg-green-50 rounded-lg">
                <h3 className="font-semibold text-green-800">导入成功！</h3>
                <p className="text-sm text-green-700">
                  Schema: {result.schema_stats.classes} 个类,
                  {result.schema_stats.properties} 个属性
                </p>
                <p className="text-sm text-green-700">
                  Instance: {result.instance_stats.nodes} 个节点,
                  {result.instance_stats.relationships} 个关系
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </AppLayout>
  )
}
```

**Step 2: Commit**

```bash
git add frontend/
git commit -m "feat: add graph import page"
```

---

### Task 3.6: 图谱可视化页面

**Files:**
- Create: `frontend/src/app/graph/visualize/page.tsx`
- Create: `frontend/src/components/graph-viewer.tsx`

**Step 1: 创建完整图谱查看器**

```tsx
// frontend/src/components/graph-viewer.tsx
'use client'

import { useEffect, useRef, useState } from 'react'
import cytoscape, { Core, ElementDefinition } from 'cytoscape'
import { graphApi } from '@/lib/api'
import { useAuthStore } from '@/lib/auth'
import { Button } from '@/components/ui/button'
import { ZoomIn, ZoomOut, Maximize2 } from 'lucide-react'

export function GraphViewer() {
  const token = useAuthStore((state) => state.token)
  const containerRef = useRef<HTMLDivElement>(null)
  const cyRef = useRef<Core | null>(null)
  const [selectedNode, setSelectedNode] = useState<any>(null)

  useEffect(() => {
    if (!containerRef.current) return

    cyRef.current = cytoscape({
      container: containerRef.current,
      style: [
        {
          selector: 'node',
          style: {
            'label': 'data(label)',
            'text-valign': 'center',
            'text-halign': 'center',
            'background-color': '#4F46E5',
            'color': '#fff',
            'width': '50px',
            'height': '50px',
            'text-wrap': 'wrap',
            'text-max-width': '80px',
          },
        },
        {
          selector: 'node:selected',
          style: {
            'border-width': 3,
            'border-color': '#F59E0B',
          },
        },
        {
          selector: 'edge',
          style: {
            'width': 2,
            'line-color': '#94a3b8',
            'target-arrow-color': '#94a3b8',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'label': 'data(label)',
            'text-rotation': 'autorotate',
            'text-margin-y': -10,
          },
        },
      ],
      layout: {
        name: 'concentric',
      },
    })

    // 双击展开邻居
    cyRef.current.on('dblclick', 'node', async (evt) => {
      const node = evt.target
      const uri = node.data('id')
      await expandNode(uri)
    })

    // 单击选中节点
    cyRef.current.on('tap', 'node', (evt) => {
      const node = evt.target
      setSelectedNode(node.data())
    })

    // 单击空白处取消选中
    cyRef.current.on('tap', (evt) => {
      if (evt.target === cyRef.current) {
        setSelectedNode(null)
      }
    })

    return () => {
      cyRef.current?.destroy()
    }
  }, [])

  const loadInitialGraph = async () => {
    try {
      const res = await graphApi.getStatistics(token!)
      // 这里简化处理，实际应该根据统计数据加载初始节点
      const elements: ElementDefinition[] = [
        { data: { id: 'demo1', label: '示例节点1' } },
        { data: { id: 'demo2', label: '示例节点2' } },
        { data: { id: 'e1', source: 'demo1', target: 'demo2', label: '关系' } },
      ]
      cyRef.current?.json({ elements })
      cyRef.current?.layout({ name: 'concentric' }).run()
    } catch (err) {
      console.error('Failed to load graph:', err)
    }
  }

  const expandNode = async (uri: string) => {
    try {
      const res = await graphApi.getNeighbors(uri, 1, token!)
      const neighbors = res.data

      const newNodes = neighbors.map((n: any) => ({
        data: { id: n.uri, label: n.name },
      }))

      const newEdges = neighbors.flatMap((n: any) =>
        n.relationships?.map((rel: string, i: number) => ({
          data: {
            id: `${uri}-${n.uri}-${i}`,
            source: uri,
            target: n.uri,
            label: rel,
          },
        })) || []
      )

      cyRef.current?.add([...newNodes, ...newEdges])
      cyRef.current?.layout({ name: 'concentric' }).run()
    } catch (err) {
      console.error('Failed to expand node:', err)
    }
  }

  const handleZoomIn = () => cyRef.current?.zoom(cyRef.current.zoom() * 1.2)
  const handleZoomOut = () => cyRef.current?.zoom(cyRef.current.zoom() * 0.8)
  const handleFit = () => cyRef.current?.fit()

  return (
    <div className="relative h-full">
      <div className="absolute top-4 left-4 z-10 flex flex-col gap-2">
        <Button size="icon" variant="secondary" onClick={handleZoomIn}>
          <ZoomIn className="h-4 w-4" />
        </Button>
        <Button size="icon" variant="secondary" onClick={handleZoomOut}>
          <ZoomOut className="h-4 w-4" />
        </Button>
        <Button size="icon" variant="secondary" onClick={handleFit}>
          <Maximize2 className="h-4 w-4" />
        </Button>
      </div>

      {selectedNode && (
        <div className="absolute top-4 right-4 z-10 bg-white p-4 rounded-lg shadow-lg max-w-xs">
          <h3 className="font-semibold">节点详情</h3>
          <p className="text-sm">URI: {selectedNode.id}</p>
          <p className="text-sm">名称: {selectedNode.label}</p>
          <Button
            size="sm"
            variant="outline"
            className="mt-2"
            onClick={() => expandNode(selectedNode.id)}
          >
            展开邻居
          </Button>
        </div>
      )}

      <div ref={containerRef} className="w-full h-full bg-gray-50" />
    </div>
  )
}
```

**Step 2: 创建可视化页面**

```tsx
// frontend/src/app/graph/visualize/page.tsx
'use client'

import { useRouter } from 'next/navigation'
import { AppLayout } from '@/components/layout'
import { GraphViewer } from '@/components/graph-viewer'
import { useAuthStore } from '@/lib/auth'

export default function VisualizePage() {
  const router = useRouter()
  const token = useAuthStore((state) => state.token)

  if (!token) {
    router.push('/')
    return null
  }

  return (
    <AppLayout>
      <div className="h-[calc(100vh-200px)]">
        <GraphViewer />
      </div>
    </AppLayout>
  )
}
```

**Step 3: Commit**

```bash
git add frontend/
git commit -m "feat: add graph visualization page"
```

---

## 第四阶段：测试与集成

### Task 4.1: 端到端测试

**Files:**
- Create: `tests/e2e/chat.spec.ts`
- Create: `playwright.config.ts`

**Step 1: 配置 Playwright**

```bash
cd frontend
pnpm exec playwright install
```

```typescript
// playwright.config.ts
import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
  webServer: {
    command: 'pnpm dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
  },
})
```

**Step 2: 编写 E2E 测试**

```typescript
// tests/e2e/complete-flow.spec.ts
import { test, expect } from '@playwright/test'

test.describe('知识图谱问答 E2E', () => {
  test.beforeEach(async ({ page }) => {
    // 登录
    await page.goto('/')
    await page.fill('input[placeholder="用户名"]', 'admin')
    await page.fill('input[placeholder="密码"]', 'admin123')
    await page.click('button[type="submit"]')
    await page.waitForURL('/dashboard')
  })

  test('配置 LLM 和 Neo4j', async ({ page }) => {
    await page.goto('/config')

    // 配置 LLM
    await page.click('text=LLM 配置')
    await page.fill('input[placeholder*="API Key"]', process.env.TEST_API_KEY || 'test-key')
    await page.fill('input[placeholder*="Base URL"]', process.env.TEST_BASE_URL || 'https://api.openai.com/v1')
    await page.fill('input[placeholder*="Model"]', process.env.TEST_MODEL || 'gpt-3.5-turbo')
    await page.click('button:has-text("保存")')

    // 配置 Neo4j
    await page.click('text=Neo4j 配置')
    await page.fill('input[placeholder*="URI"]', process.env.TEST_NEO4J_URI || 'bolt://localhost:7687')
    await page.fill('input[placeholder*="用户名"]', process.env.TEST_NEO4J_USER || 'neo4j')
    await page.fill('input[placeholder*="密码"]', process.env.TEST_NEO4J_PASS || 'password')
    await page.click('button:has-text("保存")')

    await expect(page.locator('text=LLM 配置已保存')).toBeVisible()
  })

  test('导入 OWL 文件', async ({ page }) => {
    await page.goto('/graph/import')

    // 上传文件
    const fileInput = await page.locator('input[type="file"]')
    await fileInput.setInputFiles('../sample.ttl')

    await page.click('button:has-text("开始导入")')
    await page.waitForTimeout(5000)

    await expect(page.locator('text=导入成功')).toBeVisible()
  })

  test('问答测试', async ({ page }) => {
    await page.goto('/dashboard')

    await page.fill('textarea[placeholder*="输入问题"]', 'PO_2024_001 是向哪个供应商订购的？')
    await page.click('button[type="submit"]')

    // 等待回答
    await page.waitForTimeout(10000)

    const messages = page.locator('.max-w-\\[80\\%\\]')
    await expect(messages).toHaveCount(3) // 用户 + 助手

    // 验证回答中包含关键信息
    await expect(page.locator('text=BP_10001')).toBeVisible()
  })
})
```

**Step 3: Commit**

```bash
git add tests/
git commit -m "feat: add E2E tests"
```

---

### Task 4.2: 最终验收测试

**验收步骤**

1. **启动后端**
```bash
cd backend
uv run python -m app.core.init_db  # 初始化数据库
uv run uvicorn app.main:app --reload
```

2. **启动前端**
```bash
cd frontend
pnpm dev
```

3. **验收清单**
- [ ] 登录页面正常显示，可以注册/登录
- [ ] 配置页面可以保存 LLM 和 Neo4j 配置
- [ ] 测试连接功能正常
- [ ] 可以导入 sample.ttl 文件
- [ ] 导入后可以看到图谱统计
- [ ] 问答页面可以发送问题
- [ ] LLM 返回正确的回答（基于图谱数据）
- [ ] 图谱预览正确显示相关节点
- [ ] 图谱可视化页面可以展开节点邻居
- [ ] 端到端测试全部通过

4. **测试问题示例**
- "PO_2024_001 是向哪个供应商订购的？" → 应该回答 BP_10001
- "GoodsReceipt GR_0001 完成了哪个采购订单？" → 应该回答 PO_2024_001
- "列出所有的物料类别" → 应该列出 PurchasingCategory 相关内容

**Step 4: Commit 完成版本**

```bash
git add .
git commit -m "feat: complete knowledge graph Q&A application"
```

---

## 附录：运行说明

### 开发环境启动

```bash
# 后端
cd backend
uv sync
uv run python -m app.core.init_db
uv run uvicorn app.main:app --reload

# 前端
cd frontend
pnpm install
pnpm dev
```

### 生产环境部署

```bash
# 后端
cd backend
uv sync --no-dev
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000

# 前端
cd frontend
pnpm build
pnpm start
```

### 测试

```bash
# 后端单元测试
cd backend
uv run pytest

# 前端 E2E 测试
cd frontend
pnpm exec playwright test
```
