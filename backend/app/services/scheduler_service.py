# backend/app/services/scheduler_service.py
"""
Scheduler Service for Managing Scheduled Tasks

This module provides the SchedulerService that integrates APScheduler
for cron-based scheduling of tasks with persistent job storage.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import settings
from app.models.scheduled_task import ScheduledTask
from app.repositories.scheduled_task_repository import ScheduledTaskRepository
from app.services.task_executor import TaskExecutor


logger = logging.getLogger(__name__)


# Global reference for APScheduler jobs (to avoid pickling issues with persistent storage)
_global_scheduler_instance: Optional["SchedulerService"] = None


def parse_cron_expression(cron_expr: str, timezone: str = "UTC") -> CronTrigger:
    """Parse cron expression supporting 5, 6, or 7 parts.

    Args:
        cron_expr: Cron expression string
        timezone: Timezone for the trigger

    Returns:
        CronTrigger instance

    Supported formats:
        5 parts: minute hour day month weekday (standard cron)
        6 parts: second minute hour day month weekday
        7 parts: second minute hour day month weekday year
    """
    parts = cron_expr.strip().split()
    num_parts = len(parts)

    if num_parts == 5:
        # Standard cron: minute hour day month weekday
        return CronTrigger.from_crontab(cron_expr, timezone=timezone)
    elif num_parts == 6:
        # With seconds: second minute hour day month weekday
        second, minute, hour, day, month, day_of_week = parts
        return CronTrigger(
            second=second,
            minute=minute,
            hour=hour,
            day=day,
            month=month,
            day_of_week=day_of_week,
            timezone=timezone,
        )
    elif num_parts == 7:
        # With year: second minute hour day month weekday year
        second, minute, hour, day, month, day_of_week, year = parts
        return CronTrigger(
            second=second,
            minute=minute,
            hour=hour,
            day=day,
            month=month,
            day_of_week=day_of_week,
            year=year,
            timezone=timezone,
        )
    else:
        raise ValueError(
            f"Cron expression must have 5-7 parts, got {num_parts}: {cron_expr}"
        )


async def _job_executor_wrapper(task_id: int) -> None:
    """Standalone wrapper function for APScheduler jobs to avoid instance pickling issues.

    This function is used as the job target in APScheduler. It delegates execution
    to the globally available SchedulerService instance.
    """
    if _global_scheduler_instance:
        await _global_scheduler_instance._execute_scheduled_task(task_id)
    else:
        # Fallback for when the service hasn't been initialized yet or in different context
        logger.error(
            f"Cannot execute task {task_id}: SchedulerService instance not globally available"
        )


class SchedulerService:
    """Service for managing APScheduler and scheduled tasks.

    Features:
    - Persistent job storage via SQLAlchemyJobStore
    - Cron-based scheduling with standard cron expressions
    - Automatic task loading from database on initialization
    - Dynamic task scheduling and unscheduling
    - Task execution through TaskExecutor with retry logic
    - Concurrent task execution control
    """

    def __init__(
        self,
        db_session_factory: async_sessionmaker[AsyncSession],
        max_concurrent_tasks: int = 10,
        default_timeout: int = 300,
        rule_engine: Any = None,
    ):
        """Initialize the SchedulerService.

        Args:
            db_session_factory: Async session factory for database operations
            max_concurrent_tasks: Maximum number of tasks to run concurrently
            default_timeout: Default timeout in seconds for task execution
        """
        # Configure jobstores with SQLAlchemyJobStore
        # Note: APScheduler requires synchronous URL, so we use psycopg (v3) which is already in dependencies
        # Use effective_database_url to respect POSTGRES_HOST overrides
        sync_db_url = settings.effective_database_url.replace(
            "postgresql+asyncpg", "postgresql+psycopg"
        )
        jobstores = {
            "default": SQLAlchemyJobStore(url=sync_db_url, tablename="apscheduler_jobs")
        }

        # Configure executors
        executors = {"default": AsyncIOExecutor()}

        # Configure job defaults
        job_defaults = {
            "coalesce": True,  # Combine missed executions into one
            "max_instances": 1,  # Only one instance of a job at a time
            "misfire_grace_time": 60,  # Allow 60 seconds grace for misfires
        }

        # Create the scheduler
        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone="UTC",
        )

        self.db_session_factory = db_session_factory
        self.executor = TaskExecutor(
            max_concurrent_tasks=max_concurrent_tasks,
            default_timeout=default_timeout,
            rule_engine=rule_engine,
        )
        self.repository: Optional[ScheduledTaskRepository] = None

        # Set global instance for job execution
        global _global_scheduler_instance
        _global_scheduler_instance = self

    async def initialize(self) -> None:
        """Initialize the scheduler and load enabled tasks from database.

        This method should be called during application startup to:
        1. Start the APScheduler
        2. Load all enabled scheduled tasks from the database
        3. Schedule each enabled task
        """
        logger.info("Initializing SchedulerService...")

        # Start the scheduler
        self.scheduler.start()

        # Load enabled tasks from database and schedule them
        async with self.db_session_factory() as session:
            self.repository = ScheduledTaskRepository(session)
            enabled_tasks = await self.repository.get_enabled_tasks()

            scheduled_count = 0
            for task in enabled_tasks:
                try:
                    await self._schedule_task(task)
                    scheduled_count += 1
                except Exception as e:
                    logger.error(
                        f"Failed to schedule task {task.id} ({task.task_name}): {e}"
                    )

        logger.info(
            f"SchedulerService initialized successfully. "
            f"Scheduled {scheduled_count}/{len(enabled_tasks)} enabled tasks."
        )

    async def shutdown(self) -> None:
        """Shutdown the scheduler gracefully.

        This method should be called during application shutdown.
        """
        logger.info("Shutting down SchedulerService...")
        self.scheduler.shutdown(wait=True)
        logger.info("SchedulerService shutdown complete.")

    async def schedule_task(self, task: ScheduledTask) -> str:
        """Schedule a task in the scheduler.

        This is a public method for scheduling tasks. It validates the task
        and adds it to the APScheduler.

        Args:
            task: The ScheduledTask to schedule

        Returns:
            The APScheduler job ID

        Raises:
            ValueError: If the task is disabled or has invalid cron expression
            Exception: If scheduling fails
        """
        if not task.is_enabled:
            raise ValueError(f"Task {task.id} is disabled and cannot be scheduled")

        return await self._schedule_task(task)

    async def _schedule_task(self, task: ScheduledTask) -> str:
        """Internal method to add a task to the scheduler.

        Args:
            task: The ScheduledTask to schedule

        Returns:
            The APScheduler job ID

        Raises:
            Exception: If scheduling fails
        """
        job_id = f"task_{task.id}"

        # Check if job already exists
        if self.scheduler.get_job(job_id):
            logger.warning(f"Job {job_id} already exists, removing it first")
            self.scheduler.remove_job(job_id)

        # Create cron trigger from cron expression
        # Support 5, 6, or 7 part cron expressions:
        # 5 parts: minute hour day month weekday
        # 6 parts: second minute hour day month weekday
        # 7 parts: second minute hour day month weekday year
        try:
            trigger = parse_cron_expression(task.cron_expression, timezone="UTC")
        except Exception as e:
            raise ValueError(f"Invalid cron expression '{task.cron_expression}': {e}")

        # Add the job to the scheduler
        self.scheduler.add_job(
            func=_job_executor_wrapper,
            trigger=trigger,
            id=job_id,
            args=[task.id],
            name=task.task_name,
            replace_existing=True,
        )

        logger.info(
            f"Scheduled task {task.id} ({task.task_name}) with cron '{task.cron_expression}'"
        )

        return job_id

    async def unschedule_task(self, task_id: int) -> bool:
        """Remove a task from the scheduler.

        Args:
            task_id: ID of the task to unschedule

        Returns:
            True if task was unscheduled, False if job not found
        """
        job_id = f"task_{task_id}"

        job = self.scheduler.get_job(job_id)
        if job is None:
            return False

        self.scheduler.remove_job(job_id)
        logger.info(f"Unscheduled task {task_id}")

        return True

    async def reschedule_task(self, task: ScheduledTask) -> str:
        """Reschedule a task with updated configuration.

        Args:
            task: The ScheduledTask to reschedule

        Returns:
            The APScheduler job ID

        Raises:
            ValueError: If the task is disabled
            Exception: If rescheduling fails
        """
        if not task.is_enabled:
            await self.unschedule_task(task.id)
            raise ValueError(f"Task {task.id} is disabled and cannot be scheduled")

        # Remove existing job if present
        await self.unschedule_task(task.id)

        # Schedule with new configuration
        return await self._schedule_task(task)

    async def reschedule_task_safely(self, old_task: ScheduledTask, new_task: ScheduledTask) -> str:
        """Reschedule with automatic rollback on failure.

        This method atomically replaces the old job with the new one.
        If the new job fails to schedule, the old job configuration is restored.

        Args:
            old_task: The current task with its existing configuration
            new_task: The new task configuration to schedule

        Returns:
            The APScheduler job ID

        Raises:
            ValueError: If the task cannot be scheduled
            Exception: If scheduling fails (after attempting to restore old job)
        """
        job_id = f"task_{new_task.id}"

        # Backup old job configuration if it exists
        old_job = self.scheduler.get_job(job_id)
        old_trigger = old_job.trigger if old_job else None
        old_name = old_job.name if old_job else old_task.task_name

        try:
            # Validate and create new trigger
            trigger = parse_cron_expression(new_task.cron_expression, timezone="UTC")
            # Atomically replace existing job with new configuration
            self.scheduler.add_job(
                func=_job_executor_wrapper,
                trigger=trigger,
                id=job_id,
                args=[new_task.id],
                name=new_task.task_name,
                replace_existing=True,
            )
            logger.info(
                f"Safely rescheduled task {new_task.id} ({new_task.task_name}) "
                f"with cron '{new_task.cron_expression}'"
            )
            return job_id
        except Exception as e:
            # Restore old job if it existed
            if old_trigger is not None:
                try:
                    self.scheduler.add_job(
                        func=_job_executor_wrapper,
                        trigger=old_trigger,
                        id=job_id,
                        args=[old_task.id],
                        name=old_name,
                        replace_existing=True,
                    )
                    logger.info(
                        f"Restored old scheduler job for task {old_task.id} "
                        f"after failed reschedule attempt"
                    )
                except Exception as restore_error:
                    logger.exception(
                        f"Failed to restore old scheduler job for task {old_task.id}: {restore_error}"
                    )
            raise

    def validate_task_schedule(self, task: ScheduledTask) -> None:
        """Validate that a task configuration is valid.

        This checks if the cron expression is valid, regardless of whether
        the task is enabled or disabled.

        Args:
            task: The ScheduledTask to validate

        Raises:
            ValueError: If the cron expression is invalid
        """
        try:
            parse_cron_expression(task.cron_expression, timezone="UTC")
        except Exception as e:
            raise ValueError(f"Invalid cron expression '{task.cron_expression}': {e}")

    async def _execute_scheduled_task(self, task_id: int) -> None:
        """Execute a scheduled task.

        This method is called by APScheduler when a scheduled task is triggered.
        It retrieves the task from the database and executes it via TaskExecutor.

        Args:
            task_id: ID of the task to execute
        """
        logger.info(f"Executing scheduled task {task_id}")

        async with self.db_session_factory() as session:
            repo = ScheduledTaskRepository(session)
            task = await repo.get_by_id(task_id)

            if task is None:
                logger.error(f"Task {task_id} not found in database")
                return

            if not task.is_enabled:
                logger.warning(f"Task {task_id} is disabled, skipping execution")
                return

            try:
                result = await self.executor.execute_task(
                    task=task,
                    session_factory=self.db_session_factory,
                    triggered_by="scheduler",
                )

                if result["success"]:
                    logger.info(
                        f"Task {task_id} ({task.task_name}) completed successfully. "
                        f"Execution ID: {result['execution_id']}"
                    )
                else:
                    logger.error(
                        f"Task {task_id} ({task.task_name}) failed. "
                        f"Status: {result['status']}, "
                        f"Error: {result.get('error_message')}"
                    )

            except Exception as e:
                logger.exception(f"Unexpected error executing task {task_id}: {e}")

    async def trigger_task_manually(self, task_id: int) -> Dict[str, Any]:
        """Manually trigger a task execution.

        Args:
            task_id: ID of the task to trigger

        Returns:
            Dictionary containing execution results

        Raises:
            ValueError: If task not found
        """
        async with self.db_session_factory() as session:
            repo = ScheduledTaskRepository(session)
            task = await repo.get_by_id(task_id)

            if task is None:
                raise ValueError(f"Task {task_id} not found")

        logger.info(f"Manually triggering task {task_id} ({task.task_name})")

        return await self.executor.execute_task(
            task=task,
            session_factory=self.db_session_factory,
            triggered_by="manual",
        )

    def get_scheduled_jobs(self) -> List[Dict[str, Any]]:
        """Get information about all scheduled jobs.

        Returns:
            List of dictionaries containing job information
        """
        jobs = self.scheduler.get_jobs()

        return [
            {
                "id": job.id,
                "name": job.name,
                "next_run_time": (
                    job.next_run_time.isoformat() if job.next_run_time else None
                ),
                "trigger": str(job.trigger),
            }
            for job in jobs
        ]

    def get_job_info(self, task_id: int) -> Optional[Dict[str, Any]]:
        """Get information about a specific scheduled job.

        Args:
            task_id: ID of the task

        Returns:
            Dictionary containing job information or None if not found
        """
        job_id = f"task_{task_id}"
        job = self.scheduler.get_job(job_id)

        if job is None:
            return None

        return {
            "id": job.id,
            "name": job.name,
            "next_run_time": (
                job.next_run_time.isoformat() if job.next_run_time else None
            ),
            "trigger": str(job.trigger),
        }

    async def pause_task(self, task_id: int) -> bool:
        """Pause a scheduled task.

        Args:
            task_id: ID of the task to pause

        Returns:
            True if paused, False if job not found
        """
        job_id = f"task_{task_id}"
        job = self.scheduler.get_job(job_id)

        if job is None:
            return False

        self.scheduler.pause_job(job_id)
        logger.info(f"Paused task {task_id}")

        return True

    async def resume_task(self, task_id: int) -> bool:
        """Resume a paused scheduled task.

        Args:
            task_id: ID of the task to resume

        Returns:
            True if resumed, False if job not found
        """
        job_id = f"task_{task_id}"
        job = self.scheduler.get_job(job_id)

        if job is None:
            return False

        self.scheduler.resume_job(job_id)
        logger.info(f"Resumed task {task_id}")

        return True

    def is_scheduler_running(self) -> bool:
        """Check if the scheduler is running.

        Returns:
            True if scheduler is running, False otherwise
        """
        return self.scheduler.running

    def get_running_tasks(self) -> list[int]:
        """Get list of currently running task IDs.

        Returns:
            List of running task IDs
        """
        return self.executor.get_running_tasks()

    def get_running_task_count(self) -> int:
        """Get the number of currently running tasks.

        Returns:
            Number of running tasks
        """
        return self.executor.get_running_task_count()

    async def cancel_running_task(self, task_id: int) -> bool:
        """Cancel a running task.

        Args:
            task_id: ID of the task to cancel

        Returns:
            True if task was cancelled, False if not found or already completed
        """
        return await self.executor.cancel_running_task(task_id)
