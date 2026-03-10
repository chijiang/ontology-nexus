"""ERP Emulator Database Configuration

SQLite database setup using SQLAlchemy async patterns.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool
from config import settings, get_data_dir
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def get_database_url() -> str:
    """Get the database URL with absolute path"""
    db_path = settings.DATABASE_URL

    if db_path.startswith("sqlite+aiosqlite:///"):
        # Extract relative path and make it absolute
        relative_path = db_path.replace("sqlite+aiosqlite:///", "")
        data_dir = get_data_dir()
        absolute_path = data_dir / relative_path
        absolute_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite+aiosqlite:///{absolute_path}"

    return db_path


def create_engine():
    """Create async database engine"""
    # Always use SQLite for ERP emulator to ensure isolation
    data_dir = get_data_dir()
    db_path = data_dir / "erp_emulator.db"
    db_url = f"sqlite+aiosqlite:///{db_path}"

    logger.info(f"Using ERP Emulator database: {db_path}")

    return create_async_engine(
        db_url,
        connect_args={"check_same_thread": False},
        poolclass=NullPool,
        echo=settings.DEBUG,
    )


engine = create_engine()
async_session_maker = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


class Base(DeclarativeBase):
    """Base class for all ERP models"""

    pass


async def get_db() -> AsyncSession:
    """Dependency for getting database sessions"""
    async with async_session_maker() as session:
        yield session


async def init_db():
    """Initialize database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("ERP Emulator database initialized")


async def drop_all():
    """Drop all tables (useful for testing)"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        logger.info("All ERP Emulator tables dropped")
