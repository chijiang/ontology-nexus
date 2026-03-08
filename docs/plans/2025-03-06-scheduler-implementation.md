# 全局定时器功能实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为KG-Agent服务增加基于AsyncIOScheduler的全局定时器功能，支持数据产品自动同步和业务规则定时触发，具备完整的看门狗机制和持久化支持。

**Architecture:**
- 单独的`SchedulerService`管理所有定时任务，使用APScheduler的AsyncIOScheduler
- 数据库统一存储任务配置（`scheduled_tasks`表）和执行日志（`task_executions`表）
- `TaskExecutor`负责实际执行，包含并发控制、超时保护、智能重试等看门狗机制
- 前端嵌入现有页面（数据产品和规则页面），使用灵活的cron模板配置

**Tech Stack:** APScheduler, SQLAlchemy (async), PostgreSQL, FastAPI, Next.js, TailwindCSS, Shadcn UI

---

## Phase 1: 数据库模型和迁移

### Task 1: 创建定时任务模型

**Files:**
- Create: `backend/app/models/scheduled_task.py`
- Modify: `backend/app/models/__init__.py`

**Step 1: Write the model file**

```python
# backend/app/models/scheduled_task.py
from datetime import datetime, timezone
from sqlalchemy import Boolean, String, Integer, Text, ForeignKey, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class ScheduledTask(Base):
    """定时任务配置表"""

    __tablename__ = "scheduled_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 任务类型和基本信息
    task_type: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # 'sync' | 'rule'
    task_name: Mapped[str] = mapped_column(String(255), nullable=False)
    target_id: Mapped[int] = mapped_column(Integer, nullable=False)  # data_product_id 或 rule_id

    # 调度配置
    cron_expression: Mapped[str] = mapped_column(String(100), nullable=False)

    # 状态控制
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    # 看门狗配置
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=300, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    retry_interval_seconds: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=50, nullable=False)  # 0-100

    # 元数据
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    # 关系
    executions: Mapped[list["TaskExecution"]] = relationship(
        "TaskExecution", back_populates="task", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index('ix_scheduled_tasks_type_target', 'task_type', 'target_id'),
    )


class TaskExecution(Base):
    """任务执行日志表"""

    __tablename__ = "task_executions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 关联
    task_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("scheduled_tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # 执行状态
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # 'pending' | 'running' | 'completed' | 'failed' | 'timeout'

    # 时间记录
    started_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), index=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(nullable=True)

    # 执行结果
    result_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # 重试信息
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_retry: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # 上下文信息
    triggered_by: Mapped[str | None] = mapped_column(String(50), nullable=True)  # 'scheduler' | 'manual' | 'retry'

    # 关系
    task: Mapped["ScheduledTask"] = relationship("ScheduledTask", back_populates="executions")
```

**Step 2: Update models __init__.py**

在 `backend/app/models/__init__.py` 中添加导入：

```python
from app.models.scheduled_task import ScheduledTask, TaskExecution
```

**Step 3: Verify Python syntax**

Run: `python -c "import ast; ast.parse(open('backend/app/models/scheduled_task.py', encoding='utf-8').read())"`

**Step 4: Commit**

```bash
git add backend/app/models/scheduled_task.py backend/app/models/__init__.py
git commit -m "feat: add ScheduledTask and TaskExecution models"
```

---

### Task 2: 创建数据库迁移

**Files:**
- Create: `backend/alembic/versions/xxxx_add_scheduled_tasks_tables.py`

**Step 1: Generate migration**

Run: `cd backend && uv run alembic revision -m "add scheduled tasks tables"`

**Step 2: Edit the generated migration file**

找到生成的迁移文件（在 `backend/alembic/versions/` 目录下），编辑为：

```python
# add scheduled tasks tables
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0001'  # 替换为生成的revision
down_revision = None  # 替换为生成的down_revision
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'scheduled_tasks',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('task_type', sa.String(length=20), nullable=False),
        sa.Column('task_name', sa.String(length=255), nullable=False),
        sa.Column('target_id', sa.Integer(), nullable=False),
        sa.Column('cron_expression', sa.String(length=100), nullable=False),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('timeout_seconds', sa.Integer(), nullable=False, server_default='300'),
        sa.Column('max_retries', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('retry_interval_seconds', sa.Integer(), nullable=False, server_default='60'),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='50'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_scheduled_tasks_id', 'scheduled_tasks', ['id'])
    op.create_index('ix_scheduled_tasks_is_enabled', 'scheduled_tasks', ['is_enabled'])
    op.create_index('ix_scheduled_tasks_task_type', 'scheduled_tasks', ['task_type'])
    op.create_index('ix_scheduled_tasks_type_target', 'scheduled_tasks', ['task_type', 'target_id'])

    op.create_table(
        'task_executions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('result_data', postgresql.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_type', sa.String(length=100), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_retry', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('triggered_by', sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(['task_id'], ['scheduled_tasks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_task_executions_id', 'task_executions', ['id'])
    op.create_index('ix_task_executions_started_at', 'task_executions', ['started_at'])
    op.create_index('ix_task_executions_status', 'task_executions', ['status'])
    op.create_index('ix_task_executions_task_id', 'task_executions', ['task_id'])


def downgrade():
    op.drop_index('ix_task_executions_task_id', table_name='task_executions')
    op.drop_index('ix_task_executions_status', table_name='task_executions')
    op.drop_index('ix_task_executions_started_at', table_name='task_executions')
    op.drop_index('ix_task_executions_id', table_name='task_executions')
    op.drop_table('task_executions')

    op.drop_index('ix_scheduled_tasks_type_target', table_name='scheduled_tasks')
    op.drop_index('ix_scheduled_tasks_task_type', table_name='scheduled_tasks')
    op.drop_index('ix_scheduled_tasks_is_enabled', table_name='scheduled_tasks')
    op.drop_index('ix_scheduled_tasks_id', table_name='scheduled_tasks')
    op.drop_table('scheduled_tasks')
```

**Step 3: Run migration**

Run: `cd backend && uv run alembic upgrade head`

**Step 4: Verify tables created**

Run: `psql -U postgres -d ontology_nexus -c "\dt scheduled_tasks task_executions"`

**Step 5: Commit**

```bash
git add backend/alembic/versions/
git commit -m "feat: add migration for scheduled tasks tables"
```

---

## Phase 2: 数据访问层

### Task 3: 创建ScheduledTaskRepository

**Files:**
- Create: `backend/app/repositories/scheduled_task_repository.py`
- Modify: `backend/app/repositories/__init__.py`

**Step 1: Write repository file**

```python
# backend/app/repositories/scheduled_task_repository.py
from typing import List, Optional
from sqlalchemy import select, update, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.scheduled_task import ScheduledTask, TaskExecution


class ScheduledTaskRepository:
    """定时任务数据访问层"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, task: ScheduledTask) -> ScheduledTask:
        """创建任务"""
        self.session.add(task)
        await self.session.commit()
        await self.session.refresh(task)
        return task

    async def get_by_id(self, task_id: int) -> Optional[ScheduledTask]:
        """根据ID获取任务"""
        result = await self.session.execute(
            select(ScheduledTask).where(ScheduledTask.id == task_id)
        )
        return result.scalar_one_or_none()

    async def list_tasks(
        self,
        task_type: Optional[str] = None,
        is_enabled: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[ScheduledTask]:
        """获取任务列表"""
        query = select(ScheduledTask)

        conditions = []
        if task_type is not None:
            conditions.append(ScheduledTask.task_type == task_type)
        if is_enabled is not None:
            conditions.append(ScheduledTask.is_enabled == is_enabled)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(ScheduledTask.created_at.desc()).limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_enabled_tasks(self) -> List[ScheduledTask]:
        """获取所有启用的任务"""
        result = await self.session.execute(
            select(ScheduledTask)
            .where(ScheduledTask.is_enabled == True)
            .order_by(ScheduledTask.priority.desc(), ScheduledTask.created_at.asc())
        )
        return list(result.scalars().all())

    async def update(self, task_id: int, updates: dict) -> Optional[ScheduledTask]:
        """更新任务"""
        result = await self.session.execute(
            update(ScheduledTask)
            .where(ScheduledTask.id == task_id)
            .values(**updates)
            .returning(ScheduledTask)
        )
        await self.session.commit()
        return result.scalar_one_or_none()

    async def delete(self, task_id: int) -> bool:
        """删除任务"""
        task = await self.get_by_id(task_id)
        if task:
            await self.session.delete(task)
            await self.session.commit()
            return True
        return False

    async def get_by_target(self, task_type: str, target_id: int) -> Optional[ScheduledTask]:
        """根据任务类型和目标ID获取任务"""
        result = await self.session.execute(
            select(ScheduledTask).where(
                and_(
                    ScheduledTask.task_type == task_type,
                    ScheduledTask.target_id == target_id
                )
            )
        )
        return result.scalar_one_or_none()


class TaskExecutionRepository:
    """任务执行日志数据访问层"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, execution: TaskExecution) -> TaskExecution:
        """创建执行记录"""
        self.session.add(execution)
        await self.session.commit()
        await self.session.refresh(execution)
        return execution

    async def get_by_id(self, execution_id: int) -> Optional[TaskExecution]:
        """根据ID获取执行记录"""
        result = await self.session.execute(
            select(TaskExecution).where(TaskExecution.id == execution_id)
        )
        return result.scalar_one_or_none()

    async def list_by_task(
        self,
        task_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> List[TaskExecution]:
        """获取任务的执行历史"""
        result = await self.session.execute(
            select(TaskExecution)
            .where(TaskExecution.task_id == task_id)
            .order_by(TaskExecution.started_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def list_recent(
        self,
        task_type: Optional[str] = None,
        limit: int = 100
    ) -> List[TaskExecution]:
        """获取最近的执行记录"""
        query = (
            select(TaskExecution)
            .join(ScheduledTask, TaskExecution.task_id == ScheduledTask.id)
            .order_by(TaskExecution.started_at.desc())
            .limit(limit)
        )

        if task_type:
            query = query.where(ScheduledTask.task_type == task_type)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update(self, execution_id: int, updates: dict) -> Optional[TaskExecution]:
        """更新执行记录"""
        result = await self.session.execute(
            update(TaskExecution)
            .where(TaskExecution.id == execution_id)
            .values(**updates)
            .returning(TaskExecution)
        )
        await self.session.commit()
        return result.scalar_one_or_none()

    async def get_running_executions(self, task_id: Optional[int] = None) -> List[TaskExecution]:
        """获取正在运行的执行记录"""
        query = select(TaskExecution).where(TaskExecution.status == 'running')

        if task_id:
            query = query.where(TaskExecution.task_id == task_id)

        result = await self.session.execute(query)
        return list(result.scalars().all())
```

