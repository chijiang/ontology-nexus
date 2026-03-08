"""Repository classes for scheduled task database operations.

This module provides repository classes for managing scheduled tasks
and their execution history in the database.
"""

from typing import List, Optional
from sqlalchemy import select, update, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.scheduled_task import ScheduledTask, TaskExecution


class ScheduledTaskRepository:
    """Repository for ScheduledTask database operations.

    Provides CRUD operations for managing scheduled tasks
    that support cron-based scheduling for data synchronization
    and rule execution tasks.
    """

    def __init__(self, session: AsyncSession):
        """Initialize the repository with a database session.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def create(self, task: ScheduledTask) -> ScheduledTask:
        """Create a new scheduled task.

        Args:
            task: ScheduledTask instance to create

        Returns:
            Created ScheduledTask instance
        """
        self.session.add(task)
        await self.session.commit()
        await self.session.refresh(task)
        return task

    async def get_by_id(self, task_id: int) -> Optional[ScheduledTask]:
        """Get a scheduled task by ID.

        Args:
            task_id: Task ID

        Returns:
            ScheduledTask instance or None
        """
        result = await self.session.execute(
            select(ScheduledTask).where(ScheduledTask.id == task_id)
        )
        return result.scalar_one_or_none()

    async def list_tasks(
        self,
        task_type: Optional[str] = None,
        is_enabled: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[ScheduledTask]:
        """List scheduled tasks with optional filters.

        Args:
            task_type: Filter by task type ('sync' or 'rule')
            is_enabled: Filter by enabled status
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of ScheduledTask instances
        """
        query = select(ScheduledTask)

        filters = []
        if task_type is not None:
            filters.append(ScheduledTask.task_type == task_type)
        if is_enabled is not None:
            filters.append(ScheduledTask.is_enabled == is_enabled)

        if filters:
            query = query.where(and_(*filters))

        query = query.order_by(ScheduledTask.created_at.desc()).limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_enabled_tasks(self) -> List[ScheduledTask]:
        """Get all enabled scheduled tasks.

        Returns:
            List of enabled ScheduledTask instances ordered by priority
        """
        result = await self.session.execute(
            select(ScheduledTask)
            .where(ScheduledTask.is_enabled == True)
            .order_by(ScheduledTask.priority.desc(), ScheduledTask.created_at.asc())
        )
        return list(result.scalars().all())

    async def update(
        self, task_id: int, updates: dict
    ) -> Optional[ScheduledTask]:
        """Update a scheduled task.

        Args:
            task_id: Task ID to update
            updates: Dictionary of fields to update

        Returns:
            Updated ScheduledTask or None if not found
        """
        result = await self.session.execute(
            update(ScheduledTask)
            .where(ScheduledTask.id == task_id)
            .values(**updates)
            .returning(ScheduledTask)
        )
        await self.session.commit()
        return result.scalar_one_or_none()

    async def delete(self, task_id: int) -> bool:
        """Delete a scheduled task.

        Args:
            task_id: Task ID to delete

        Returns:
            True if deleted, False if not found
        """
        task = await self.get_by_id(task_id)
        if task is None:
            return False

        await self.session.delete(task)
        await self.session.commit()
        return True

    async def get_by_target(
        self, task_type: str, target_id: int
    ) -> Optional[ScheduledTask]:
        """Get a scheduled task by type and target ID.

        Args:
            task_type: Task type ('sync' or 'rule')
            target_id: Target entity ID

        Returns:
            ScheduledTask instance or None
        """
        result = await self.session.execute(
            select(ScheduledTask).where(
                and_(
                    ScheduledTask.task_type == task_type,
                    ScheduledTask.target_id == target_id,
                )
            )
        )
        return result.scalar_one_or_none()


class TaskExecutionRepository:
    """Repository for TaskExecution database operations.

    Provides CRUD operations for managing task execution history,
    tracking the status and results of scheduled task executions.
    """

    def __init__(self, session: AsyncSession):
        """Initialize the repository with a database session.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def create(self, execution: TaskExecution) -> TaskExecution:
        """Create a new task execution record.

        Args:
            execution: TaskExecution instance to create

        Returns:
            Created TaskExecution instance
        """
        self.session.add(execution)
        await self.session.commit()
        await self.session.refresh(execution)
        return execution

    async def get_by_id(self, execution_id: int) -> Optional[TaskExecution]:
        """Get a task execution by ID.

        Args:
            execution_id: Execution ID

        Returns:
            TaskExecution instance or None
        """
        result = await self.session.execute(
            select(TaskExecution)
            .options(selectinload(TaskExecution.scheduled_task))
            .where(TaskExecution.id == execution_id)
        )
        return result.scalar_one_or_none()

    async def list_by_task(
        self, task_id: int, limit: int = 50, offset: int = 0
    ) -> List[TaskExecution]:
        """List executions for a specific task.

        Args:
            task_id: Scheduled task ID
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of TaskExecution instances ordered by started_at desc
        """
        result = await self.session.execute(
            select(TaskExecution)
            .where(TaskExecution.task_id == task_id)
            .order_by(TaskExecution.started_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def list_recent(
        self, task_type: Optional[str] = None, limit: int = 100
    ) -> List[TaskExecution]:
        """List recent task executions.

        Args:
            task_type: Optional filter by task type
            limit: Maximum number of results

        Returns:
            List of TaskExecution instances ordered by started_at desc
        """
        query = select(TaskExecution).options(
            selectinload(TaskExecution.scheduled_task)
        )

        if task_type is not None:
            query = query.join(ScheduledTask).where(
                ScheduledTask.task_type == task_type
            )

        query = query.order_by(TaskExecution.started_at.desc()).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update(
        self, execution_id: int, updates: dict
    ) -> Optional[TaskExecution]:
        """Update a task execution.

        Args:
            execution_id: Execution ID to update
            updates: Dictionary of fields to update

        Returns:
            Updated TaskExecution or None if not found
        """
        result = await self.session.execute(
            update(TaskExecution)
            .where(TaskExecution.id == execution_id)
            .values(**updates)
            .returning(TaskExecution)
        )
        await self.session.commit()
        return result.scalar_one_or_none()

    async def get_running_executions(
        self, task_id: Optional[int] = None
    ) -> List[TaskExecution]:
        """Get all currently running executions.

        Args:
            task_id: Optional filter by specific task ID

        Returns:
            List of running TaskExecution instances
        """
        query = select(TaskExecution).where(TaskExecution.status == "running")

        if task_id is not None:
            query = query.where(TaskExecution.task_id == task_id)

        result = await self.session.execute(query)
        return list(result.scalars().all())
