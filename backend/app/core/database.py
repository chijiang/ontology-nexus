# backend/app/core/database.py
"""数据库配置和会话管理

支持 PostgreSQL (asyncpg) 和 SQLite (aiosqlite)
根据 DATABASE_URL 自动检测数据库类型
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import NullPool
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


def _create_engine():
    """根据 DATABASE_URL 创建对应的数据库引擎"""
    db_url = settings.effective_database_url

    if db_url.startswith("postgresql://") or db_url.startswith("postgresql+asyncpg://"):
        # PostgreSQL 配置
        if not db_url.startswith("postgresql+asyncpg://"):
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")

        logger.info(f"Using PostgreSQL database: {db_url.split('@')[-1]}")
        return create_async_engine(
            db_url,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            echo=False,
        )

    elif db_url.startswith("sqlite://"):
        # SQLite 配置（开发/测试用）
        db_url = db_url.replace("sqlite://", "sqlite+aiosqlite://")
        logger.info(f"Using SQLite database: {db_url}")
        return create_async_engine(
            db_url,
            connect_args={"check_same_thread": False},
            poolclass=NullPool,  # SQLite 不需要连接池
        )

    else:
        raise ValueError(f"Unsupported database URL scheme: {db_url}")


engine = _create_engine()
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session