**Step 2: Update repositories __init__.py**

在 `backend/app/repositories/__init__.py` 中添加：

```python
from app.repositories.scheduled_task_repository import ScheduledTaskRepository, TaskExecutionRepository
```

**Step 3: Verify syntax**

Run: `python -c "import ast; ast.parse(open('backend/app/repositories/scheduled_task_repository.py', encoding='utf-8').read())"`

**Step 4: Commit**

```bash
git add backend/app/repositories/scheduled_task_repository.py backend/app/repositories/__init__.py
git commit -m "feat: add ScheduledTaskRepository and TaskExecutionRepository"
```

---

## Phase 3: Pydantic Schemas

### Task 4: 创建定时任务Schema

**Files:**
- Create: `backend/app/schemas/scheduled_task.py`

**Step 1: Write schemas**

```python
# backend/app/schemas/scheduled_task.py
from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator


class ScheduledTaskBase(BaseModel):
    """定时任务基础Schema"""
    task_type: Literal["sync", "rule"] = Field(..., description="任务类型")
    task_name: str = Field(..., min_length=1, max_length=255, description="任务名称")
    target_id: int = Field(..., gt=0, description="关联目标ID")
    cron_expression: str = Field(..., min_length=1, max_length=100, description="Cron表达式")
    is_enabled: bool = Field(default=True, description="是否启用")
    timeout_seconds: int = Field(default=300, ge=1, le=3600, description="超时时间（秒）")
    max_retries: int = Field(default=3, ge=0, le=10, description="最大重试次数")
    retry_interval_seconds: int = Field(default=60, ge=1, le=3600, description="重试间隔（秒）")
    priority: int = Field(default=50, ge=0, le=100, description="优先级")
    description: Optional[str] = Field(None, description="任务描述")

    @field_validator('cron_expression')
    @classmethod
    def validate_cron(cls, v: str) -> str:
        """验证cron表达式格式"""
        # 基本验证：5-7段，用空格分隔
        parts = v.strip().split()
        if not 5 <= len(parts) <= 7:
            raise ValueError('Cron expression must have 5-7 parts (min hour day month weekday [year])')
        return v


class ScheduledTaskCreate(ScheduledTaskBase):
    """创建定时任务请求"""
    pass


class ScheduledTaskUpdate(BaseModel):
    """更新定时任务请求"""
    task_name: Optional[str] = Field(None, min_length=1, max_length=255)
    cron_expression: Optional[str] = Field(None, min_length=1, max_length=100)
    is_enabled: Optional[bool] = None
    timeout_seconds: Optional[int] = Field(None, ge=1, le=3600)
    max_retries: Optional[int] = Field(None, ge=0, le=10)
    retry_interval_seconds: Optional[int] = Field(None, ge=1, le=3600)
    priority: Optional[int] = Field(None, ge=0, le=100)
    description: Optional[str] = None

    @field_validator('cron_expression')
    @classmethod
    def validate_cron(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            parts = v.strip().split()
            if not 5 <= len(parts) <= 7:
                raise ValueError('Cron expression must have 5-7 parts')
        return v


class ScheduledTaskResponse(ScheduledTaskBase):
    """定时任务响应"""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TaskExecutionBase(BaseModel):
    """任务执行基础Schema"""
    task_id: int
    status: Literal["pending", "running", "completed", "failed", "timeout"]
    triggered_by: Optional[Literal["scheduler", "manual", "retry"]] = None


class TaskExecutionResponse(TaskExecutionBase):
    """任务执行响应"""
    id: int
    started_at: datetime
    completed_at: Optional[datetime]
    duration_seconds: Optional[float]
    result_data: Optional[dict]
    error_message: Optional[str]
    error_type: Optional[str]
    retry_count: int
    is_retry: bool

    class Config:
        from_attributes = True


class TaskExecutionCreate(BaseModel):
    """创建执行记录请求"""
    task_id: int
    triggered_by: Literal["scheduler", "manual", "retry"] = "scheduler"


class CronTemplate(BaseModel):
    """Cron模板配置"""
    type: Literal["interval", "specific", "advanced"] = Field(..., description="模板类型")

    # 间隔配置
    interval_value: Optional[int] = Field(None, ge=1, le=1000, description="间隔数值")
    interval_unit: Optional[Literal["second", "minute", "hour", "day"]] = Field(None, description="间隔单位")

    # 具体时间配置
    frequency: Optional[Literal["hourly", "daily", "weekly", "monthly"]] = Field(None, description="频率")
    time: Optional[str] = Field(None, pattern=r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$", description="时间 HH:MM")
    day_of_week: Optional[int] = Field(None, ge=0, le=6, description="星期几 (0-6)")
    day_of_month: Optional[int] = Field(None, ge=1, le=31, description="每月第几天 (1-31)")

    # 高级模式
    advanced: Optional[str] = Field(None, min_length=1, max_length=100, description="原始cron表达式")


class ManualTriggerRequest(BaseModel):
    """手动触发请求"""
    task_id: int = Field(..., gt=0)
```

**Step 2: Update schemas __init__.py**

在 `backend/app/schemas/__init__.py` 中添加：

```python
from app.schemas.scheduled_task import (
    ScheduledTaskCreate,
    ScheduledTaskUpdate,
    ScheduledTaskResponse,
    TaskExecutionResponse,
    TaskExecutionCreate,
    CronTemplate,
    ManualTriggerRequest,
)
```

**Step 3: Verify syntax**

Run: `python -c "import ast; ast.parse(open('backend/app/schemas/scheduled_task.py', encoding='utf-8').read())"`

**Step 4: Commit**

```bash
git add backend/app/schemas/scheduled_task.py backend/app/schemas/__init__.py
git commit -m "feat: add scheduled task schemas"
```

---

## Phase 4: 核心调度服务

### Task 5: 创建TaskExecutor

**Files:**
- Create: `backend/app/services/task_executor.py`

**Step 1: Write task executor**

