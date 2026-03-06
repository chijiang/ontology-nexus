"""Fixtures for API tests."""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.api.deps import get_current_user
from app.models.user import User


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    from fastapi.testclient import TestClient

    return TestClient(app)


@pytest.fixture
async def async_client():
    """Create an async test client for the FastAPI app."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        yield ac


@pytest.fixture
def mock_user_instance():
    """Create a mock user instance."""
    return User(
        id=1,
        username="testuser",
        email="test@example.com",
        is_admin=True,
        approval_status="approved",
    )


@pytest.fixture
def auth_headers(mock_user_instance):
    """Bypass actual auth and return mock headers."""

    def mock_get_current_user():
        return mock_user_instance

    app.dependency_overrides[get_current_user] = mock_get_current_user
    yield {"Authorization": "Bearer mock-token"}
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def sample_action_dsl():
    """Sample ACTION DSL for testing."""
    return """
    ACTION PurchaseOrder.submit
    PARAMETERS
    END

    PRECONDITIONS
        PRECOND submit_can_proceed
            this.status == "draft"
            ON_FAILURE "Cannot submit: status must be draft"
    END

    EFFECT
        SET this.status = "submitted"
        SET this.submittedAt = NOW()
    END
    """


@pytest.fixture
def sample_rule_dsl():
    """Sample RULE DSL for testing."""
    return """
    RULE AutoApproveLowValue
    PRIORITY 100
    ON UPDATE PurchaseOrder.status

    FOR po IN PurchaseOrder
        WHERE po.status == "submitted" AND po.totalAmount < 1000
    DO
        SET po.status = "approved"
        SET po.approvedAt = NOW()
    END
    """
