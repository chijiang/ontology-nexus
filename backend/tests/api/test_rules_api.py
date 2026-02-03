"""Tests for rules API endpoints."""

import pytest
import tempfile
import shutil
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.rule_engine.rule_registry import RuleRegistry
from app.services.rule_storage import RuleStorage
from app.api import rules
from app.api.deps import get_current_user
from app.models.user import User


@pytest.fixture
def temp_rules_dir():
    """Create a temporary directory for rule storage."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def client_with_rules(temp_rules_dir):
    """Create a test client with initialized rules API."""
    # Initialize registry and storage
    registry = RuleRegistry()
    storage = RuleStorage(temp_rules_dir)

    # Initialize the API
    rules.init_rules_api(registry, storage)

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
            "metadata": {"description": "Auto-approve low value orders"}
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
            "dsl_content": sample_rule_dsl
        }
    )

    # Try to upload again with same name
    response = client_with_rules.post(
        "/api/rules/",
        json={
            "name": "AutoApproveLowValue",
            "dsl_content": sample_rule_dsl
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
            "metadata": {"author": "test"}
        }
    )

    # Get the rule
    response = client_with_rules.get("/api/rules/AutoApproveLowValue")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "AutoApproveLowValue"
    assert data["metadata"]["author"] == "test"
    assert "dsl_content" in data
    assert "rule_info" in data


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
            "dsl_content": sample_rule_dsl
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


def test_upload_rule_with_metadata(client_with_rules):
    """Test uploading a rule with custom metadata."""
    dsl = """
    RULE TestRule PRIORITY 50 {
        ON UPDATE (Test.prop)
        FOR (t: Test) {
        }
    }
    """

    metadata = {
        "author": "test-user",
        "description": "A test rule",
        "tags": ["test", "sample"]
    }

    response = client_with_rules.post(
        "/api/rules/",
        json={
            "name": "TestRule",
            "dsl_content": dsl,
            "metadata": metadata
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["rule"]["metadata"] == metadata

    # Verify metadata is preserved
    get_response = client_with_rules.get("/api/rules/TestRule")
    assert get_response.status_code == 200
    rule_data = get_response.json()
    assert rule_data["metadata"]["author"] == "test-user"
    assert rule_data["metadata"]["tags"] == ["test", "sample"]