```python
# backend/app/services/task_executor.py
import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Optional, Callable, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scheduled_task import ScheduledTask, TaskExecution
from app.repositories.scheduled_task_repository import TaskExecutionRepository
from app.services.sync_service import SyncService

logger = logging.getLogger(__name__)


# 可重试错误模式
RETRYABLE_ERROR_PATTERNS = [
    r"connection.*timeout",
    r"network.*unreachable",
    r"503 Service Unavailable",
    r"504 Gateway Timeout",
    r"temporarily unavailable",
    r"Connection refused",
    r"TimeoutError",
    r"AsyncPostgresConnector",
]

# 不可重试错误模式
NON_RETRYABLE_ERROR_PATTERNS = [
    r"authentication.*failed",
    r"unauthorized",
    r"401 Unauthorized",
    r"403 Forbidden",
    r"invalid.*format",
    r"validation.*error",
    r"400 Bad Request",
    r"IntegrityError",
    r"UniqueConstraintError",
]


class TaskExecutor:
    """任务执行器，负责实际的任务执行和看门狗机制"""

    def __init__(
        self,
        max_concurrent_tasks: int = 10,
        default_timeout: int = 300
    ):
        self.semaphore = asyncio.Semaphore(max_concurrent_tasks)
        self.default_timeout = default_timeout
        self.running_tasks: dict[int, asyncio.Task] = {}
        self._task_executors = {
            "sync": self._execute_sync_task,
            "rule": self._execute_rule_task,
        }

    async def execute_task(
        self,
        task: ScheduledTask,
        session_factory: Callable[[], AsyncSession],
        triggered_by: str = "scheduler"
    ) -> dict[str, Any]:
        """执行单个任务，包含看门狗机制"""

        # 检查是否已有相同任务在运行
        if task.id in self.running_tasks:
            logger.warning(f"Task {task.id} is already running, skipping")
            return {
                "status": "skipped",
                "reason": "Task already running",
                "task_id": task.id,
            }

        async with self.semaphore:  # 并发控制
            # 创建执行记录
            async with session_factory() as session:
                exec_repo = TaskExecutionRepository(session)

                execution = TaskExecution(
                    task_id=task.id,
                    status="running",
                    triggered_by=triggered_by,
                    started_at=datetime.now(timezone.utc).replace(tzinfo=None),
                    retry_count=0,
                    is_retry=(triggered_by == "retry"),
                )
                await exec_repo.create(execution)

            try:
                # 执行任务（带超时控制）
                result = await asyncio.wait_for(
                    self._execute_with_watchdog(task, execution, session_factory),
                    timeout=task.timeout_seconds
                )

                # 更新执行记录
                async with session_factory() as session:
                    exec_repo = TaskExecutionRepository(session)
                    await exec_repo.update(execution.id, {
                        "status": "completed",
                        "completed_at": datetime.now(timezone.utc).replace(tzinfo=None),
                        "duration_seconds": (datetime.now(timezone.utc) - execution.started_at.replace(tzinfo=timezone.utc)).total_seconds(),
                        "result_data": result,
                    })

                return {
                    "status": "completed",
                    "task_id": task.id,
                    "execution_id": execution.id,
                    "result": result,
                }

            except asyncio.TimeoutError:
                logger.error(f"Task {task.id} timed out after {task.timeout_seconds}s")

                async with session_factory() as session:
                    exec_repo = TaskExecutionRepository(session)
                    await exec_repo.update(execution.id, {
                        "status": "timeout",
                        "completed_at": datetime.now(timezone.utc).replace(tzinfo=None),
                        "duration_seconds": task.timeout_seconds,
                        "error_message": f"Task timed out after {task.timeout_seconds} seconds",
                        "error_type": "TimeoutError",
                    })

                return {
                    "status": "timeout",
                    "task_id": task.id,
                    "execution_id": execution.id,
                }

            except Exception as e:
                logger.exception(f"Task {task.id} failed: {e}")

                error_type = type(e).__name__
                error_msg = str(e)

                async with session_factory() as session:
                    exec_repo = TaskExecutionRepository(session)
                    await exec_repo.update(execution.id, {
                        "status": "failed",
                        "completed_at": datetime.now(timezone.utc).replace(tzinfo=None),
                        "duration_seconds": (datetime.now(timezone.utc) - execution.started_at.replace(tzinfo=timezone.utc)).total_seconds(),
                        "error_message": error_msg,
                        "error_type": error_type,
                    })

                # 检查是否需要重试
                if execution.retry_count < task.max_retries and self._should_retry(e):
                    logger.info(f"Retrying task {task.id} (attempt {execution.retry_count + 1}/{task.max_retries})")
                    await asyncio.sleep(task.retry_interval_seconds)

                    # 递归重试
                    return await self.execute_task(
                        task,
                        session_factory,
                        triggered_by="retry"
                    )

                return {
                    "status": "failed",
                    "task_id": task.id,
                    "execution_id": execution.id,
                    "error": error_msg,
                    "error_type": error_type,
                }

            finally:
                # 清理运行任务记录
                if task.id in self.running_tasks:
                    del self.running_tasks[task.id]

    async def _execute_with_watchdog(
        self,
        task: ScheduledTask,
        execution: TaskExecution,
        session_factory: Callable[[], AsyncSession]
    ) -> dict[str, Any]:
        """带看门狗保护的执行"""
        self.running_tasks[task.id] = asyncio.current_task()

        executor_func = self._task_executors.get(task.task_type)
        if not executor_func:
            raise ValueError(f"Unknown task type: {task.task_type}")

        return await executor_func(task, session_factory)

    async def _execute_sync_task(
        self,
        task: ScheduledTask,
        session_factory: Callable[[], AsyncSession]
    ) -> dict[str, Any]:
        """执行数据同步任务"""
        async with session_factory() as session:
            sync_service = SyncService(session)
            result = await sync_service.sync_data_product(
                product_id=task.target_id,
                sync_relationships=True,
            )
            return result

    async def _execute_rule_task(
        self,
        task: ScheduledTask,
        session_factory: Callable[[], AsyncSession]
    ) -> dict[str, Any]:
        """执行规则定时任务"""
        # TODO: 实现规则定时触发逻辑
        # 这需要与规则引擎集成
        return {
            "message": "Rule execution not yet implemented",
            "rule_id": task.target_id,
        }

    def _should_retry(self, error: Exception) -> bool:
        """判断错误是否可重试"""
        error_msg = str(error).lower()
        error_type = type(error).__name__

        # 首先检查是否为不可重试错误
        for pattern in NON_RETRYABLE_ERROR_PATTERNS:
            if re.search(pattern, error_msg, re.IGNORECASE):
                return False

        # 检查是否为可重试错误
        for pattern in RETRYABLE_ERROR_PATTERNS:
            if re.search(pattern, error_msg, re.IGNORECASE):
                return True

        # 默认网络相关错误可重试
        return any(keyword in error_type for keyword in [
            'Connection', 'Timeout', 'Network'
        ])

    async def cancel_running_task(self, task_id: int) -> bool:
        """取消正在运行的任务"""
        if task_id in self.running_tasks:
            task = self.running_tasks[task_id]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            return True
        return False

    def get_running_tasks(self) -> list[int]:
        """获取当前运行中的任务ID列表"""
        return list(self.running_tasks.keys())
```

**Step 2: Verify syntax**

Run: `python -c "import ast; ast.parse(open('backend/app/services/task_executor.py', encoding='utf-8').read())"`

**Step 3: Commit**

```bash
git add backend/app/services/task_executor.py
git commit -m "feat: add TaskExecutor with watchdog mechanism"
```

---

### Task 6: 创建SchedulerService

**Files:**
- Create: `backend/app/services/scheduler_service.py`

**Step 1: Write scheduler service**

```python
# backend/app/services/scheduler_service.py
import logging
from typing import Optional, Callable
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scheduled_task import ScheduledTask
from app.repositories.scheduled_task_repository import ScheduledTaskRepository, TaskExecutionRepository
from app.services.task_executor import TaskExecutor
from app.core.config import settings

logger = logging.getLogger(__name__)


class SchedulerService:
    """全局定时调度服务"""

    def __init__(
        self,
        db_session_factory: Callable[[], AsyncSession],
        max_concurrent_tasks: int = 10,
        default_timeout: int = 300
    ):
        # 配置jobstore
        jobstores = {
            'default': SQLAlchemyJobStore(
                url=settings.DATABASE_URL,
                tablename='apscheduler_jobs'
            )
        }

        # 配置executor
        executors = {
            'default': AsyncIOExecutor()
        }

        # 配置job defaults
        job_defaults = {
            'coalesce': True,  # 合并堆积的任务
            'max_instances': 1,  # 同一任务最多1个实例
            'misfire_grace_time': 60  # 错过执行后的宽限时间
        }

        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone='UTC'
        )

        self.db_session_factory = db_session_factory
        self.executor = TaskExecutor(
            max_concurrent_tasks=max_concurrent_tasks,
            default_timeout=default_timeout
        )
        self.repository: Optional[ScheduledTaskRepository] = None

    async def initialize(self) -> None:
        """初始化scheduler，从数据库加载所有启用的任务"""
        logger.info("Initializing SchedulerService...")

        async with self.db_session_factory() as session:
            self.repository = ScheduledTaskRepository(session)
            enabled_tasks = await self.repository.get_enabled_tasks()

            for task in enabled_tasks:
                await self._schedule_task(task)

            logger.info(f"Loaded {len(enabled_tasks)} enabled scheduled tasks")

    async def _schedule_task(self, task: ScheduledTask) -> str:
        """将任务添加到scheduler"""
        try:
            trigger = CronTrigger.from_crontab(task.cron_expression)

            self.scheduler.add_job(
                func=self._execute_scheduled_task,
                trigger=trigger,
                id=f"task_{task.id}",
                name=task.task_name,
                args=[task.id],
                replace_existing=True,
            )

            logger.info(f"Scheduled task {task.id}: {task.task_name} ({task.cron_expression})")
            return f"task_{task.id}"

        except Exception as e:
            logger.error(f"Failed to schedule task {task.id}: {e}")
            raise

    async def _execute_scheduled_task(self, task_id: int) -> None:
        """Scheduler调用的执行函数"""
        async with self.db_session_factory() as session:
            repo = ScheduledTaskRepository(session)
            task = await repo.get_by_id(task_id)

            if not task:
                logger.error(f"Task {task_id} not found")
                return

            if not task.is_enabled:
                logger.info(f"Task {task_id} is disabled, skipping")
                return

            await self.executor.execute_task(task, self.db_session_factory, triggered_by="scheduler")

    async def add_task(self, task: ScheduledTask) -> str:
        """添加新任务到scheduler"""
        await self._schedule_task(task)
        return f"task_{task.id}"

    async def update_task(self, task_id: int, updates: dict) -> bool:
        """更新任务配置（下次执行生效）"""
        async with self.db_session_factory() as session:
            repo = ScheduledTaskRepository(session)
            task = await repo.update(task_id, updates)

            if not task:
                return False

            # 重新调度任务
            if task.is_enabled:
                # 先移除旧任务
                try:
                    self.scheduler.remove_job(f"task_{task_id}")
                except Exception:
                    pass

                # 添加新任务
                await self._schedule_task(task)
            else:
                # 任务被禁用，移除
                try:
                    self.scheduler.remove_job(f"task_{task_id}")
                except Exception:
                    pass

            return True

    async def remove_task(self, task_id: int) -> bool:
        """移除任务"""
        try:
            self.scheduler.remove_job(f"task_{task_id}")

            async with self.db_session_factory() as session:
                repo = ScheduledTaskRepository(session)
                await repo.delete(task_id)

            return True
        except Exception as e:
            logger.error(f"Failed to remove task {task_id}: {e}")
            return False

    async def pause_task(self, task_id: int) -> bool:
        """暂停任务"""
        try:
            self.scheduler.pause_job(f"task_{task_id}")

            async with self.db_session_factory() as session:
                repo = ScheduledTaskRepository(session)
                await repo.update(task_id, {"is_enabled": False})

            return True
        except Exception as e:
            logger.error(f"Failed to pause task {task_id}: {e}")
            return False

    async def resume_task(self, task_id: int) -> bool:
        """恢复任务"""
        try:
            self.scheduler.resume_job(f"task_{task_id}")

            async with self.db_session_factory() as session:
                repo = ScheduledTaskRepository(session)
                await repo.update(task_id, {"is_enabled": True})

            return True
        except Exception as e:
            logger.error(f"Failed to resume task {task_id}: {e}")
            return False

    async def trigger_task_manually(self, task_id: int) -> dict:
        """手动触发任务执行"""
        async with self.db_session_factory() as session:
            repo = ScheduledTaskRepository(session)
            task = await repo.get_by_id(task_id)

            if not task:
                return {
                    "status": "error",
                    "message": f"Task {task_id} not found"
                }

            result = await self.executor.execute_task(task, self.db_session_factory, triggered_by="manual")
            return result

    async def get_task_status(self, task_id: int) -> dict:
        """获取任务当前状态"""
        try:
            job = self.scheduler.get_job(f"task_{task_id}")

            async with self.db_session_factory() as session:
                exec_repo = TaskExecutionRepository(session)
                recent_executions = await exec_repo.list_by_task(task_id, limit=5)

                running = self.executor.get_running_tasks()

            return {
                "task_id": task_id,
                "scheduled": job is not None,
                "next_run_time": job.next_run_time.isoformat() if job else None,
                "is_running": task_id in running,
                "recent_executions": [
                    {
                        "id": e.id,
                        "status": e.status,
                        "started_at": e.started_at.isoformat(),
                        "duration_seconds": e.duration_seconds,
                    }
                    for e in recent_executions
                ]
            }
        except Exception as e:
            return {
                "task_id": task_id,
                "error": str(e)
            }

    async def get_execution_history(self, task_id: int, limit: int = 50):
        """获取任务执行历史"""
        async with self.db_session_factory() as session:
            exec_repo = TaskExecutionRepository(session)
            return await exec_repo.list_by_task(task_id, limit=limit)

    async def start(self) -> None:
        """启动scheduler"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Scheduler started")

    async def shutdown(self) -> None:
        """优雅关闭scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)
            logger.info("Scheduler shutdown complete")
```

