"""Fixtures for API tests."""

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    """Get authenticated headers for testing."""
    # Create a test user and get token
    response = client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpass123"
        }
    )

    if response.status_code == 200:
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    # User might already exist, try login
    response = client.post(
        "/api/auth/login",
        data={
            "username": "testuser",
            "password": "testpass123"
        }
    )

    if response.status_code == 200:
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return {}


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
