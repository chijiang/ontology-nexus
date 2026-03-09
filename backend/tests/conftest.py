import sys
import os
import pytest
from pathlib import Path
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

# Set required environment variables for tests
os.environ.setdefault("SECRET_KEY", "test_secret_key_for_testing")
os.environ.setdefault("DATABASE_URL", "sqlite:///test.db")
os.environ.setdefault("ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")

# Add backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.main import app
from app.core.database import get_db


# ============================================================================
# Test Database Setup (for API tests that need database)
# ============================================================================

# Test database URL (SQLite in-memory)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


test_engine = None
TestSessionLocal = None


@pytest.fixture(autouse=True)
async def setup_test_db():
    """Set up test database for tests that need it.

    Note: This fixture must be explicitly requested by tests that need database access.
    """
    global test_engine, TestSessionLocal

    # Import models
    from app.models.scheduled_task import ScheduledTask, TaskExecution
    from sqlalchemy import (
        Table,
        Column,
        Integer,
        String,
        Text,
        Boolean,
        DateTime,
        ForeignKey,
        MetaData,
    )

    # Create engine for SQLite
    test_engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Mock scheduler_service to avoid real DB connection in lifespan
    from unittest.mock import AsyncMock, MagicMock
    from datetime import datetime

    # Create a fake scheduler class with explicit sync/async methods
    class FakeSchedulerService:
        def __init__(self):
            self.trigger_task_manually = AsyncMock(return_value={
                "id": 1,
                "task_id": 1,
                "status": "pending",
                "started_at": datetime.now(),
                "retry_count": 0,
                "is_retry": False,
            })
            self.validate_task_schedule = MagicMock()
            self.reschedule_task_safely = AsyncMock()
            self.unschedule_task = AsyncMock()

    app.state.scheduler_service = FakeSchedulerService()

    # Create session factory
    TestSessionLocal = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Create tables (manually to handle JSONB -> Text conversion for SQLite)
    async with test_engine.begin() as conn:

        def create_tables(connection):
            # Create ScheduledTask table
            ScheduledTask.__table__.create(connection, checkfirst=True)

            # Create TaskExecution table using the same metadata as ScheduledTask
            metadata = ScheduledTask.metadata
            task_executions_table = Table(
                "task_executions",
                metadata,
                Column("id", Integer, primary_key=True),
                Column(
                    "task_id",
                    Integer,
                    ForeignKey("scheduled_tasks.id", ondelete="CASCADE"),
                    nullable=False,
                ),
                Column("status", String(20), nullable=False),
                Column("started_at", DateTime, nullable=False),
                Column("completed_at", DateTime),
                Column("duration_seconds", Integer),
                Column("result_data", Text),  # Text instead of JSONB for SQLite
                Column("error_message", Text),
                Column("error_type", String(100)),
                Column("retry_count", Integer, default=0),
                Column("is_retry", Boolean, default=False),
                Column("triggered_by", String(50)),
                extend_existing=True,
            )
            task_executions_table.create(connection, checkfirst=True)

        await conn.run_sync(create_tables)

    # Override the get_db dependency
    async def get_test_db():
        async with TestSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = get_test_db

    yield

    # Clean up
    app.dependency_overrides.clear()
    if test_engine:
        await test_engine.dispose()


@pytest.fixture
async def db(setup_test_db) -> AsyncGenerator[AsyncSession, None]:
    """Get a test database session (requires setup_test_db fixture)."""
    async with TestSessionLocal() as session:
        yield session


# ============================================================================
# Async Client Fixture
# ============================================================================


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client for the FastAPI app."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        yield ac