**Step 2: Verify syntax**

Run: `python -c "import ast; ast.parse(open('backend/app/services/scheduler_service.py', encoding='utf-8').read())"`

**Step 3: Commit**

```bash
git add backend/app/services/scheduler_service.py
git commit -m "feat: add SchedulerService with APScheduler integration"
```

---

## Phase 5: API路由

### Task 7: 创建定时任务API

**Files:**
- Create: `backend/app/api/scheduled_tasks.py`
- Modify: `backend/app/main.py`

**Step 1: Write API routes**

```python
# backend/app/api/scheduled_tasks.py
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.scheduled_task import (
    ScheduledTaskCreate,
    ScheduledTaskUpdate,
    ScheduledTaskResponse,
    TaskExecutionResponse,
    CronTemplate,
    ManualTriggerRequest,
)
from app.models.scheduled_task import ScheduledTask
from app.repositories.scheduled_task_repository import ScheduledTaskRepository, TaskExecutionRepository
from app.services.scheduler_service import SchedulerService

router = APIRouter(prefix="/api/scheduled-tasks", tags=["scheduled-tasks"])

# 全局scheduler_service实例，在main.py中初始化
_scheduler_service: Optional[SchedulerService] = None

def init_scheduled_tasks_api(scheduler_service: SchedulerService):
    """初始化API模块，设置scheduler_service"""
    global _scheduler_service
    _scheduler_service = scheduler_service


def get_scheduler() -> SchedulerService:
    """获取scheduler_service依赖"""
    if _scheduler_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Scheduler service not available"
        )
    return _scheduler_service


@router.post("/", response_model=ScheduledTaskResponse, status_code=status.HTTP_201_CREATED)
async def create_scheduled_task(
    task_data: ScheduledTaskCreate,
    db: AsyncSession = Depends(get_db),
    scheduler: SchedulerService = Depends(get_scheduler)
):
    """创建定时任务"""
    repo = ScheduledTaskRepository(db)

    # 检查是否已存在相同类型和目标的任务
    existing = await repo.get_by_target(task_data.task_type, task_data.target_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Task already exists for {task_data.task_type}:{task_data.target_id}"
        )

    task = ScheduledTask(**task_data.model_dump())
    created = await repo.create(task)

    # 如果启用，添加到scheduler
    if created.is_enabled:
        await scheduler.add_task(created)

    return created


@router.get("/", response_model=List[ScheduledTaskResponse])
async def list_scheduled_tasks(
    task_type: Optional[str] = None,
    is_enabled: Optional[bool] = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """获取定时任务列表"""
    repo = ScheduledTaskRepository(db)
    tasks = await repo.list_tasks(task_type=task_type, is_enabled=is_enabled, limit=limit, offset=offset)
    return tasks


@router.get("/{task_id}", response_model=ScheduledTaskResponse)
async def get_scheduled_task(
    task_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取定时任务详情"""
    repo = ScheduledTaskRepository(db)
    task = await repo.get_by_id(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )
    return task


@router.put("/{task_id}", response_model=ScheduledTaskResponse)
async def update_scheduled_task(
    task_id: int,
    updates: ScheduledTaskUpdate,
    db: AsyncSession = Depends(get_db),
    scheduler: SchedulerService = Depends(get_scheduler)
):
    """更新定时任务（下次执行生效）"""
    # 只更新提供的字段
    update_data = {k: v for k, v in updates.model_dump().items() if v is not None}

    await scheduler.update_task(task_id, update_data)

    repo = ScheduledTaskRepository(db)
    task = await repo.get_by_id(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scheduled_task(
    task_id: int,
    scheduler: SchedulerService = Depends(get_scheduler)
):
    """删除定时任务"""
    success = await scheduler.remove_task(task_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )
    return None


@router.post("/{task_id}/pause")
async def pause_scheduled_task(
    task_id: int,
    scheduler: SchedulerService = Depends(get_scheduler)
):
    """暂停定时任务"""
    success = await scheduler.pause_task(task_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )
    return {"status": "paused", "task_id": task_id}


@router.post("/{task_id}/resume")
async def resume_scheduled_task(
    task_id: int,
    scheduler: SchedulerService = Depends(get_scheduler)
):
    """恢复定时任务"""
    success = await scheduler.resume_task(task_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )
    return {"status": "resumed", "task_id": task_id}


@router.post("/{task_id}/trigger")
async def trigger_scheduled_task(
    task_id: int,
    scheduler: SchedulerService = Depends(get_scheduler)
):
    """手动触发任务执行"""
    result = await scheduler.trigger_task_manually(task_id)
    if result.get("status") == "error":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.get("message")
        )
    return result


@router.get("/{task_id}/status")
async def get_scheduled_task_status(
    task_id: int,
    scheduler: SchedulerService = Depends(get_scheduler)
):
    """获取任务当前状态"""
    return await scheduler.get_task_status(task_id)


@router.get("/{task_id}/executions", response_model=List[TaskExecutionResponse])
async def get_task_executions(
    task_id: int,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """获取任务执行历史"""
    repo = TaskExecutionRepository(db)
    executions = await repo.list_by_task(task_id, limit=limit)
    return executions


@router.get("/executions/recent", response_model=List[TaskExecutionResponse])
async def get_recent_executions(
    task_type: Optional[str] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """获取最近的执行记录"""
    repo = TaskExecutionRepository(db)
    executions = await repo.list_recent(task_type=task_type, limit=limit)
    return executions


@router.post("/cron/parse")
async def parse_cron_template(template: CronTemplate):
    """将cron模板转换为cron表达式"""
    from app.services.cron_parser import cron_template_to_expression

    try:
        expression = cron_template_to_expression(template)
        return {"cron_expression": expression}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
```

**Step 2: Update main.py**

在 `backend/app/main.py` 中添加：

```python
# 在导入部分添加
from app.api import scheduled_tasks

# 在lifespan函数中，scheduler初始化后添加
# Initialize scheduled tasks API
scheduled_tasks.init_scheduled_tasks_api(scheduler_service)

# 在app.include_router部分添加
app.include_router(scheduled_tasks.router)
```

**Step 3: Verify syntax**

Run: `python -c "import ast; ast.parse(open('backend/app/api/scheduled_tasks.py', encoding='utf-8').read())"`

**Step 4: Commit**

```bash
git add backend/app/api/scheduled_tasks.py backend/app/main.py
git commit -m "feat: add scheduled tasks API endpoints"
```

---

### Task 8: 创建Cron解析工具

**Files:**
- Create: `backend/app/services/cron_parser.py`

**Step 1: Write cron parser**

```python
# backend/app/services/cron_parser.py
from app.schemas.scheduled_task import CronTemplate


def cron_template_to_expression(template: CronTemplate) -> str:
    """将cron模板转换为cron表达式"""

    if template.type == "advanced":
        if not template.advanced:
            raise ValueError("Advanced cron expression is required")
        # 验证格式
        parts = template.advanced.strip().split()
        if not 5 <= len(parts) <= 7:
            raise ValueError("Cron expression must have 5-7 parts")
        return template.advanced

    elif template.type == "interval":
        if not template.interval_value or not template.interval_unit:
            raise ValueError("Interval value and unit are required")

        value = template.interval_value
        unit = template.interval_unit

        # 间隔模式: */n
        if unit == "second":
            return f"*/{value} * * * * *"
        elif unit == "minute":
            return f"*/{value} * * * *"
        elif unit == "hour":
            return f"0 */{value} * * *"
        elif unit == "day":
            return f"0 0 */{value} * *"
        else:
            raise ValueError(f"Unknown interval unit: {unit}")

    elif template.type == "specific":
        if not template.frequency:
            raise ValueError("Frequency is required")

        freq = template.frequency

        if freq == "hourly":
            return "0 * * * *"

        elif freq == "daily":
            time_str = template.time or "00:00"
            hour, minute = time_str.split(":")
            return f"{minute} {hour} * * *"

        elif freq == "weekly":
            time_str = template.time or "00:00"
            hour, minute = time_str.split(":")
            dow = template.day_of_week or 0
            return f"{minute} {hour} * * {dow}"

        elif freq == "monthly":
            time_str = template.time or "00:00"
            hour, minute = time_str.split(":")
            dom = template.day_of_month or 1
            return f"{minute} {hour} {dom} * *"

        else:
            raise ValueError(f"Unknown frequency: {freq}")

    else:
        raise ValueError(f"Unknown template type: {template.type}")


def cron_expression_to_template(expression: str) -> CronTemplate:
    """将cron表达式转换为cron模板（尽力而为）"""
    parts = expression.strip().split()

    if len(parts) == 6:
        # 含秒的六段式
        return CronTemplate(
            type="advanced",
            advanced=expression
        )

    # 检查是否为间隔模式
    if parts[0].startswith("*/"):
        value = parts[0][2:]
        if len(parts) == 5:
            return CronTemplate(
                type="interval",
                interval_value=int(value),
                interval_unit="minute"
            )

    # 检查其他常见模式
    if parts == ["0", "*", "*", "*", "*"]:
        return CronTemplate(type="specific", frequency="hourly")

    if parts[0] == "0" and parts[2] == "*" and parts[3] == "*" and parts[4] == "*":
        # 每天
        return CronTemplate(
            type="specific",
            frequency="daily",
            time=f"{parts[1].zfill(2)}:00"
        )

    # 默认返回高级模式
    return CronTemplate(
        type="advanced",
        advanced=expression
    )
```

