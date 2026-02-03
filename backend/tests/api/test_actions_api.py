"""Tests for actions API endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base
from app.rule_engine.action_registry import ActionRegistry
from app.rule_engine.action_executor import ActionExecutor
from app.api import actions
from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User


# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def test_engine():
    """Create a test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
def temp_rules_dir():
    """Create a temporary directory for rule storage."""
    import tempfile
    import shutil
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def client_with_actions(test_engine, temp_rules_dir):
    """Create a test client with initialized actions API."""
    # Initialize registries
    registry = ActionRegistry()
    executor = ActionExecutor(registry)

    # Initialize the API
    actions.init_actions_api(registry, executor)

    # Override database dependency
    async_session = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async def get_test_db():
        async with async_session() as session:
            yield session

    app.dependency_overrides[get_db] = get_test_db

    # Mock user for authentication
    def mock_get_current_user():
        return User(id=1, username="test", email="test@example.com", password_hash="hash")

    app.dependency_overrides[get_current_user] = mock_get_current_user

    # Create test client
    client = TestClient(app)

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


def test_upload_action_definition(client_with_actions, sample_action_dsl):
    """Test uploading an action definition via API."""
    response = client_with_actions.post(
        "/api/actions/",
        json={
            "name": "PurchaseOrder.submit",
            "entity_type": "PurchaseOrder",
            "dsl_content": sample_action_dsl,
            "is_active": True
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Action uploaded successfully"
    assert "action" in data
    assert data["action"]["name"] == "PurchaseOrder.submit"
    assert data["action"]["entity_type"] == "PurchaseOrder"


def test_upload_action_duplicate(client_with_actions, sample_action_dsl):
    """Test uploading a duplicate action."""
    # Upload first time
    client_with_actions.post(
        "/api/actions/",
        json={
            "name": "PurchaseOrder.submit",
            "entity_type": "PurchaseOrder",
            "dsl_content": sample_action_dsl
        }
    )

    # Try to upload again with same name
    response = client_with_actions.post(
        "/api/actions/",
        json={
            "name": "PurchaseOrder.submit",
            "entity_type": "PurchaseOrder",
            "dsl_content": sample_action_dsl
        }
    )

    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "already exists" in data["detail"]


def test_list_action_definitions(client_with_actions, sample_action_dsl):
    """Test listing action definitions from database."""
    # Upload an action
    client_with_actions.post(
        "/api/actions/",
        json={
            "name": "PurchaseOrder.submit",
            "entity_type": "PurchaseOrder",
            "dsl_content": sample_action_dsl
        }
    )

    # List definitions
    response = client_with_actions.get("/api/actions/definitions")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] >= 1

    # Find our action
    actions = [a for a in data["actions"] if a["name"] == "PurchaseOrder.submit"]
    assert len(actions) == 1
    assert actions[0]["entity_type"] == "PurchaseOrder"
    assert actions[0]["is_active"] is True


def test_get_action_definition(client_with_actions, sample_action_dsl):
    """Test getting an action definition by name."""
    # Upload an action
    client_with_actions.post(
        "/api/actions/",
        json={
            "name": "PurchaseOrder.submit",
            "entity_type": "PurchaseOrder",
            "dsl_content": sample_action_dsl
        }
    )

    # Get the definition
    response = client_with_actions.get("/api/actions/definitions/PurchaseOrder.submit")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "PurchaseOrder.submit"
    assert data["entity_type"] == "PurchaseOrder"
    assert "dsl_content" in data


def test_get_action_definition_not_found(client_with_actions):
    """Test getting a non-existent action definition."""
    response = client_with_actions.get("/api/actions/definitions/NonExistent")
    assert response.status_code == 404


def test_delete_action_definition(client_with_actions, sample_action_dsl):
    """Test deleting an action definition."""
    # Upload an action
    client_with_actions.post(
        "/api/actions/",
        json={
            "name": "PurchaseOrder.submit",
            "entity_type": "PurchaseOrder",
            "dsl_content": sample_action_dsl
        }
    )

    # Delete the action
    response = client_with_actions.delete("/api/actions/definitions/PurchaseOrder.submit")
    assert response.status_code == 200
    data = response.json()
    assert "deleted successfully" in data["message"]

    # Verify it's gone
    get_response = client_with_actions.get("/api/actions/definitions/PurchaseOrder.submit")
    assert get_response.status_code == 404
