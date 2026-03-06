# backend/app/models/scheduled_task.py
"""
Scheduled task models for the scheduler feature.

This module defines the ORM models for managing scheduled tasks and their executions.
Supports cron-based scheduling for data synchronization and rule execution tasks.
"""

from datetime import datetime, timezone
from sqlalchemy import String, Boolean, Integer, Text, ForeignKey, DateTime, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class ScheduledTask(Base):
    """Represents a scheduled task with cron-based scheduling.

    Supports scheduling of various task types:
    - 'sync': Data product synchronization tasks
    - 'rule': Business rule execution tasks

    Attributes:
        id: Primary key
        task_type: Type of task ('sync' or 'rule')
        task_name: Human-readable name for the task
        target_id: ID of the target entity (data_product_id for sync, rule_id for rule)
        cron_expression: Cron expression for scheduling (e.g., "0 0 * * *")
        is_enabled: Whether the task is active
        timeout_seconds: Maximum execution time before timeout
        max_retries: Maximum number of retry attempts on failure
        retry_interval_seconds: Delay between retry attempts
        priority: Execution priority (higher values execute first)
        description: Optional description of the task
        created_at: Timestamp when the task was created
        updated_at: Timestamp when the task was last updated
    """

    __tablename__ = "scheduled_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_type: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # 'sync' | 'rule'
    task_name: Mapped[str] = mapped_column(String(255), nullable=False)
    target_id: Mapped[int] = mapped_column(Integer, nullable=False)  # FK to data_products.id or rules.id
    cron_expression: Mapped[str] = mapped_column(String(100), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=300, nullable=False)  # 5 minutes default
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    retry_interval_seconds: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )

    # Relationship to executions
    executions: Mapped[list["TaskExecution"]] = relationship(
        "TaskExecution",
        back_populates="scheduled_task",
        cascade="all, delete-orphan",
        order_by="TaskExecution.started_at.desc()",
    )

    __table_args__ = (
        Index("idx_scheduled_tasks_type_target", "task_type", "target_id"),
    )

    def __repr__(self) -> str:
        return f"<ScheduledTask(id={self.id}, name='{self.task_name}', type='{self.task_type}', enabled={self.is_enabled})>"


class TaskExecution(Base):
    """Represents a single execution of a scheduled task.

    Tracks the execution history, status, and results of scheduled tasks.
    Includes retry information and error tracking for troubleshooting.

    Attributes:
        id: Primary key
        task_id: Foreign key to the scheduled task
        status: Current execution status ('pending'|'running'|'completed'|'failed'|'timeout')
        started_at: Timestamp when the execution started
        completed_at: Timestamp when the execution completed (None if still running)
        duration_seconds: Total execution duration in seconds
        result_data: JSONB data containing execution results
        error_message: Error message if the execution failed
        error_type: Type of error that occurred
        retry_count: Number of retry attempts made
        is_retry: Whether this execution is a retry attempt
        triggered_by: How the execution was triggered ('cron'|'manual'|'retry')
    """

    __tablename__ = "task_executions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("scheduled_tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # 'pending' | 'running' | 'completed' | 'failed' | 'timeout'
    started_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), index=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    result_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_retry: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    triggered_by: Mapped[str] = mapped_column(String(20), default="cron", nullable=False)  # 'cron' | 'manual' | 'retry'

    # Relationship to scheduled task
    scheduled_task: Mapped["ScheduledTask"] = relationship(
        "ScheduledTask", back_populates="executions"
    )

    __table_args__ = (
        Index("idx_task_executions_task_status", "task_id", "status"),
        Index("idx_task_executions_started_at", "started_at"),
    )

    def __repr__(self) -> str:
        return f"<TaskExecution(id={self.id}, task_id={self.task_id}, status='{self.status}', started_at={self.started_at})>"
