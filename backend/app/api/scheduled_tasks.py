"""
Scheduled Tasks API Routes

This module provides REST API endpoints for managing scheduled tasks
that support cron-based scheduling for data synchronization and rule execution.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user, require_admin
from app.models.user import User
from app.services.scheduler_service import parse_cron_expression
from app.schemas.scheduled_task import (
    ScheduledTaskCreate,
    ScheduledTaskUpdate,
    ScheduledTaskResponse,
    ScheduledTaskListResponse,
    TaskExecutionResponse,
    TaskExecutionListResponse,
    ManualTriggerResponse,
    CronValidationResponse,
    CronValidationRequest,
)
from app.models.scheduled_task import ScheduledTask
from app.repositories.scheduled_task_repository import (
    ScheduledTaskRepository,
    TaskExecutionRepository,
)

router = APIRouter(prefix="/scheduled-tasks", tags=["scheduled-tasks"])


@router.post(
    "/", response_model=ScheduledTaskResponse, status_code=status.HTTP_201_CREATED
)
async def create_scheduled_task(
    task_data: ScheduledTaskCreate,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a new scheduled task."""
    repo = ScheduledTaskRepository(db)

    # Check if task already exists for the same type and target
    existing = await repo.get_by_target(task_data.task_type, task_data.target_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Task already exists for {task_data.task_type}:{task_data.target_id}",
        )

    # Validate cron expression before creating the task
    try:
        parse_cron_expression(task_data.cron_expression)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid cron expression: {e}",
        )

    # Create the task
    task = ScheduledTask(**task_data.model_dump())
    created = await repo.create(task)

    # Schedule the task if it's enabled
    if created.is_enabled:
        scheduler_service = request.app.state.scheduler_service
        try:
            await scheduler_service.schedule_task(created)
        except ValueError as e:
            # Cron validation failed during scheduling - rollback and return error
            await repo.delete(created.id)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to schedule task: {e}",
            )
        except Exception as e:
            # Other scheduling failures - rollback and return error
            await repo.delete(created.id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to schedule task: {e}",
            )

    return created


