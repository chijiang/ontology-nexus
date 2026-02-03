"""Tests for rules API endpoints."""

import pytest
import tempfile
import shutil
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base
from app.rule_engine.rule_registry import RuleRegistry
from app.services.rule_storage import RuleStorage
from app.api import rules
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
async def test_session(test_engine):
    """Create a test database session."""
    async_session = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session


@pytest.fixture
def temp_rules_dir():
    """Create a temporary directory for rule storage."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def client_with_rules(test_engine, temp_rules_dir):
    """Create a test client with initialized rules API."""
    # Initialize registry and storage
    registry = RuleRegistry()
    storage = RuleStorage(temp_rules_dir)

    # Initialize the API
    rules.init_rules_api(registry, storage)

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
def sample_rule_dsl():
    """Sample RULE DSL for testing."""
    return """
    RULE AutoApproveLowValue PRIORITY 100 {
        ON UPDATE (PurchaseOrder.status)
        FOR (po: PurchaseOrder) {
            SET po.status = "approved";
            SET po.approvedAt = NOW();
        }
    }
    """


def test_list_rules_empty(client_with_rules):
    """Test listing rules when none exist."""
    response = client_with_rules.get("/api/rules/")
    assert response.status_code == 200
    data = response.json()
    assert "rules" in data
    assert "count" in data
    assert data["count"] == 0


def test_upload_rule_success(client_with_rules, sample_rule_dsl):
    """Test uploading a rule successfully."""
    response = client_with_rules.post(
        "/api/rules/",
        json={
            "name": "AutoApproveLowValue",
            "dsl_content": sample_rule_dsl,
            "priority": 100
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Rule uploaded successfully"
    assert "rule" in data
    assert data["rule"]["name"] == "AutoApproveLowValue"


def test_upload_rule_duplicate(client_with_rules, sample_rule_dsl):
    """Test uploading a duplicate rule."""
    # Upload first time
    client_with_rules.post(
        "/api/rules/",
        json={
            "name": "AutoApproveLowValue",
            "dsl_content": sample_rule_dsl,
            "priority": 100
        }
    )

    # Try to upload again with same name
    response = client_with_rules.post(
        "/api/rules/",
        json={
            "name": "AutoApproveLowValue",
            "dsl_content": sample_rule_dsl,
            "priority": 100
        }
    )

    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "already exists" in data["detail"]


def test_upload_rule_invalid_dsl(client_with_rules):
    """Test uploading a rule with invalid DSL."""
    response = client_with_rules.post(
        "/api/rules/",
        json={
            "name": "InvalidRule",
            "dsl_content": "This is not valid DSL content"
        }
    )

    assert response.status_code == 400


def test_get_rule_success(client_with_rules, sample_rule_dsl):
    """Test getting a rule by name."""
    # Upload a rule first
    client_with_rules.post(
        "/api/rules/",
        json={
            "name": "AutoApproveLowValue",
            "dsl_content": sample_rule_dsl,
            "priority": 100
        }
    )

    # Get the rule
    response = client_with_rules.get("/api/rules/AutoApproveLowValue")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "AutoApproveLowValue"
    assert "dsl_content" in data
    assert "trigger" in data


def test_get_rule_not_found(client_with_rules):
    """Test getting a non-existent rule."""
    response = client_with_rules.get("/api/rules/NonExistent")
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert "not found" in data["detail"]


def test_delete_rule_success(client_with_rules, sample_rule_dsl):
    """Test deleting a rule."""
    # Upload a rule first
    client_with_rules.post(
        "/api/rules/",
        json={
            "name": "AutoApproveLowValue",
            "dsl_content": sample_rule_dsl,
            "priority": 100
        }
    )

    # Delete the rule
    response = client_with_rules.delete("/api/rules/AutoApproveLowValue")
    assert response.status_code == 200
    data = response.json()
    assert "deleted successfully" in data["message"]

    # Verify it's gone
    get_response = client_with_rules.get("/api/rules/AutoApproveLowValue")
    assert get_response.status_code == 404


def test_delete_rule_not_found(client_with_rules):
    """Test deleting a non-existent rule."""
    response = client_with_rules.delete("/api/rules/NonExistent")
    assert response.status_code == 404


def test_list_rules_multiple(client_with_rules):
    """Test listing multiple rules."""
    # Upload multiple rules
    rule1 = """
    RULE RuleOne PRIORITY 100 {
        ON UPDATE (Entity.prop)
        FOR (e: Entity) {
        }
    }
    """

    rule2 = """
    RULE RuleTwo PRIORITY 200 {
        ON UPDATE (Entity.prop)
        FOR (e: Entity) {
        }
    }
    """

    client_with_rules.post(
        "/api/rules/",
        json={"name": "RuleOne", "dsl_content": rule1}
    )

    client_with_rules.post(
        "/api/rules/",
        json={"name": "RuleTwo", "dsl_content": rule2}
    )

    # List all rules
    response = client_with_rules.get("/api/rules/")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 2

    rule_names = [r["name"] for r in data["rules"]]
    assert "RuleOne" in rule_names
    assert "RuleTwo" in rule_names


def test_upload_rule_with_priority(client_with_rules):
    """Test uploading a rule with custom priority."""
    dsl = """
    RULE TestRule PRIORITY 50 {
        ON UPDATE (Test.prop)
        FOR (t: Test) {
        }
    }
    """

    response = client_with_rules.post(
        "/api/rules/",
        json={
            "name": "TestRule",
            "dsl_content": dsl,
            "priority": 50,
            "is_active": True
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["rule"]["priority"] == 50

    # Verify priority is preserved
    get_response = client_with_rules.get("/api/rules/TestRule")
    assert get_response.status_code == 200
    rule_data = get_response.json()
    assert rule_data["priority"] == 50


def test_reload_rules(client_with_rules, sample_rule_dsl):
    """Test reloading rules from database."""
    # Upload a rule
    client_with_rules.post(
        "/api/rules/",
        json={
            "name": "AutoApproveLowValue",
            "dsl_content": sample_rule_dsl,
            "priority": 100
        }
    )

    # Reload rules
    response = client_with_rules.post("/api/rules/reload")
    assert response.status_code == 200
    data = response.json()
    assert "loaded" in data
    assert data["loaded"] >= 0


def test_migrate_rules_from_files(client_with_rules, temp_rules_dir):
    """Test migrating rules from file storage."""
    # Create a rule file in the storage directory
    import json
    rule_file = Path(temp_rules_dir) / "FileRule.json"
    rule_data = {
        "name": "FileRule",
        "dsl_content": """
        RULE FileRule PRIORITY 75 {
            ON UPDATE (Entity.prop)
            FOR (e: Entity) {
            }
        }
        """,
        "metadata": {"source": "file"},
        "rule_info": {
            "priority": 75,
            "trigger": {
                "type": "UPDATE",
                "entity_type": "Entity",
                "property": "prop"
            }
        }
    }
    with open(rule_file, "w") as f:
        json.dump(rule_data, f)

    # Migrate
    response = client_with_rules.post("/api/rules/migrate")
    assert response.status_code == 200
    data = response.json()
    assert "migrated" in data
    assert data["migrated"] >= 1

    # Verify rule was migrated
    get_response = client_with_rules.get("/api/rules/FileRule")
    assert get_response.status_code == 200