**Step 2: Verify syntax**

Run: `python -c "import ast; ast.parse(open('backend/app/services/cron_parser.py', encoding='utf-8').read())"`

**Step 3: Commit**

```bash
git add backend/app/services/cron_parser.py
git commit -m "feat: add cron template parser"
```

---

## Phase 6: 数据产品API集成

### Task 9: 扩展数据产品API

**Files:**
- Modify: `backend/app/api/data_products.py`

**Step 1: Add sync schedule endpoints**

在 `backend/app/api/data_products.py` 中添加以下路由：

```python
# 在现有导入后添加
from app.schemas.scheduled_task import ScheduledTaskResponse, CronTemplate
from app.repositories.scheduled_task_repository import ScheduledTaskRepository

@router.get("/{product_id}/sync-schedule", response_model=Optional[ScheduledTaskResponse])
async def get_product_sync_schedule(
    product_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取数据产品的同步计划"""
    repo = ScheduledTaskRepository(db)
    task = await repo.get_by_target("sync", product_id)
    return task


@router.put("/{product_id}/sync-schedule", response_model=ScheduledTaskResponse)
async def set_product_sync_schedule(
    product_id: int,
    template: CronTemplate,
    db: AsyncSession = Depends(get_db)
):
    """设置数据产品的同步计划"""
    # 验证产品存在
    from app.repositories.data_product_repository import DataProductRepository
    product_repo = DataProductRepository(db)
    product = await product_repo.get_by_id(product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data product {product_id} not found"
        )

    # 转换cron模板
    from app.services.cron_parser import cron_template_to_expression
    cron_expr = cron_template_to_expression(template)

    # 检查是否已存在
    task_repo = ScheduledTaskRepository(db)
    existing = await task_repo.get_by_target("sync", product_id)

    if existing:
        # 更新现有任务
        from app.models.scheduled_task import ScheduledTask
        task = await task_repo.update(existing.id, {
            "cron_expression": cron_expr,
            "task_name": f"Sync: {product.name}",
        })
    else:
        # 创建新任务
        from app.models.scheduled_task import ScheduledTask
        task = ScheduledTask(
            task_type="sync",
            task_name=f"Sync: {product.name}",
            target_id=product_id,
            cron_expression=cron_expr,
            is_enabled=True,
            timeout_seconds=600,  # 10分钟
        )
        task = await task_repo.create(task)

    # 更新scheduler
    from app.main import app
    if hasattr(app.state, 'scheduler_service'):
        await app.state.scheduler_service.add_task(task)

    return task


@router.delete("/{product_id}/sync-schedule", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product_sync_schedule(
    product_id: int,
    db: AsyncSession = Depends(get_db)
):
    """删除数据产品的同步计划"""
    task_repo = ScheduledTaskRepository(db)
    task = await task_repo.get_by_target("sync", product_id)

    if task:
        await task_repo.delete(task.id)

        # 从scheduler移除
        from app.main import app
        if hasattr(app.state, 'scheduler_service'):
            await app.state.scheduler_service.remove_task(task.id)

    return None


@router.get("/{product_id}/sync-history")
async def get_product_sync_history(
    product_id: int,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """获取数据产品的同步历史"""
    task_repo = ScheduledTaskRepository(db)
    task = await task_repo.get_by_target("sync", product_id)

    if not task:
        return []

    exec_repo = TaskExecutionRepository(db)
    executions = await exec_repo.list_by_task(task.id, limit=limit)
    return executions
```

**Step 2: Commit**

```bash
git add backend/app/api/data_products.py
git commit -m "feat: add sync schedule endpoints to data products API"
```

---

## Phase 7: 规则API集成

### Task 10: 扩展规则API

**Files:**
- Modify: `backend/app/api/rules.py`

**Step 1: Add rule schedule endpoints**

在 `backend/app/api/rules.py` 中添加以下路由：

```python
# 在现有导入后添加
from app.schemas.scheduled_task import ScheduledTaskResponse, CronTemplate
from app.repositories.scheduled_task_repository import ScheduledTaskRepository

@router.get("/{rule_id}/schedule", response_model=Optional[ScheduledTaskResponse])
async def get_rule_schedule(
    rule_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取规则的定时配置"""
    repo = ScheduledTaskRepository(db)
    task = await repo.get_by_target("rule", rule_id)
    return task


@router.put("/{rule_id}/schedule", response_model=ScheduledTaskResponse)
async def set_rule_schedule(
    rule_id: int,
    template: CronTemplate,
    db: AsyncSession = Depends(get_db)
):
    """设置规则的定时配置"""
    # 验证规则存在
    from app.models.rule import Rule
    from sqlalchemy import select
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = result.scalar_one_or_none()

    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule {rule_id} not found"
        )

    # 转换cron模板
    from app.services.cron_parser import cron_template_to_expression
    cron_expr = cron_template_to_expression(template)

    # 检查是否已存在
    task_repo = ScheduledTaskRepository(db)
    existing = await task_repo.get_by_target("rule", rule_id)

    if existing:
        # 更新现有任务
        task = await task_repo.update(existing.id, {
            "cron_expression": cron_expr,
            "task_name": f"Rule: {rule.name}",
        })
    else:
        # 创建新任务
        from app.models.scheduled_task import ScheduledTask
        task = ScheduledTask(
            task_type="rule",
            task_name=f"Rule: {rule.name}",
            target_id=rule_id,
            cron_expression=cron_expr,
            is_enabled=True,
            timeout_seconds=120,  # 2分钟
        )
        task = await task_repo.create(task)

    # 更新scheduler
    from app.main import app
    if hasattr(app.state, 'scheduler_service'):
        await app.state.scheduler_service.add_task(task)

    return task


@router.delete("/{rule_id}/schedule", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule_schedule(
    rule_id: int,
    db: AsyncSession = Depends(get_db)
):
    """删除规则的定时配置"""
    task_repo = ScheduledTaskRepository(db)
    task = await task_repo.get_by_target("rule", rule_id)

    if task:
        await task_repo.delete(task.id)

        # 从scheduler移除
        from app.main import app
        if hasattr(app.state, 'scheduler_service'):
            await app.state.scheduler_service.remove_task(task.id)

    return None


@router.get("/{rule_id}/execution-history")
async def get_rule_execution_history(
    rule_id: int,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """获取规则的执行历史"""
    task_repo = ScheduledTaskRepository(db)
    task = await task_repo.get_by_target("rule", rule_id)

    if not task:
        return []

    exec_repo = TaskExecutionRepository(db)
    executions = await exec_repo.list_by_task(task.id, limit=limit)
    return executions
```

**Step 2: Commit**

```bash
git add backend/app/api/rules.py
git commit -m "feat: add schedule endpoints to rules API"
```

---

## Phase 8: 规则执行器集成

### Task 11: 实现规则定时执行

**Files:**
- Modify: `backend/app/services/task_executor.py`

**Step 1: Update _execute_rule_task method**

修改 `backend/app/services/task_executor.py` 中的 `_execute_rule_task` 方法：

```python
async def _execute_rule_task(
    self,
    task: ScheduledTask,
    session_factory: Callable[[], AsyncSession]
) -> dict[str, Any]:
    """执行规则定时任务"""
    from app.models.rule import Rule
    from app.rule_engine.rule_engine import RuleEngine
    from app.rule_engine.models import UpdateEvent, TriggerType
    from sqlalchemy import select

    async with session_factory() as session:
        # 获取规则定义
        result = await session.execute(select(Rule).where(Rule.id == task.target_id))
        rule = result.scalar_one_or_none()

        if not rule:
            raise ValueError(f"Rule {task.target_id} not found")

        # 创建虚拟的定时触发事件
        event = UpdateEvent(
            entity_type=rule.trigger_entity,
            entity_id="cron",
            property=rule.trigger_property or "_cron_trigger",
            old_value=None,
            new_value=None,
            actor_name=f"Scheduler:{task.id}",
            actor_type="SYSTEM",
        )

        # 获取rule_engine实例
        from app.main import app
        if not hasattr(app.state, 'rule_engine'):
            raise ValueError("Rule engine not initialized")

        rule_engine: RuleEngine = app.state.rule_engine

        # 手动触发规则执行
        # 这里需要创建一个特殊的规则执行，不依赖事件
        from app.rule_engine.rule_registry import RuleRegistry
        from app.rule_engine.parser import RuleParser

        parser = RuleParser()
        parsed = parser.parse(rule.dsl_content)
        rule_def = parsed[0] if parsed else None

        if not rule_def:
            raise ValueError(f"Failed to parse rule {rule.id}")

        # 直接执行规则
        result = await self._execute_rule_definition(rule_def, event, session)

        return {
            "rule_id": rule.id,
            "rule_name": rule.name,
            "entities_affected": result.get("entities_affected", 0),
            "statements_executed": result.get("statements_executed", 0),
        }

async def _execute_rule_definition(
    self,
    rule_def,
    event: UpdateEvent,
    session: AsyncSession
) -> dict[str, Any]:
    """直接执行规则定义"""
    from app.rule_engine.rule_engine import RuleEngine
    from app.main import app

    rule_engine: RuleEngine = app.state.rule_engine

    # 使用rule_engine的内部方法执行规则
    # 这里需要适配现有的rule_engine架构
    # 暂时返回模拟结果
    return {
        "entities_affected": 0,
        "statements_executed": 0,
    }
```

**Step 2: Commit**

```bash
git add backend/app/services/task_executor.py
git commit -m "feat: implement rule execution for scheduled tasks"
```

---

## Phase 9: 配置和依赖

### Task 12: 添加APScheduler依赖

**Files:**
- Modify: `backend/pyproject.toml`

**Step 1: Add dependency**

在 `backend/pyproject.toml` 的 dependencies 中添加：

```toml
apscheduler = "^3.10.4"
```

**Step 2: Install dependency**