@router.get("/", response_model=ScheduledTaskListResponse)
async def list_scheduled_tasks(
    task_type: Optional[str] = Query(None, description="Filter by task type"),
    is_enabled: Optional[bool] = Query(None, description="Filter by enabled status"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all scheduled tasks with optional filters."""
    repo = ScheduledTaskRepository(db)
    tasks = await repo.list_tasks(
        task_type=task_type, is_enabled=is_enabled, limit=limit, offset=offset
    )

    # Get total count
    all_tasks = await repo.list_tasks(
        task_type=task_type, is_enabled=is_enabled, limit=10000, offset=0
    )

    return ScheduledTaskListResponse(items=tasks, total=len(all_tasks))


@router.get("/{task_id}", response_model=ScheduledTaskResponse)
async def get_scheduled_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a scheduled task by ID."""
    repo = ScheduledTaskRepository(db)
    task = await repo.get_by_id(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )
    return task


@router.put("/{task_id}", response_model=ScheduledTaskResponse)
async def update_scheduled_task(
    task_id: int,
    updates: ScheduledTaskUpdate,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update a scheduled task."""
    # Build update data with only non-None values
    update_data = {k: v for k, v in updates.model_dump().items() if v is not None}

    if not update_data:
        # No updates provided
        repo = ScheduledTaskRepository(db)
        task = await repo.get_by_id(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found",
            )
        return task

    # Validate cron expression if provided
    if "cron_expression" in update_data:
        try:
            parse_cron_expression(update_data["cron_expression"])
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid cron expression: {e}",
            )

    repo = ScheduledTaskRepository(db)
    task = await repo.update(task_id, update_data)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )

    # Reschedule the task
    scheduler_service = request.app.state.scheduler_service
    try:
        if task.is_enabled:
            await scheduler_service.reschedule_task(task)
        else:
            await scheduler_service.unschedule_task(task_id)
    except ValueError as e:
        # Cron validation failed during rescheduling
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to reschedule task: {e}",
        )
    except Exception as e:
        # Other scheduling failures
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reschedule task: {e}",
        )

    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scheduled_task(
    task_id: int,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete a scheduled task."""
    repo = ScheduledTaskRepository(db)
    success = await repo.delete(task_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )

    # Unschedule from scheduler
    scheduler_service = request.app.state.scheduler_service
    await scheduler_service.unschedule_task(task_id)

    return None


@router.post("/{task_id}/pause", response_model=dict)
async def pause_scheduled_task(
    task_id: int,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Pause a scheduled task."""
    repo = ScheduledTaskRepository(db)
    task = await repo.get_by_id(task_id)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )

    # Update to disabled
    await repo.update(task_id, {"is_enabled": False})

    # Pause in scheduler
    scheduler_service = request.app.state.scheduler_service
    await scheduler_service.pause_task(task_id)

    return {"status": "paused", "task_id": task_id}


@router.post("/{task_id}/resume", response_model=dict)
async def resume_scheduled_task(
    task_id: int,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Resume a paused scheduled task."""
    repo = ScheduledTaskRepository(db)
    task = await repo.get_by_id(task_id)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )

    # Update to enabled
    await repo.update(task_id, {"is_enabled": True})

    # Resume in scheduler
    scheduler_service = request.app.state.scheduler_service
    await scheduler_service.resume_task(task_id)

    return {"status": "resumed", "task_id": task_id}


@router.post("/{task_id}/trigger", response_model=ManualTriggerResponse)
async def trigger_scheduled_task(
    task_id: int,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger a task execution.

    Note: This endpoint requires the scheduler service to be initialized.
    For now, it returns a mock response.
    """
    repo = ScheduledTaskRepository(db)
    task = await repo.get_by_id(task_id)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )

    # Trigger via scheduler service
    scheduler_service = request.app.state.scheduler_service
    try:
        result = await scheduler_service.trigger_task_manually(task_id)
        return ManualTriggerResponse(
            execution_id=result.get("execution_id", 0),
            task_id=task_id,
            status=result.get("status", "pending"),
            message="Task triggered successfully",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger task: {str(e)}",
        )


@router.get("/{task_id}/status", response_model=dict)
async def get_scheduled_task_status(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current status of a scheduled task."""
    repo = ScheduledTaskRepository(db)
    task = await repo.get_by_id(task_id)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )

    return {
        "task_id": task_id,
        "task_name": task.task_name,
        "is_enabled": task.is_enabled,
        "cron_expression": task.cron_expression,
        "status": "enabled" if task.is_enabled else "disabled",
    }


@router.get("/{task_id}/executions", response_model=TaskExecutionListResponse)
async def get_task_executions(
    task_id: int,
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get execution history for a specific task."""
    repo = ScheduledTaskRepository(db)
    task = await repo.get_by_id(task_id)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )

    exec_repo = TaskExecutionRepository(db)
    executions = await exec_repo.list_by_task(task_id, limit=limit, offset=offset)

    # Get total count
    all_executions = await exec_repo.list_by_task(task_id, limit=10000, offset=0)

    return TaskExecutionListResponse(items=executions, total=len(all_executions))


@router.post("/validate-cron", response_model=CronValidationResponse)
async def validate_cron_expression(request: CronValidationRequest):
    """Validate a cron expression using the same parser as the scheduler."""
    try:
        # Use the actual parser to ensure validation matches what the scheduler accepts
        parse_cron_expression(request.cron_expression)
        return CronValidationResponse(
            is_valid=True,
            message="Cron expression is valid",
            next_run_times=None,
        )
    except ValueError as e:
        return CronValidationResponse(
            is_valid=False,
            message=str(e),
            next_run_times=None,
        )
    except Exception as e:
        return CronValidationResponse(
            is_valid=False,
            message=f"Error validating cron expression: {str(e)}",
            next_run_times=None,
        )
