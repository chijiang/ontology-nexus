"""Tests for actions API endpoints."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.main import app
from app.rule_engine.action_registry import ActionRegistry
from app.rule_engine.action_executor import ActionExecutor
from app.api import actions
from app.api.deps import get_current_user
from app.models.user import User


@pytest.fixture
def client_with_actions():
    """Create a test client with initialized actions API."""
    # Initialize registries
    registry = ActionRegistry()
    executor = ActionExecutor(registry)

    # Initialize the API
    actions.init_actions_api(registry, executor)

    # Create test client
    client = TestClient(app)

    # Mock user for authentication
    def mock_get_current_user():
        return User(id=1, username="test", email="test@example.com", password_hash="hash")

    app.dependency_overrides[get_current_user] = mock_get_current_user

    yield client

    # Clean up
    app.dependency_overrides = {}


@pytest.fixture
def sample_action_dsl():
    """Sample ACTION DSL for testing."""
    return """
    ACTION PurchaseOrder.submit {
        PRECONDITION: this.status == "draft" ON_FAILURE: "Cannot submit: status must be draft"
        EFFECT {
            SET this.status = "submitted";
        }
    }
    """


def test_list_actions_empty(client_with_actions):
    """Test listing actions when none are registered."""
    response = client_with_actions.get("/api/actions/")
    assert response.status_code == 200
    data = response.json()
    assert "actions" in data
    assert "count" in data
    assert data["count"] == 0


def test_list_actions_with_registered_actions(client_with_actions, sample_action_dsl):
    """Test listing actions after registering one."""
    # Get the registry and load an action
    from app.api.actions import get_action_registry
    registry = get_action_registry()
    registry.load_from_text(sample_action_dsl)

    response = client_with_actions.get("/api/actions/")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["actions"][0]["entity_type"] == "PurchaseOrder"
    assert data["actions"][0]["action_name"] == "submit"


def test_list_entity_actions(client_with_actions, sample_action_dsl):
    """Test listing actions for a specific entity type."""
    # Load an action
    from app.api.actions import get_action_registry
    registry = get_action_registry()
    registry.load_from_text(sample_action_dsl)

    response = client_with_actions.get("/api/actions/PurchaseOrder")
    assert response.status_code == 200
    data = response.json()
    assert data["entity_type"] == "PurchaseOrder"
    assert data["count"] == 1
    assert data["actions"][0]["action_name"] == "submit"


def test_list_entity_actions_not_found(client_with_actions):
    """Test listing actions for an entity type with no actions."""
    response = client_with_actions.get("/api/actions/NonExistent")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 0
    assert data["actions"] == []


def test_execute_action_success(client_with_actions, sample_action_dsl):
    """Test executing an action successfully."""
    # Load an action
    from app.api.actions import get_action_registry
    registry = get_action_registry()
    registry.load_from_text(sample_action_dsl)

    # Execute the action
    response = client_with_actions.post(
        "/api/actions/PurchaseOrder/submit",
        json={
            "entity_id": "po-123",
            "entity_data": {"status": "draft", "totalAmount": 500},
            "params": {}
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "changes" in data
    assert "message" in data


def test_execute_action_precondition_fails(client_with_actions, sample_action_dsl):
    """Test executing an action when precondition fails."""
    # Load an action
    from app.api.actions import get_action_registry
    registry = get_action_registry()
    registry.load_from_text(sample_action_dsl)

    # Execute with wrong status (precondition should fail)
    response = client_with_actions.post(
        "/api/actions/PurchaseOrder/submit",
        json={
            "entity_id": "po-123",
            "entity_data": {"status": "already_submitted", "totalAmount": 500},
            "params": {}
        }
    )

    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "Cannot submit" in data["detail"]


def test_execute_action_not_found(client_with_actions):
    """Test executing a non-existent action."""
    response = client_with_actions.post(
        "/api/actions/NonExistent/action",
        json={
            "entity_id": "test-123",
            "entity_data": {},
            "params": {}
        }
    )

    assert response.status_code == 400


def test_list_actions_multiple_actions(client_with_actions):
    """Test listing multiple actions."""
    # Load multiple actions
    from app.api.actions import get_action_registry
    registry = get_action_registry()

    dsl1 = """
    ACTION PurchaseOrder.submit {
        PRECONDITION: this.status == "draft" ON_FAILURE: "Cannot submit"
        EFFECT {
            SET this.status = "submitted";
        }
    }
    """

    dsl2 = """
    ACTION PurchaseOrder.cancel {
        PRECONDITION: this.status == "draft" ON_FAILURE: "Cannot cancel"
        EFFECT {
            SET this.status = "cancelled";
        }
    }
    """

    registry.load_from_text(dsl1)
    registry.load_from_text(dsl2)

    response = client_with_actions.get("/api/actions/")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 2

    action_names = [a["action_name"] for a in data["actions"]]
    assert "submit" in action_names
    assert "cancel" in action_names
