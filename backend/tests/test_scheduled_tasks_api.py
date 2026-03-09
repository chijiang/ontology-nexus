"""
Integration tests for the Scheduled Tasks API endpoints.

This module tests the REST API endpoints for managing scheduled tasks,
including CRUD operations, pause/resume functionality, manual triggers,
and execution history retrieval.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scheduled_task import ScheduledTask
from app.repositories.scheduled_task_repository import ScheduledTaskRepository


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
async def admin_headers(async_client: AsyncClient):
    """Create admin auth headers for testing."""
    from app.main import app
    from app.api.deps import get_current_user, require_admin
    from app.models.user import User

    mock_user = User(
        id=1,
        username="testadmin",
        email="admin@example.com",
        is_admin=True,
        approval_status="approved",
    )

    def mock_get_current_user():
        return mock_user

    def mock_require_admin():
        return mock_user

    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[require_admin] = mock_require_admin
    yield {"Authorization": "Bearer mock-admin-token"}
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(require_admin, None)


@pytest.fixture
async def sample_task(db: AsyncSession):
    """Create a sample scheduled task for testing."""
    repo = ScheduledTaskRepository(db)
    task = ScheduledTask(
        task_type="sync",
        task_name="Test Sync Task",
        target_id=1,
        cron_expression="*/5 * * * *",
        is_enabled=True,
        timeout_seconds=300,
        max_retries=3,
        retry_interval_seconds=60,
        priority=50,
        description="Test task for API integration tests",
    )
    created = await repo.create(task)
    yield created
    # Cleanup
    await repo.delete(created.id)


@pytest.fixture
async def multiple_tasks(db: AsyncSession):
    """Create multiple sample tasks for listing tests."""
    repo = ScheduledTaskRepository(db)
    tasks = []
    cron_expressions = [
        ("*/5 * * * *", "Every 5 minutes"),
        ("0 * * * *", "Every hour"),
        ("0 0 * * *", "Daily at midnight"),
    ]

    for cron_expr, desc in cron_expressions:
        task = ScheduledTask(
            task_type="sync",
            task_name=f"Test Task {desc}",
            target_id=len(tasks) + 1,
            cron_expression=cron_expr,
            is_enabled=True,
        )
        created = await repo.create(task)
        tasks.append(created)

    yield tasks

    # Cleanup
    for task in tasks:
        await repo.delete(task.id)


# ============================================================================
# Create Scheduled Task Tests
# ============================================================================


@pytest.mark.asyncio
async def test_create_scheduled_task(async_client: AsyncClient, admin_headers, db: AsyncSession):
    """Test creating a new scheduled task."""
    response = await async_client.post(
        "/api/scheduled-tasks/",
        json={
            "task_type": "sync",
            "task_name": "New Sync Task",
            "target_id": 100,
            "cron_expression": "*/10 * * * *",
            "is_enabled": True,
            "timeout_seconds": 600,
            "max_retries": 5,
            "priority": 75,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["task_name"] == "New Sync Task"
    assert data["task_type"] == "sync"
    assert data["target_id"] == 100
    assert data["cron_expression"] == "*/10 * * * *"
    assert data["is_enabled"] is True
    assert data["timeout_seconds"] == 600
    assert data["max_retries"] == 5
    assert data["priority"] == 75
    assert "id" in data
    assert "created_at" in data

    # Cleanup
    repo = ScheduledTaskRepository(db)
    await repo.delete(data["id"])


@pytest.mark.asyncio
async def test_create_task_with_invalid_cron(async_client: AsyncClient, admin_headers):
    """Test creating a task with invalid cron expression fails."""
    response = await async_client.post(
        "/api/scheduled-tasks/",
        json={
            "task_type": "sync",
            "task_name": "Invalid Task",
            "target_id": 1,
            "cron_expression": "* * * *",  # Only 4 parts
        },
    )
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_create_task_duplicate_target(async_client: AsyncClient, admin_headers, sample_task: ScheduledTask):
    """Test creating duplicate task for same target fails."""
    response = await async_client.post(
        "/api/scheduled-tasks/",
        json={
            "task_type": sample_task.task_type,
            "task_name": "Duplicate Task",
            "target_id": sample_task.target_id,  # Same target_id
            "cron_expression": "0 * * * *",
        },
    )
    assert response.status_code == 409  # Conflict
    assert "already exists" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_task_rule_type(async_client: AsyncClient, admin_headers, db: AsyncSession):
    """Test creating a rule-type scheduled task."""
    response = await async_client.post(
        "/api/scheduled-tasks/",
        json={
            "task_type": "rule",
            "task_name": "Rule Execution Task",
            "target_id": 5,
            "cron_expression": "0 9 * * 1",  # Mondays at 9 AM
            "is_enabled": False,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["task_type"] == "rule"
    assert data["is_enabled"] is False

    # Cleanup
    repo = ScheduledTaskRepository(db)
    await repo.delete(data["id"])


@pytest.mark.asyncio
async def test_create_task_with_all_fields(async_client: AsyncClient, admin_headers, db: AsyncSession):
    """Test creating a task with all optional fields."""
    response = await async_client.post(
        "/api/scheduled-tasks/",
        json={
            "task_type": "sync",
            "task_name": "Complete Task",
            "target_id": 1,
            "cron_expression": "0 0 * * *",
            "is_enabled": True,
            "timeout_seconds": 1200,
            "max_retries": 5,
            "retry_interval_seconds": 120,
            "priority": 100,
            "description": "A complete task with all fields specified",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["timeout_seconds"] == 1200
    assert data["max_retries"] == 5
    assert data["retry_interval_seconds"] == 120
    assert data["priority"] == 100
    assert data["description"] == "A complete task with all fields specified"

    # Cleanup
    repo = ScheduledTaskRepository(db)
    await repo.delete(data["id"])


@pytest.mark.asyncio
async def test_create_task_without_auth(async_client: AsyncClient):
    """Test creating a task without authentication fails."""
    response = await async_client.post(
        "/api/scheduled-tasks/",
        json={
            "task_type": "sync",
            "task_name": "Unauthorized Task",
            "target_id": 1,
            "cron_expression": "0 * * * *",
        },
    )
    assert response.status_code == 401  # Unauthorized


# ============================================================================
# List Scheduled Tasks Tests
# ============================================================================


@pytest.mark.asyncio
async def test_list_scheduled_tasks(async_client: AsyncClient, admin_headers, multiple_tasks: list[ScheduledTask]):
    """Test listing all scheduled tasks."""
    response = await async_client.get("/api/scheduled-tasks/")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert len(data["items"]) >= len(multiple_tasks)


@pytest.mark.asyncio
async def test_list_tasks_with_type_filter(async_client: AsyncClient, admin_headers, multiple_tasks: list[ScheduledTask]):
    """Test filtering tasks by type."""
    response = await async_client.get("/api/scheduled-tasks/?task_type=sync")
    assert response.status_code == 200
    data = response.json()
    assert all(task["task_type"] == "sync" for task in data["items"])


@pytest.mark.asyncio
async def test_list_tasks_with_enabled_filter(async_client: AsyncClient, admin_headers, multiple_tasks: list[ScheduledTask]):
    """Test filtering tasks by enabled status."""
    response = await async_client.get("/api/scheduled-tasks/?is_enabled=true")
    assert response.status_code == 200
    data = response.json()
    assert all(task["is_enabled"] is True for task in data["items"])


@pytest.mark.asyncio
async def test_list_tasks_with_pagination(async_client: AsyncClient, admin_headers, multiple_tasks: list[ScheduledTask]):
    """Test pagination of tasks list."""
    # Get first page
    response = await async_client.get("/api/scheduled-tasks/?limit=2&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) <= 2


@pytest.mark.asyncio
async def test_list_tasks_without_auth(async_client: AsyncClient):
    """Test listing tasks without authentication fails."""
    response = await async_client.get("/api/scheduled-tasks/")
    assert response.status_code == 401  # Unauthorized


# ============================================================================
# Get Scheduled Task by ID Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_task_by_id(async_client: AsyncClient, admin_headers, sample_task: ScheduledTask):
    """Test retrieving a task by ID."""
    response = await async_client.get(f"/api/scheduled-tasks/{sample_task.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == sample_task.id
    assert data["task_name"] == sample_task.task_name
    assert data["cron_expression"] == sample_task.cron_expression


@pytest.mark.asyncio
async def test_get_task_not_found(async_client: AsyncClient, admin_headers):
    """Test retrieving non-existent task returns 404."""
    response = await async_client.get("/api/scheduled-tasks/99999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_task_without_auth(async_client: AsyncClient):
    """Test getting a task without authentication fails."""
    response = await async_client.get("/api/scheduled-tasks/1")
    assert response.status_code == 401  # Unauthorized


# ============================================================================
# Update Scheduled Task Tests
# ============================================================================


@pytest.mark.asyncio
async def test_update_task_name(async_client: AsyncClient, admin_headers, sample_task: ScheduledTask):
    """Test updating task name."""
    new_name = "Updated Task Name"
    response = await async_client.put(
        f"/api/scheduled-tasks/{sample_task.id}",
        json={"task_name": new_name},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["task_name"] == new_name
    assert data["id"] == sample_task.id


@pytest.mark.asyncio
async def test_update_task_cron_expression(async_client: AsyncClient, admin_headers, sample_task: ScheduledTask):
    """Test updating task cron expression."""
    new_cron = "0 */2 * * *"
    response = await async_client.put(
        f"/api/scheduled-tasks/{sample_task.id}",
        json={"cron_expression": new_cron},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["cron_expression"] == new_cron


@pytest.mark.asyncio
async def test_update_task_multiple_fields(async_client: AsyncClient, admin_headers, sample_task: ScheduledTask):
    """Test updating multiple task fields."""
    response = await async_client.put(
        f"/api/scheduled-tasks/{sample_task.id}",
        json={
            "task_name": "Updated Name",
            "is_enabled": False,
            "priority": 90,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["task_name"] == "Updated Name"
    assert data["is_enabled"] is False
    assert data["priority"] == 90


@pytest.mark.asyncio
async def test_update_task_with_invalid_values(async_client: AsyncClient, admin_headers, sample_task: ScheduledTask):
    """Test updating task with invalid values fails."""
    response = await async_client.put(
        f"/api/scheduled-tasks/{sample_task.id}",
        json={"timeout_seconds": 5000},  # Exceeds max of 3600
    )
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_update_task_not_found(async_client: AsyncClient, admin_headers):
    """Test updating non-existent task returns 404."""
    response = await async_client.put(
        "/api/scheduled-tasks/99999",
        json={"task_name": "New Name"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_task_no_changes(async_client: AsyncClient, admin_headers, sample_task: ScheduledTask):
    """Test updating task with no changes returns current task."""
    response = await async_client.put(
        f"/api/scheduled-tasks/{sample_task.id}",
        json={},  # No updates
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == sample_task.id


@pytest.mark.asyncio
async def test_update_task_without_auth(async_client: AsyncClient):
    """Test updating a task without authentication fails."""
    response = await async_client.put(
        "/api/scheduled-tasks/1",
        json={"task_name": "Hacked Name"},
    )
    assert response.status_code == 401  # Unauthorized


# ============================================================================
# Delete Scheduled Task Tests
# ============================================================================


@pytest.mark.asyncio
async def test_delete_task(async_client: AsyncClient, admin_headers, db: AsyncSession):
    """Test deleting a task."""
    # First create a task
    repo = ScheduledTaskRepository(db)
    task = ScheduledTask(
        task_type="sync",
        task_name="To Delete",
        target_id=999,
        cron_expression="* * * * *",
    )
    created = await repo.create(task)

    # Delete it
    response = await async_client.delete(f"/api/scheduled-tasks/{created.id}")
    assert response.status_code == 204

    # Verify deleted
    get_response = await async_client.get(f"/api/scheduled-tasks/{created.id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_task_not_found(async_client: AsyncClient, admin_headers):
    """Test deleting non-existent task returns 404."""
    response = await async_client.delete("/api/scheduled-tasks/99999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_task_without_auth(async_client: AsyncClient):
    """Test deleting a task without authentication fails."""
    response = await async_client.delete("/api/scheduled-tasks/1")
    assert response.status_code == 401  # Unauthorized


# ============================================================================
# Pause/Resume Task Tests
# ============================================================================


@pytest.mark.asyncio
async def test_pause_task(async_client: AsyncClient, admin_headers, sample_task: ScheduledTask):
    """Test pausing a task."""
    response = await async_client.post(f"/api/scheduled-tasks/{sample_task.id}/pause")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "paused"
    assert data["task_id"] == sample_task.id

    # Verify task is disabled
    get_response = await async_client.get(f"/api/scheduled-tasks/{sample_task.id}")
    assert get_response.json()["is_enabled"] is False


@pytest.mark.asyncio
async def test_resume_task(async_client: AsyncClient, admin_headers, sample_task: ScheduledTask):
    """Test resuming a paused task."""
    # First pause
    await async_client.post(f"/api/scheduled-tasks/{sample_task.id}/pause")

    # Then resume
    response = await async_client.post(
        f"/api/scheduled-tasks/{sample_task.id}/resume"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "resumed"
    assert data["task_id"] == sample_task.id

    # Verify task is enabled
    get_response = await async_client.get(f"/api/scheduled-tasks/{sample_task.id}")
    assert get_response.json()["is_enabled"] is True


@pytest.mark.asyncio
async def test_pause_task_not_found(async_client: AsyncClient, admin_headers):
    """Test pausing non-existent task returns 404."""
    response = await async_client.post("/api/scheduled-tasks/99999/pause")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_resume_task_not_found(async_client: AsyncClient, admin_headers):
    """Test resuming non-existent task returns 404."""
    response = await async_client.post("/api/scheduled-tasks/99999/resume")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_pause_task_without_auth(async_client: AsyncClient):
    """Test pausing a task without authentication fails."""
    response = await async_client.post("/api/scheduled-tasks/1/pause")
    assert response.status_code == 401  # Unauthorized


# ============================================================================
# Trigger Task Tests
# ============================================================================


@pytest.mark.asyncio
async def test_trigger_task(async_client: AsyncClient, admin_headers, sample_task: ScheduledTask):
    """Test manually triggering a task."""
    response = await async_client.post(
        f"/api/scheduled-tasks/{sample_task.id}/trigger"
    )
    assert response.status_code == 200
    data = response.json()
    assert "execution_id" in data
    assert data["task_id"] == sample_task.id
    assert data["status"] in ["pending", "running"]


@pytest.mark.asyncio
async def test_trigger_task_not_found(async_client: AsyncClient, admin_headers):
    """Test triggering non-existent task returns 404."""
    response = await async_client.post("/api/scheduled-tasks/99999/trigger")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_trigger_task_without_auth(async_client: AsyncClient):
    """Test triggering a task without authentication fails."""
    response = await async_client.post("/api/scheduled-tasks/1/trigger")
    assert response.status_code == 401  # Unauthorized


# ============================================================================
# Get Task Status Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_task_status(async_client: AsyncClient, admin_headers, sample_task: ScheduledTask):
    """Test getting task status."""
    response = await async_client.get(f"/api/scheduled-tasks/{sample_task.id}/status")
    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == sample_task.id
    assert data["task_name"] == sample_task.task_name
    assert "status" in data
    assert data["status"] in ["enabled", "disabled"]


@pytest.mark.asyncio
async def test_get_task_status_not_found(async_client: AsyncClient, admin_headers):
    """Test getting status of non-existent task returns 404."""
    response = await async_client.get("/api/scheduled-tasks/99999/status")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_task_status_without_auth(async_client: AsyncClient):
    """Test getting task status without authentication fails."""
    response = await async_client.get("/api/scheduled-tasks/1/status")
    assert response.status_code == 401  # Unauthorized


# ============================================================================
# Get Task Executions Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_task_executions(async_client: AsyncClient, admin_headers, sample_task: ScheduledTask):
    """Test getting task execution history."""
    response = await async_client.get(
        f"/api/scheduled-tasks/{sample_task.id}/executions"
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)


@pytest.mark.asyncio
async def test_get_task_executions_with_pagination(async_client: AsyncClient, admin_headers, sample_task: ScheduledTask):
    """Test pagination of task executions."""
    response = await async_client.get(
        f"/api/scheduled-tasks/{sample_task.id}/executions?limit=10&offset=0"
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) <= 10


@pytest.mark.asyncio
async def test_get_task_executions_not_found(async_client: AsyncClient, admin_headers):
    """Test getting executions for non-existent task returns 404."""
    response = await async_client.get("/api/scheduled-tasks/99999/executions")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_task_executions_without_auth(async_client: AsyncClient):
    """Test getting task executions without authentication fails."""
    response = await async_client.get("/api/scheduled-tasks/1/executions")
    assert response.status_code == 401  # Unauthorized


# ============================================================================
# Validate Cron Expression Tests
# ============================================================================


@pytest.mark.asyncio
async def test_validate_cron_valid(async_client: AsyncClient):
    """Test validating a valid cron expression."""
    response = await async_client.post(
        "/api/scheduled-tasks/validate-cron",
        json={"cron_expression": "*/5 * * * *"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_valid"] is True
    assert "valid" in data["message"].lower()


@pytest.mark.asyncio
async def test_validate_cron_invalid(async_client: AsyncClient):
    """Test validating an invalid cron expression."""
    response = await async_client.post(
        "/api/scheduled-tasks/validate-cron",
        json={"cron_expression": "* * * *"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_valid"] is False
    assert "5-7 parts" in data["message"]


@pytest.mark.asyncio
async def test_validate_cron_empty(async_client: AsyncClient):
    """Test validating an empty cron expression."""
    response = await async_client.post(
        "/api/scheduled-tasks/validate-cron",
        json={"cron_expression": ""},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_valid"] is False


@pytest.mark.asyncio
async def test_validate_cron_extended(async_client: AsyncClient):
    """Test validating extended cron expressions with seconds."""
    response = await async_client.post(
        "/api/scheduled-tasks/validate-cron",
        json={"cron_expression": "*/30 * * * * *"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_valid"] is True


@pytest.mark.asyncio
async def test_validate_cron_with_year(async_client: AsyncClient):
    """Test validating 7-part cron expression with year."""
    response = await async_client.post(
        "/api/scheduled-tasks/validate-cron",
        json={"cron_expression": "0 0 0 1 1 * 2026"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_valid"] is True


@pytest.mark.asyncio
async def test_validate_cron_invalid_field(async_client: AsyncClient):
    """Test validating cron with invalid field value."""
    response = await async_client.post(
        "/api/scheduled-tasks/validate-cron",
        json={"cron_expression": "99 * * * *"},  # Invalid minute (99)
    )
    assert response.status_code == 200
    data = response.json()
    # CronTrigger should reject invalid field values
    assert data["is_valid"] is False


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


@pytest.mark.asyncio
async def test_create_task_with_minimum_fields(async_client: AsyncClient, admin_headers, db: AsyncSession):
    """Test creating a task with only required fields."""
    response = await async_client.post(
        "/api/scheduled-tasks/",
        json={
            "task_type": "sync",
            "task_name": "Minimal Task",
            "target_id": 1,
            "cron_expression": "* * * * *",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["timeout_seconds"] == 300  # Default value
    assert data["max_retries"] == 3  # Default value
    assert data["priority"] == 50  # Default value

    # Cleanup
    repo = ScheduledTaskRepository(db)
    await repo.delete(data["id"])


@pytest.mark.asyncio
async def test_create_task_invalid_type(async_client: AsyncClient, admin_headers):
    """Test creating a task with invalid task type."""
    response = await async_client.post(
        "/api/scheduled-tasks/",
        json={
            "task_type": "invalid_type",
            "task_name": "Invalid Type Task",
            "target_id": 1,
            "cron_expression": "* * * * *",
        },
    )
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_update_task_with_none_values(async_client: AsyncClient, admin_headers, sample_task: ScheduledTask):
    """Test that None values in update are ignored."""
    response = await async_client.put(
        f"/api/scheduled-tasks/{sample_task.id}",
        json={"description": None},
    )
    assert response.status_code == 200


# ============================================================================
# Update Scheduling Failure Rollback Tests
# ============================================================================


@pytest.mark.asyncio
async def test_update_task_with_invalid_cron_rolls_back(async_client: AsyncClient, admin_headers, sample_task: ScheduledTask):
    """Test that updating with an invalid cron expression rolls back the database change."""
    original_cron = sample_task.cron_expression
    original_name = sample_task.task_name

    # Try to update with invalid cron (e.g., invalid minute value)
    response = await async_client.put(
        f"/api/scheduled-tasks/{sample_task.id}",
        json={
            "task_name": "Should Be Rolled Back",
            "cron_expression": "99 * * * *",  # Invalid: minute must be 0-59
        },
    )
    assert response.status_code == 400  # Bad Request due to invalid cron

    # Verify the task was NOT updated in the database
    get_response = await async_client.get(f"/api/scheduled-tasks/{sample_task.id}")
    assert get_response.status_code == 200
    data = get_response.json()
    assert data["cron_expression"] == original_cron  # Should be unchanged
    assert data["task_name"] == original_name  # Should be unchanged


@pytest.mark.asyncio
async def test_update_task_wrong_part_count_rolls_back(async_client: AsyncClient, admin_headers, sample_task: ScheduledTask):
    """Test that updating with wrong cron part count rolls back the database change."""
    original_cron = sample_task.cron_expression

    # Try to update with 4-part cron (invalid)
    response = await async_client.put(
        f"/api/scheduled-tasks/{sample_task.id}",
        json={"cron_expression": "* * * *"},  # Only 4 parts
    )
    assert response.status_code == 400  # Bad Request

    # Verify the task was NOT updated in the database
    get_response = await async_client.get(f"/api/scheduled-tasks/{sample_task.id}")
    assert get_response.status_code == 200
    data = get_response.json()
    assert data["cron_expression"] == original_cron  # Should be unchanged


@pytest.mark.asyncio
async def test_create_task_with_invalid_cron_rolls_back(async_client: AsyncClient, admin_headers, db: AsyncSession):
    """Test that creating a task with invalid cron expression rolls back the database change."""
    invalid_crons = [
        "* * * *",  # 4 parts
        "99 * * * *",  # Invalid minute
        "a b c d e",  # Non-numeric values
    ]

    for invalid_cron in invalid_crons:
        response = await async_client.post(
            "/api/scheduled-tasks/",
            json={
                "task_type": "sync",
                "task_name": f"Invalid Cron Test {invalid_cron}",
                "target_id": 9999,
                "cron_expression": invalid_cron,
                "is_enabled": False,  # Disabled to avoid scheduling attempt
            },
        )
        assert response.status_code == 400, f"Expected 400 for cron: {invalid_cron}"

    # Verify no tasks were created with invalid crons
    repo = ScheduledTaskRepository(db)
    for invalid_cron in invalid_crons:
        task = await repo.get_by_target("sync", 9999)
        assert task is None, f"Task should not exist for invalid cron: {invalid_cron}"