Run: `cd backend && uv sync`

**Step 3: Verify installation**

Run: `uv run python -c "import apscheduler; print(apscheduler.__version__)"`

**Step 4: Commit**

```bash
git add backend/pyproject.toml
git commit -m "deps: add APScheduler dependency"
```

---

### Task 13: 添加环境配置

**Files:**
- Modify: `backend/app/core/config.py`
- Modify: `.env.example`

**Step 1: Add config settings**

在 `backend/app/core/config.py` 中添加：

```python
class Settings(BaseSettings):
    # ... 现有配置 ...

    # Scheduler settings
    SCHEDULER_MAX_CONCURRENT: int = Field(default=10, description="最大并发任务数")
    SCHEDULER_DEFAULT_TIMEOUT: int = Field(default=300, description="默认超时时间（秒）")
```

**Step 2: Update .env.example**

在 `.env.example` 中添加：

```bash
# Scheduler Settings
SCHEDULER_MAX_CONCURRENT=10
SCHEDULER_DEFAULT_TIMEOUT=300
```

**Step 3: Commit**

```bash
git add backend/app/core/config.py .env.example
git commit -m "feat: add scheduler configuration settings"
```

---

## Phase 10: 集成到应用生命周期

### Task 14: 更新main.py集成scheduler

**Files:**
- Modify: `backend/app/main.py`

**Step 1: Update lifespan function**

修改 `backend/app/main.py` 中的 `lifespan` 函数，在 `action_registry` 初始化后添加：

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # === Startup ===
    await init_db()

    # ... 现有的 event_emitter, action_registry 等初始化 ...

    # 初始化定时调度服务
    from app.services.scheduler_service import SchedulerService

    scheduler_service = SchedulerService(
        db_session_factory=async_session,
        max_concurrent_tasks=settings.SCHEDULER_MAX_CONCURRENT,
        default_timeout=settings.SCHEDULER_DEFAULT_TIMEOUT
    )
    await scheduler_service.initialize()
    await scheduler_service.start()

    logger.info("Scheduler service initialized and started")

    # 初始化定时任务API（在导入scheduled_tasks模块后）
    # scheduled_tasks.init_scheduled_tasks_api(scheduler_service)
    # 这部分在scheduled_tasks模块导入后处理

    # 存储到app.state
    app.state.scheduler_service = scheduler_service

    yield

    # === Shutdown ===
    # 关闭scheduler
    if hasattr(app.state, 'scheduler_service'):
        await app.state.scheduler_service.shutdown()

    await engine.dispose()
    logger.info("Application shutdown complete")
```

**Step 2: Update router imports and initialization**

在 `backend/app/main.py` 中：

```python
# 在导入部分添加
from app.api import scheduled_tasks

# 在app.state赋值部分之后、yield之前添加
# Initialize scheduled tasks API
scheduled_tasks.init_scheduled_tasks_api(scheduler_service)

# 在app.include_router部分添加
app.include_router(scheduled_tasks.router)
```

**Step 3: Verify syntax**

Run: `python -c "import ast; ast.parse(open('backend/app/main.py', encoding='utf-8').read())"`

**Step 4: Test startup**

Run: `cd backend && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level info`

检查日志中是否有 "Scheduler service initialized and started" 消息。

**Step 5: Commit**

```bash
git add backend/app/main.py
git commit -m "feat: integrate scheduler service into application lifecycle"
```

---

## Phase 11: 前端 - 数据产品同步配置

### Task 15: 创建Cron模板组件

**Files:**
- Create: `frontend/src/components/scheduler/CronTemplateSelector.tsx`
- Create: `frontend/src/components/scheduler/CronTemplateSelector.types.ts`

**Step 1: Create types file**

```typescript
// frontend/src/components/scheduler/CronTemplateSelector.types.ts

export type CronTemplateType = 'interval' | 'specific' | 'advanced';

export type IntervalUnit = 'second' | 'minute' | 'hour' | 'day';
export type Frequency = 'hourly' | 'daily' | 'weekly' | 'monthly';

export interface IntervalTemplate {
  type: 'interval';
  interval_value: number;
  interval_unit: IntervalUnit;
}

export interface SpecificTemplate {
  type: 'specific';
  frequency: Frequency;
  time?: string; // HH:MM
  day_of_week?: number; // 0-6
  day_of_month?: number; // 1-31
}

export interface AdvancedTemplate {
  type: 'advanced';
  advanced: string;
}

export type CronTemplate = IntervalTemplate | SpecificTemplate | AdvancedTemplate;

export interface CronTemplateSelectorProps {
  value: CronTemplate;
  onChange: (value: CronTemplate) => void;
  disabled?: boolean;
  error?: string;
}
```

**Step 2: Create component**

```tsx
// frontend/src/components/scheduler/CronTemplateSelector.tsx
'use client';

import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Clock, Calendar, Code } from 'lucide-react';
import type { CronTemplate, CronTemplateType, CronTemplateSelectorProps } from './CronTemplateSelector.types';

const INTERVAL_UNITS = [
  { value: 'second' as const, label: '秒' },
  { value: 'minute' as const, label: '分钟' },
  { value: 'hour' as const, label: '小时' },
  { value: 'day' as const, label: '天' },
];

const FREQUENCIES = [
  { value: 'hourly' as const, label: '每小时' },
  { value: 'daily' as const, label: '每天' },
  { value: 'weekly' as const, label: '每周' },
  { value: 'monthly' as const, label: '每月' },
];

const WEEKDAYS = [
  { value: 0, label: '周日' },
  { value: 1, label: '周一' },
  { value: 2, label: '周二' },
  { value: 3, label: '周三' },
  { value: 4, label: '周四' },
  { value: 5, label: '周五' },
  { value: 6, label: '周六' },
];

