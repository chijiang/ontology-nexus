# backend/app/services/task_executor.py
"""
Task Executor Service for Scheduled Tasks

This module provides the TaskExecutor service that executes scheduled tasks
with proper concurrency control, timeout handling, and retry logic.
"""

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Callable, Awaitable
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.exc import IntegrityError

from app.models.scheduled_task import ScheduledTask, TaskExecution
from app.repositories.scheduled_task_repository import TaskExecutionRepository
from app.services.sync_service import SyncService


logger = logging.getLogger(__name__)


# Error patterns for retry determination
RETRYABLE_PATTERNS = [
    r"connection.*timeout",
    r"network.*unreachable",
    r"503",
    r"504",
    r"temporarily unavailable",
    r"connection refused",
    r"TimeoutError",
    r"AsyncIO timeout",
    r"timeout awaiting",
]

NON_RETRYABLE_PATTERNS = [
    r"auth.*failed",
    r"unauthorized",
    r"401",
    r"403",
    r"invalid format",
    r"validation error",
    r"400 Bad Request",
    r"IntegrityError",
    r"unique constraint",
    r"foreign key constraint",
]


class TaskExecutor:
    """Executes scheduled tasks with watchdog mechanism.

    Features:
    - Concurrency control via semaphore
    - Per-task timeout enforcement
    - Automatic retry with exponential backoff
    - Error pattern matching for retry decisions
    - Comprehensive execution tracking
    """

    def __init__(
        self,
        max_concurrent_tasks: int = 10,
        default_timeout: int = 300,
    ):
        """Initialize the TaskExecutor.

        Args:
            max_concurrent_tasks: Maximum number of tasks to run concurrently
            default_timeout: Default timeout in seconds for task execution
        """
        self.semaphore = asyncio.Semaphore(max_concurrent_tasks)
        self.default_timeout = default_timeout
        self.running_tasks: Dict[int, asyncio.Task] = {}
        self._task_executors: Dict[str, Callable] = {
            "sync": self._execute_sync_task,
            "rule": self._execute_rule_task,
        }

    async def execute_task(
        self,
        task: ScheduledTask,
        session_factory: async_sessionmaker[AsyncSession],
        triggered_by: str = "scheduler",
    ) -> Dict[str, Any]:
        """Execute a scheduled task with full monitoring and retry logic.

        Args:
            task: The ScheduledTask to execute
            session_factory: Async session factory for database operations
            triggered_by: How this execution was triggered ('scheduler'|'manual'|'retry')

        Returns:
            Dictionary containing execution results with keys:
            - success: bool - Whether execution succeeded
            - execution_id: int - ID of the execution record
            - status: str - Final status ('completed'|'failed'|'timeout')
            - result_data: dict - Optional result data
            - error_message: str - Optional error message
            - retry_count: int - Number of retries attempted
        """
        execution_id: Optional[int] = None
        retry_count = 0
        last_error: Optional[Exception] = None
        last_error_type: Optional[str] = None
        last_error_message: Optional[str] = None

        async with self.semaphore:
            # Create execution record
            async with session_factory() as session:
                exec_repo = TaskExecutionRepository(session)
                execution = TaskExecution(
                    task_id=task.id,
                    status="pending",
                    started_at=datetime.now(timezone.utc).replace(tzinfo=None),
                    triggered_by=triggered_by,
                    retry_count=0,
                    is_retry=(triggered_by == "retry"),
                )
                execution = await exec_repo.create(execution)
                execution_id = execution.id

            # Mark task as running
            self.running_tasks[task.id] = asyncio.current_task()

            try:
                # Attempt execution with retries
                while retry_count <= task.max_retries:
                    # Update execution status to running
                    async with session_factory() as session:
                        exec_repo = TaskExecutionRepository(session)
                        await exec_repo.update(
                            execution_id,
                            {"status": "running", "retry_count": retry_count},
                        )

                    try:
                        # Execute with timeout
                        timeout = task.timeout_seconds or self.default_timeout
                        result = await asyncio.wait_for(
                            self._execute_task_internal(
                                task, session_factory, triggered_by
                            ),
                            timeout=timeout,
                        )

                        # Success - update execution record
                        async with session_factory() as session:
                            exec_repo = TaskExecutionRepository(session)
                            completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
                            duration = (
                                completed_at - execution.started_at
                            ).total_seconds()

                            await exec_repo.update(
                                execution_id,
                                {
                                    "status": "completed",
                                    "completed_at": completed_at,
                                    "duration_seconds": duration,
                                    "result_data": result,
                                },
                            )

                        logger.info(
                            f"Task {task.id} ({task.task_name}) completed successfully "
                            f"in {duration:.2f}s"
                        )

                        return {
                            "success": True,
                            "execution_id": execution_id,
                            "status": "completed",
                            "result_data": result,
                            "error_message": None,
                            "retry_count": retry_count,
                        }

                    except asyncio.TimeoutError as e:
                        last_error = e
                        last_error_type = "TimeoutError"
                        last_error_message = (
                            f"Task exceeded timeout of {timeout} seconds"
                        )
                        logger.warning(
                            f"Task {task.id} ({task.task_name}) timed out after {timeout}s"
                        )

                        # Timeout is not retryable - fail immediately
                        break

                    except Exception as e:
                        last_error = e
                        last_error_type = type(e).__name__
                        last_error_message = str(e)

                        # Check if error is retryable
                        if not self._should_retry(e):
                            logger.warning(
                                f"Task {task.id} ({task.task_name}) encountered "
                                f"non-retryable error: {e}"
                            )
                            break

                        # Check if we should retry
                        if retry_count < task.max_retries:
                            retry_count += 1
                            delay = task.retry_interval_seconds * (2 ** (retry_count - 1))

                            logger.info(
                                f"Task {task.id} ({task.task_name}) failed with "
                                f"retryable error, retrying in {delay}s "
                                f"(attempt {retry_count}/{task.max_retries})"
                            )

                            await asyncio.sleep(delay)
                        else:
                            logger.warning(
                                f"Task {task.id} ({task.task_name}) failed after "
                                f"{retry_count} retries"
                            )
                            break

                # All retries exhausted or non-retryable error
                async with session_factory() as session:
                    exec_repo = TaskExecutionRepository(session)
                    completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
                    duration = (completed_at - execution.started_at).total_seconds()

                    # Determine final status
                    final_status = (
                        "timeout" if last_error_type == "TimeoutError" else "failed"
                    )

                    await exec_repo.update(
                        execution_id,
                        {
                            "status": final_status,
                            "completed_at": completed_at,
                            "duration_seconds": duration,
                            "error_message": last_error_message,
                            "error_type": last_error_type,
                            "retry_count": retry_count,
                        },
                    )

                logger.error(
                    f"Task {task.id} ({task.task_name}) failed with status: {final_status}, "
                    f"error: {last_error_message}"
                )

                return {
                    "success": False,
                    "execution_id": execution_id,
                    "status": final_status,
                    "result_data": None,
                    "error_message": last_error_message,
                    "retry_count": retry_count,
                }

            finally:
                # Remove from running tasks
                self.running_tasks.pop(task.id, None)

    async def _execute_task_internal(
        self,
        task: ScheduledTask,
        session_factory: async_sessionmaker[AsyncSession],
        triggered_by: str,
    ) -> Dict[str, Any]:
        """Internal method to execute a task.

        Args:
            task: The ScheduledTask to execute
            session_factory: Async session factory for database operations
            triggered_by: How this execution was triggered

        Returns:
            Dictionary containing task execution results

        Raises:
            Exception: If task execution fails
        """
        executor = self._task_executors.get(task.task_type)

        if executor is None:
            raise ValueError(f"Unknown task type: {task.task_type}")

        return await executor(task, session_factory)

    async def _execute_sync_task(
        self,
        task: ScheduledTask,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> Dict[str, Any]:
        """Execute a data product sync task.

        Args:
            task: The ScheduledTask to execute (task_type='sync')
            session_factory: Async session factory for database operations

        Returns:
            Dictionary containing sync results

        Raises:
            Exception: If sync fails
        """
        async with session_factory() as session:
            sync_service = SyncService(session)
            result = await sync_service.sync_data_product(
                product_id=task.target_id,
                sync_relationships=True,
            )

            logger.info(
                f"Sync task {task.id} completed: "
                f"processed={result.get('processed', 0)}, "
                f"created={result.get('created', 0)}, "
                f"updated={result.get('updated', 0)}, "
                f"failed={result.get('failed', 0)}"
            )

            return result

    async def _execute_rule_task(
        self,
        task: ScheduledTask,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> Dict[str, Any]:
        """Execute a rule evaluation task.

        Args:
            task: The ScheduledTask to execute (task_type='rule')
            session_factory: Async session factory for database operations

        Returns:
            Dictionary containing rule execution results

        Raises:
            NotImplementedError: Rule execution is not yet implemented
        """
        # TODO: Implement rule execution
        # This will integrate with the rule engine when ready
        raise NotImplementedError(
            "Rule execution is not yet implemented. "
            "This is a placeholder for future rule task execution."
        )

    def _should_retry(self, error: Exception) -> bool:
        """Determine if an error is retryable based on pattern matching.

        Args:
            error: The exception to evaluate

        Returns:
            True if the error is retryable, False otherwise
        """
        error_str = str(error)
        error_type = type(error).__name__

        # Check non-retryable patterns first
        for pattern in NON_RETRYABLE_PATTERNS:
            if re.search(pattern, error_str, re.IGNORECASE):
                return False

        # Check for specific exception types
        if isinstance(error, IntegrityError):
            return False

        # Check retryable patterns
        for pattern in RETRYABLE_PATTERNS:
            if re.search(pattern, error_str, re.IGNORECASE):
                return True

        # Check exception type
        if error_type in ("TimeoutError", "AsyncIO timeout"):
            return True

        # Default: don't retry unknown errors
        return False

    async def cancel_task(self, task_id: int) -> bool:
        """Cancel a running task.

        Args:
            task_id: ID of the task to cancel

        Returns:
            True if task was cancelled, False if not found or already completed
        """
        running_task = self.running_tasks.get(task_id)

        if running_task is None:
            return False

        running_task.cancel()
        try:
            await running_task
        except asyncio.CancelledError:
            pass

        return True

    def get_running_task_count(self) -> int:
        """Get the number of currently running tasks.

        Returns:
            Number of running tasks
        """
        return len(self.running_tasks)

    def is_task_running(self, task_id: int) -> bool:
        """Check if a specific task is currently running.

        Args:
            task_id: ID of the task to check

        Returns:
            True if the task is running, False otherwise
        """
        return task_id in self.running_tasks