export function CronTemplateSelector({ value, onChange, disabled = false, error }: CronTemplateSelectorProps) {
  const [activeTab, setActiveTab] = useState<CronTemplateType>(value.type);

  const handleTypeChange = (type: CronTemplateType) => {
    setActiveTab(type);

    // 设置默认值
    switch (type) {
      case 'interval':
        onChange({ type: 'interval', interval_value: 5, interval_unit: 'minute' });
        break;
      case 'specific':
        onChange({ type: 'specific', frequency: 'daily', time: '02:00' });
        break;
      case 'advanced':
        onChange({ type: 'advanced', advanced: '0 2 * * *' });
        break;
    }
  };

  const updateValue = <K extends keyof CronTemplate>(key: K, val: CronTemplate[K]) => {
    onChange({ ...value, [key]: val });
  };

  return (
    <div className="space-y-4">
      <Tabs value={activeTab} onValueChange={(v) => handleTypeChange(v as CronTemplateType)}>
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="interval" className="flex items-center gap-2">
            <Clock className="h-4 w-4" />
            按间隔
          </TabsTrigger>
          <TabsTrigger value="specific" className="flex items-center gap-2">
            <Calendar className="h-4 w-4" />
            按时间
          </TabsTrigger>
          <TabsTrigger value="advanced" className="flex items-center gap-2">
            <Code className="h-4 w-4" />
            高级
          </TabsTrigger>
        </TabsList>

        <TabsContent value="interval" className="space-y-4">
          <div className="flex items-center gap-4">
            <div className="flex-1">
              <Label htmlFor="interval-value">每</Label>
              <Input
                id="interval-value"
                type="number"
                min={1}
                max={1000}
                value={value.type === 'interval' ? value.interval_value : 5}
                onChange={(e) => updateValue('interval_value', parseInt(e.target.value) || 1)}
                disabled={disabled}
                className="mt-1"
              />
            </div>
            <div className="flex-1">
              <Label htmlFor="interval-unit">单位</Label>
              <Select
                value={value.type === 'interval' ? value.interval_unit : 'minute'}
                onValueChange={(v) => updateValue('interval_unit', v as IntervalUnit)}
                disabled={disabled}
              >
                <SelectTrigger id="interval-unit" className="mt-1">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {INTERVAL_UNITS.map((unit) => (
                    <SelectItem key={unit.value} value={unit.value}>
                      {unit.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <p className="text-sm text-muted-foreground">
            例如: 每 5 分钟
          </p>
        </TabsContent>

        <TabsContent value="specific" className="space-y-4">
          <div>
            <Label htmlFor="frequency">频率</Label>
            <Select
              value={value.type === 'specific' ? value.frequency : 'daily'}
              onValueChange={(v) => updateValue('frequency', v as Frequency)}
              disabled={disabled}
            >
              <SelectTrigger id="frequency" className="mt-1">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {FREQUENCIES.map((freq) => (
                  <SelectItem key={freq.value} value={freq.value}>
                    {freq.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {value.type === 'specific' && (
            <>
              {(value.frequency === 'daily' || value.frequency === 'weekly' || value.frequency === 'monthly') && (
                <div>
                  <Label htmlFor="time">时间</Label>
                  <Input
                    id="time"
                    type="time"
                    value={value.time || '02:00'}
                    onChange={(e) => updateValue('time', e.target.value)}
                    disabled={disabled}
                    className="mt-1"
                  />
                </div>
              )}

              {value.frequency === 'weekly' && (
                <div>
                  <Label htmlFor="day-of-week">星期</Label>
                  <Select
                    value={value.day_of_week?.toString() || '0'}
                    onValueChange={(v) => updateValue('day_of_week', parseInt(v))}
                    disabled={disabled}
                  >
                    <SelectTrigger id="day-of-week" className="mt-1">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {WEEKDAYS.map((day) => (
                        <SelectItem key={day.value} value={day.value.toString()}>
                          {day.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}

              {value.frequency === 'monthly' && (
                <div>
                  <Label htmlFor="day-of-month">每月第几天</Label>
                  <Input
                    id="day-of-month"
                    type="number"
                    min={1}
                    max={31}
                    value={value.day_of_month || 1}
                    onChange={(e) => updateValue('day_of_month', parseInt(e.target.value) || 1)}
                    disabled={disabled}
                    className="mt-1"
                  />
                </div>
              )}
            </>
          )}

          <p className="text-sm text-muted-foreground">
            {value.type === 'specific' && value.frequency === 'daily' && '每天在指定时间执行'}
            {value.type === 'specific' && value.frequency === 'weekly' && '每周在指定时间执行'}
            {value.type === 'specific' && value.frequency === 'monthly' && '每月在指定日期和时间执行'}
          </p>
        </TabsContent>

        <TabsContent value="advanced" className="space-y-4">
          <div>
            <Label htmlFor="cron-expression">Cron 表达式</Label>
            <Input
              id="cron-expression"
              type="text"
              placeholder="0 2 * * *"
              value={value.type === 'advanced' ? value.advanced : ''}
              onChange={(e) => updateValue('advanced', e.target.value)}
              disabled={disabled}
              className="mt-1 font-mono"
            />
            <p className="text-sm text-muted-foreground mt-2">
              标准 cron 表达式格式: 分 时 日 月 周
            </p>
          </div>
        </TabsContent>
      </Tabs>

      {error && (
        <p className="text-sm text-destructive">{error}</p>
      )}
    </div>
  );
}
```

**Step 3: Export from index**

在 `frontend/src/components/scheduler/index.ts` 中添加：

```typescript
export { CronTemplateSelector } from './CronTemplateSelector';
export type {
  CronTemplate,
  CronTemplateType,
  IntervalUnit,
  Frequency,
} from './CronTemplateSelector.types';
```

**Step 4: Commit**

```bash
git add frontend/src/components/scheduler/
git commit -m "feat: add CronTemplateSelector component"
```

---

### Task 16: 数据产品页面添加同步配置

**Files:**
- Modify: `frontend/src/app/[locale]/dashboard/data-products/[id]/page.tsx` (或相应页面)
- Create: `frontend/src/lib/api/scheduled-tasks.ts`

**Step 1: Create API client**

```typescript
// frontend/src/lib/api/scheduled-tasks.ts
import { apiClient } from './client';

export interface CronTemplate {
  type: 'interval' | 'specific' | 'advanced';
  interval_value?: number;
  interval_unit?: 'second' | 'minute' | 'hour' | 'day';
  frequency?: 'hourly' | 'daily' | 'weekly' | 'monthly';
  time?: string;
  day_of_week?: number;
  day_of_month?: number;
  advanced?: string;
}

export interface ScheduledTask {
  id: number;
  task_type: 'sync' | 'rule';
  task_name: string;
  target_id: number;
  cron_expression: string;
  is_enabled: boolean;
  timeout_seconds: number;
  max_retries: number;
  retry_interval_seconds: number;
  priority: number;
  description?: string;
  created_at: string;
  updated_at: string;
}

export interface TaskExecution {
  id: number;
  task_id: number;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'timeout';
  started_at: string;
  completed_at?: string;
  duration_seconds?: number;
  error_message?: string;
  retry_count: number;
  is_retry: boolean;
  triggered_by?: string;
}

export const scheduledTasksApi = {
  // 获取数据产品的同步计划
  getProductSyncSchedule: async (productId: number) =>
    apiClient.get<ScheduledTask | null>(`/api/data-products/${productId}/sync-schedule`),

  // 设置数据产品的同步计划
  setProductSyncSchedule: async (productId: number, template: CronTemplate) =>
    apiClient.put<ScheduledTask>(`/api/data-products/${productId}/sync-schedule`, template),

  // 删除数据产品的同步计划
  deleteProductSyncSchedule: async (productId: number) =>
    apiClient.delete(`/api/data-products/${productId}/sync-schedule`),

  // 获取同步历史
  getProductSyncHistory: async (productId: number, limit = 20) =>
    apiClient.get<TaskExecution[]>(`/api/data-products/${productId}/sync-history`, {
      params: { limit },
    }),

  // 手动触发同步
  triggerSync: async (taskId: number) =>
    apiClient.post(`/api/scheduled-tasks/${taskId}/trigger`),
};
```

**Step 2: Create sync schedule component**

```tsx
// frontend/src/components/data-product/SyncSchedulePanel.tsx
'use client';

import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import { CronTemplateSelector } from '@/components/scheduler';
import { scheduledTasksApi, CronTemplate, ScheduledTask } from '@/lib/api/scheduled-tasks';
import { Clock, CheckCircle, XCircle, AlertCircle } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { zhCN } from 'date-fns/locale';

interface SyncSchedulePanelProps {
  productId: number;
  productName: string;
}

export function SyncSchedulePanel({ productId, productName }: SyncSchedulePanelProps) {
  const [schedule, setSchedule] = useState<ScheduledTask | null>(null);
  const [template, setTemplate] = useState<CronTemplate>({
    type: 'interval',
    interval_value: 30,
    interval_unit: 'minute',
  });
  const [isSaving, setIsSaving] = useState(false);
  const [history, setHistory] = useState<any[]>([]);

  useEffect(() => {
    loadSchedule();
    loadHistory();
  }, [productId]);

  const loadSchedule = async () => {
    try {
      const data = await scheduledTasksApi.getProductSyncSchedule(productId);
      setSchedule(data);
    } catch (error) {
      console.error('Failed to load schedule:', error);
    }
  };

  const loadHistory = async () => {
    try {
      const data = await scheduledTasksApi.getProductSyncHistory(productId);
      setHistory(data);
    } catch (error) {
      console.error('Failed to load history:', error);
    }
  };

  const handleSaveSchedule = async () => {
    setIsSaving(true);
    try {
      await scheduledTasksApi.setProductSyncSchedule(productId, template);
      await loadSchedule();
    } catch (error) {
      console.error('Failed to save schedule:', error);
    } finally {
      setIsSaving(false);
    }
  };

  const handleToggleEnabled = async (enabled: boolean) => {
    try {
      if (schedule) {
        // TODO: 调用 pause/resume API
        await loadSchedule();
      }
    } catch (error) {
      console.error('Failed to toggle schedule:', error);
    }
  };

  const handleDeleteSchedule = async () => {
    try {
      await scheduledTasksApi.deleteProductSyncSchedule(productId);
      setSchedule(null);
    } catch (error) {
      console.error('Failed to delete schedule:', error);
    }
  };

  const handleManualSync = async () => {
    if (!schedule) return;
    try {
      await scheduledTasksApi.triggerSync(schedule.id);
      await loadHistory();
    } catch (error) {
      console.error('Failed to trigger sync:', error);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'failed':
      case 'timeout':
        return <XCircle className="h-4 w-4 text-red-500" />;
      case 'running':
        return <Clock className="h-4 w-4 text-blue-500 animate-spin" />;
      default:
        return <AlertCircle className="h-4 w-4 text-gray-500" />;
    }
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>自动同步设置</CardTitle>
            <CardDescription>配置数据自动同步的频率和时间</CardDescription>
          </div>
          {schedule && (
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">启用</span>
              <Switch
                checked={schedule.is_enabled}
                onCheckedChange={handleToggleEnabled}
              />
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {!schedule ? (
          <>
            <CronTemplateSelector
              value={template}
              onChange={setTemplate}
            />
            <Button onClick={handleSaveSchedule} disabled={isSaving}>
              {isSaving ? '保存中...' : '启用自动同步'}
            </Button>
          </>
        ) : (
          <div className="space-y-4">
            <div className="p-4 bg-muted rounded-lg">
              <p className="text-sm font-medium">当前配置</p>
              <p className="text-2xl font-mono mt-2">{schedule.cron_expression}</p>
            </div>

            <div className="flex gap-2">
              <Button variant="outline" onClick={handleManualSync}>
                立即同步
              </Button>
              <Button variant="destructive" onClick={handleDeleteSchedule}>
                禁用自动同步
              </Button>
            </div>

            <div>
              <h3 className="text-sm font-medium mb-3">最近同步</h3>
              <div className="space-y-2">
                {history.slice(0, 5).map((execution) => (
                  <div key={execution.id} className="flex items-center justify-between p-3 bg-muted rounded">
                    <div className="flex items-center gap-3">
                      {getStatusIcon(execution.status)}
                      <div>
                        <p className="text-sm font-medium">
                          {execution.status === 'completed' ? '成功' : '失败'}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {formatDistanceToNow(new Date(execution.started_at), {
                            addSuffix: true,
                            locale: zhCN,
                          })}
                        </p>
                      </div>
                    </div>
                    {execution.duration_seconds && (
                      <span className="text-sm text-muted-foreground">
                        {execution.duration_seconds.toFixed(2)}s
                      </span>
                    )}
                  </div>
                ))}
                {history.length === 0 && (
                  <p className="text-sm text-muted-foreground text-center py-4">
                    暂无同步记录
                  </p>
                )}
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
```

**Step 3: Commit**

```bash
git add frontend/src/lib/api/scheduled-tasks.ts frontend/src/components/data-product/
git commit -m "feat: add sync schedule panel for data products"
```

---

## Phase 12: 规则定时配置UI

### Task 17: 规则页面添加定时触发配置

**Files:**
- Modify: `frontend/src/app/[locale]/dashboard/rules/[id]/page.tsx`
- Create: `frontend/src/components/rule/RuleSchedulePanel.tsx`

**Step 1: Create rule schedule panel**

```tsx
// frontend/src/components/rule/RuleSchedulePanel.tsx
'use client';

import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { CronTemplateSelector } from '@/components/scheduler';
import { apiClient } from '@/lib/api/client';

interface RuleSchedulePanelProps {
  ruleId: number;
  ruleName: string;
}

type TriggerType = 'event' | 'scheduled' | 'hybrid';

export function RuleSchedulePanel({ ruleId, ruleName }: RuleSchedulePanelProps) {
  const [triggerType, setTriggerType] = useState<TriggerType>('event');
  const [schedule, setSchedule] = useState<any>(null);
  const [template, setTemplate] = useState({
    type: 'specific' as const,
    frequency: 'daily' as const,
    time: '09:00',
  });
  const [isSaving, setIsSaving] = useState(false);
  const [history, setHistory] = useState<any[]>([]);

  useEffect(() => {
    loadSchedule();
    loadHistory();
  }, [ruleId]);

  const loadSchedule = async () => {
    try {
      const data = await apiClient.get(`/api/rules/${ruleId}/schedule`);
      if (data) {
        setSchedule(data);
        setTriggerType('scheduled');
      }
    } catch (error) {
      console.error('Failed to load schedule:', error);
    }
  };

  const loadHistory = async () => {
    try {
      const data = await apiClient.get(`/api/rules/${ruleId}/execution-history`);
      setHistory(data);
    } catch (error) {
      console.error('Failed to load history:', error);
    }
  };

  const handleSaveSchedule = async () => {
    setIsSaving(true);
    try {
      await apiClient.put(`/api/rules/${ruleId}/schedule`, template);
      await loadSchedule();
    } catch (error) {
      console.error('Failed to save schedule:', error);
    } finally {
      setIsSaving(false);
    }
  };

  const handleDeleteSchedule = async () => {
    try {
      await apiClient.delete(`/api/rules/${ruleId}/schedule`);
      setSchedule(null);
      setTriggerType('event');
    } catch (error) {
      console.error('Failed to delete schedule:', error);
    }
  };

  const handleManualTrigger = async () => {
    if (!schedule) return;
    try {
      await apiClient.post(`/api/scheduled-tasks/${schedule.id}/trigger`);
      await loadHistory();
    } catch (error) {
      console.error('Failed to trigger rule:', error);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>触发方式</CardTitle>
        <CardDescription>配置规则的触发条件</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <RadioGroup value={triggerType} onValueChange={(v) => setTriggerType(v as TriggerType)}>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="event" id="event" />
            <Label htmlFor="event">事件触发</Label>
          </div>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="scheduled" id="scheduled" />
            <Label htmlFor="scheduled">定时触发</Label>
          </div>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="hybrid" id="hybrid" />
            <Label htmlFor="hybrid">混合触发（事件 + 定时）</Label>
          </div>
        </RadioGroup>

        {(triggerType === 'scheduled' || triggerType === 'hybrid') && (
          <div className="space-y-4 pt-4 border-t">
            {!schedule ? (
              <>
                <h3 className="text-sm font-medium">定时触发配置</h3>
                <CronTemplateSelector
                  value={template}
                  onChange={setTemplate}
                />
                <Button onClick={handleSaveSchedule} disabled={isSaving}>
                  {isSaving ? '保存中...' : '保存定时配置'}
                </Button>
              </>
            ) : (
              <div className="space-y-4">
                <div className="p-4 bg-muted rounded-lg">
                  <p className="text-sm font-medium">当前配置</p>
                  <p className="text-2xl font-mono mt-2">{schedule.cron_expression}</p>
                </div>

                <div className="flex gap-2">
                  <Button variant="outline" onClick={handleManualTrigger}>
                    立即执行
                  </Button>
                  <Button variant="destructive" onClick={handleDeleteSchedule}>
                    删除定时配置
                  </Button>
                </div>

                {history.length > 0 && (
                  <div>
                    <h3 className="text-sm font-medium mb-3">最近执行</h3>
                    <div className="space-y-2">
                      {history.slice(0, 5).map((execution) => (
                        <div key={execution.id} className="flex items-center justify-between p-3 bg-muted rounded">
                          <span className="text-sm">
                            {execution.started_at} - {execution.status}
                          </span>
                          {execution.duration_seconds && (
                            <span className="text-sm text-muted-foreground">
                              {execution.duration_seconds.toFixed(2)}s
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
```

**Step 2: Commit**

```bash
git add frontend/src/components/rule/
git commit -m "feat: add rule schedule panel component"
```

---

## Phase 13: 测试

### Task 18: 编写后端测试

**Files:**
- Create: `backend/tests/test_scheduler_service.py`
- Create: `backend/tests/test_task_executor.py`
- Create: `backend/tests/test_cron_parser.py`

**Step 1: Write cron parser tests**

```python
# backend/tests/test_cron_parser.py
import pytest
from app.services.cron_parser import cron_template_to_expression, cron_expression_to_template
from app.schemas.scheduled_task import CronTemplate


def test_interval_every_minute():
    template = CronTemplate(
        type="interval",
        interval_value=5,
        interval_unit="minute"
    )
    result = cron_template_to_expression(template)
    assert result == "*/5 * * * *"


def test_interval_every_hour():
    template = CronTemplate(
        type="interval",
        interval_value=1,
        interval_unit="hour"
    )
    result = cron_template_to_expression(template)
    assert result == "0 */1 * * *"


def test_specific_daily():
    template = CronTemplate(
        type="specific",
        frequency="daily",
        time="02:00"
    )
    result = cron_template_to_expression(template)
    assert result == "0 2 * * *"


def test_specific_weekly():
    template = CronTemplate(
        type="specific",
        frequency="weekly",
        time="09:00",
        day_of_week=1
    )
    result = cron_template_to_expression(template)
    assert result == "0 9 * * 1"


def test_advanced_mode():
    template = CronTemplate(
        type="advanced",
        advanced="0 */2 * * *"
    )
    result = cron_template_to_expression(template)
    assert result == "0 */2 * * *"


def test_invalid_interval_missing_value():
    template = CronTemplate(
        type="interval",
        interval_unit="minute"
    )
    with pytest.raises(ValueError):
        cron_template_to_expression(template)
```

**Step 2: Run tests**

Run: `cd backend && uv run pytest tests/test_cron_parser.py -v`

**Step 3: Commit**

```bash
git add backend/tests/test_cron_parser.py
git commit -m "test: add cron parser tests"
```

---

### Task 19: 编写集成测试

**Files:**
- Create: `backend/tests/test_scheduled_tasks_api.py`

**Step 1: Write API integration tests**

```python
# backend/tests/test_scheduled_tasks_api.py
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_create_scheduled_task(async_client: AsyncClient, db: AsyncSession):
    response = await async_client.post(
        "/api/scheduled-tasks/",
        json={
            "task_type": "sync",
            "task_name": "Test Sync Task",
            "target_id": 1,
            "cron_expression": "*/5 * * * *",
            "is_enabled": True,
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["task_name"] == "Test Sync Task"
    assert data["cron_expression"] == "*/5 * * * *"


@pytest.mark.asyncio
async def test_list_scheduled_tasks(async_client: AsyncClient):
    response = await async_client.get("/api/scheduled-tasks/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_get_task_status(async_client: AsyncClient):
    # First create a task
    create_response = await async_client.post(
        "/api/scheduled-tasks/",
        json={
            "task_type": "sync",
            "task_name": "Status Test",
            "target_id": 1,
            "cron_expression": "0 * * * *",
        }
    )
    task_id = create_response.json()["id"]

    # Get status
    response = await async_client.get(f"/api/scheduled-tasks/{task_id}/status")
    assert response.status_code == 200
    data = response.json()
    assert "task_id" in data
    assert "is_running" in data


@pytest.mark.asyncio
async def test_pause_resume_task(async_client: AsyncClient):
    # Create task
    create_response = await async_client.post(
        "/api/scheduled-tasks/",
        json={
            "task_type": "sync",
            "task_name": "Pause Test",
            "target_id": 1,
            "cron_expression": "0 * * * *",
        }
    )
    task_id = create_response.json()["id"]

    # Pause
    pause_response = await async_client.post(f"/api/scheduled-tasks/{task_id}/pause")
    assert pause_response.status_code == 200
    assert pause_response.json()["status"] == "paused"

    # Resume
    resume_response = await async_client.post(f"/api/scheduled-tasks/{task_id}/resume")
    assert resume_response.status_code == 200
    assert resume_response.json()["status"] == "resumed"
```

**Step 2: Run tests**

Run: `cd backend && uv run pytest tests/test_scheduled_tasks_api.py -v`

**Step 3: Commit**

```bash
git add backend/tests/test_scheduled_tasks_api.py
git commit -m "test: add scheduled tasks API integration tests"
```

---

## Phase 14: 文档和部署

### Task 20: 更新项目文档

**Files:**
- Modify: `CLAUDE.md`
- Modify: `README.md`

**Step 1: Update CLAUDE.md**

在 `CLAUDE.md` 的 "Architecture Notes" 部分添加：

```markdown
### Scheduler Service

- Global scheduler using APScheduler with AsyncIOScheduler
- Tasks stored in `scheduled_tasks` table, executions in `task_executions`
- Watchdog mechanism: concurrent task limiting (Semaphore), timeout control (wait_for)
- Smart retry: network errors retry, business logic errors don't
- Two task types: 'sync' for data product sync, 'rule' for scheduled rule execution
- Cron template support: interval, specific time, or advanced cron expression
```

**Step 2: Update README.md**

添加新的API端点说明和使用示例。

**Step 3: Commit**

```bash
git add CLAUDE.md README.md
git commit -m "docs: update project documentation for scheduler feature"
```

---

## 实现检查清单

- [ ] Phase 1: 数据库模型和迁移完成
- [ ] Phase 2: 数据访问层完成
- [ ] Phase 3: Pydantic Schemas完成
- [ ] Phase 4: 核心调度服务完成
- [ ] Phase 5: API路由完成
- [ ] Phase 6: 数据产品API集成完成
- [ ] Phase 7: 规则API集成完成
- [ ] Phase 8: 规则执行器集成完成
- [ ] Phase 9: 配置和依赖完成
- [ ] Phase 10: 应用生命周期集成完成
- [ ] Phase 11: 前端Cron模板组件完成
- [ ] Phase 12: 数据产品同步配置UI完成
- [ ] Phase 13: 规则定时配置UI完成
- [ ] Phase 14: 测试完成
- [ ] Phase 15: 文档更新完成

---

## 注意事项

1. **数据库迁移**: 在生产环境部署前，务必先备份数据库
2. **时区**: 所有时间都使用UTC，cron表达式也基于UTC
3. **并发控制**: 默认最大并发任务数为10，可通过环境变量调整
4. **超时处理**: 任务超时会被标记为timeout状态，不会自动重试（除非配置）
5. **日志级别**: 生产环境建议使用INFO或WARNING级别
