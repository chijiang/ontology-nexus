"""Tests for repository layer.

Tests the ActionDefinitionRepository and RuleRepository classes.
"""

import pytest
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.rule import ActionDefinition, Rule
from app.repositories.rule_repository import ActionDefinitionRepository, RuleRepository


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


class TestActionDefinitionRepository:
    """Test ActionDefinitionRepository."""

    @pytest.mark.asyncio
    async def test_create_action(self, test_session):
        """Test creating an action definition."""
        repo = ActionDefinitionRepository(test_session)
        action = await repo.create(
            name="PurchaseOrder.submit",
            entity_type="PurchaseOrder",
            dsl_content='ACTION PurchaseOrder.submit { EFFECT { SET this.status = "submitted"; } }'
        )

        assert action.id is not None
        assert action.name == "PurchaseOrder.submit"
        assert action.entity_type == "PurchaseOrder"
        assert action.is_active is True

    @pytest.mark.asyncio
    async def test_get_by_name(self, test_session):
        """Test getting an action by name."""
        repo = ActionDefinitionRepository(test_session)
        await repo.create(
            name="PurchaseOrder.submit",
            entity_type="PurchaseOrder",
            dsl_content="ACTION PurchaseOrder.submit { }"
        )

        action = await repo.get_by_name("PurchaseOrder.submit")
        assert action is not None
        assert action.name == "PurchaseOrder.submit"

    @pytest.mark.asyncio
    async def test_get_by_name_not_found(self, test_session):
        """Test getting a non-existent action."""
        repo = ActionDefinitionRepository(test_session)
        action = await repo.get_by_name("NonExistent")
        assert action is None

    @pytest.mark.asyncio
    async def test_list_active(self, test_session):
        """Test listing active actions."""
        repo = ActionDefinitionRepository(test_session)
        await repo.create(
            name="Action1.active",
            entity_type="Entity",
            dsl_content="ACTION Entity.action1 { }",
            is_active=True
        )
        await repo.create(
            name="Action2.inactive",
            entity_type="Entity",
            dsl_content="ACTION Entity.action2 { }",
            is_active=False
        )

        actions = await repo.list_active()
        assert len(actions) == 1
        assert actions[0].name == "Action1.active"

    @pytest.mark.asyncio
    async def test_list_all(self, test_session):
        """Test listing all actions."""
        repo = ActionDefinitionRepository(test_session)
        await repo.create(
            name="Action1",
            entity_type="Entity",
            dsl_content="ACTION Entity.action1 { }",
            is_active=True
        )
        await repo.create(
            name="Action2",
            entity_type="Entity",
            dsl_content="ACTION Entity.action2 { }",
            is_active=False
        )

        actions = await repo.list_all()
        assert len(actions) == 2

    @pytest.mark.asyncio
    async def test_list_by_entity_type(self, test_session):
        """Test listing actions by entity type."""
        repo = ActionDefinitionRepository(test_session)
        await repo.create(
            name="PurchaseOrder.submit",
            entity_type="PurchaseOrder",
            dsl_content="ACTION PurchaseOrder.submit { }"
        )
        await repo.create(
            name="Supplier.approve",
            entity_type="Supplier",
            dsl_content="ACTION Supplier.approve { }"
        )

        actions = await repo.list_by_entity_type("PurchaseOrder")
        assert len(actions) == 1
        assert actions[0].name == "PurchaseOrder.submit"

    @pytest.mark.asyncio
    async def test_update(self, test_session):
        """Test updating an action."""
        repo = ActionDefinitionRepository(test_session)
        await repo.create(
            name="Action1",
            entity_type="Entity",
            dsl_content="ACTION Entity.action1 { }"
        )

        updated = await repo.update(
            "Action1",
            dsl_content="ACTION Entity.action1 { EFFECT { SET this.status = 'done'; } }",
            is_active=False
        )

        assert updated is not None
        assert updated.dsl_content != "ACTION Entity.action1 { }"
        assert updated.is_active is False

    @pytest.mark.asyncio
    async def test_delete(self, test_session):
        """Test deleting an action."""
        repo = ActionDefinitionRepository(test_session)
        await repo.create(
            name="Action1",
            entity_type="Entity",
            dsl_content="ACTION Entity.action1 { }"
        )

        result = await repo.delete("Action1")
        assert result is True

        action = await repo.get_by_name("Action1")
        assert action is None

    @pytest.mark.asyncio
    async def test_exists(self, test_session):
        """Test checking if an action exists."""
        repo = ActionDefinitionRepository(test_session)

        assert await repo.exists("Action1") is False

        await repo.create(
            name="Action1",
            entity_type="Entity",
            dsl_content="ACTION Entity.action1 { }"
        )

        assert await repo.exists("Action1") is True


class TestRuleRepository:
    """Test RuleRepository."""

    @pytest.mark.asyncio
    async def test_create_rule(self, test_session):
        """Test creating a rule."""
        repo = RuleRepository(test_session)
        rule = await repo.create(
            name="AutoApprove",
            dsl_content="RULE AutoApprove PRIORITY 100 { ON UPDATE (Entity.prop) FOR (e: Entity) { } }",
            trigger_type="UPDATE",
            trigger_entity="Entity",
            trigger_property="prop",
            priority=100
        )

        assert rule.id is not None
        assert rule.name == "AutoApprove"
        assert rule.trigger_type == "UPDATE"
        assert rule.priority == 100

    @pytest.mark.asyncio
    async def test_get_by_name(self, test_session):
        """Test getting a rule by name."""
        repo = RuleRepository(test_session)
        await repo.create(
            name="TestRule",
            dsl_content="RULE TestRule PRIORITY 50 { ON UPDATE (Entity.prop) FOR (e: Entity) { } }",
            trigger_type="UPDATE",
            trigger_entity="Entity",
            trigger_property="prop"
        )

        rule = await repo.get_by_name("TestRule")
        assert rule is not None
        assert rule.name == "TestRule"

    @pytest.mark.asyncio
    async def test_list_active_ordered_by_priority(self, test_session):
        """Test listing active rules ordered by priority."""
        repo = RuleRepository(test_session)
        await repo.create(
            name="LowPriority",
            dsl_content="RULE LowPriority PRIORITY 10 { ON UPDATE (Entity.prop) FOR (e: Entity) { } }",
            trigger_type="UPDATE",
            trigger_entity="Entity",
            priority=10,
            is_active=True
        )
        await repo.create(
            name="HighPriority",
            dsl_content="RULE HighPriority PRIORITY 100 { ON UPDATE (Entity.prop) FOR (e: Entity) { } }",
            trigger_type="UPDATE",
            trigger_entity="Entity",
            priority=100,
            is_active=True
        )
        await repo.create(
            name="Inactive",
            dsl_content="RULE Inactive PRIORITY 50 { ON UPDATE (Entity.prop) FOR (e: Entity) { } }",
            trigger_type="UPDATE",
            trigger_entity="Entity",
            priority=50,
            is_active=False
        )

        rules = await repo.list_active()
        assert len(rules) == 2
        # Should be ordered by priority descending
        assert rules[0].name == "HighPriority"
        assert rules[1].name == "LowPriority"

    @pytest.mark.asyncio
    async def test_update(self, test_session):
        """Test updating a rule."""
        repo = RuleRepository(test_session)
        await repo.create(
            name="TestRule",
            dsl_content="RULE TestRule PRIORITY 50 { ON UPDATE (Entity.prop) FOR (e: Entity) { } }",
            trigger_type="UPDATE",
            trigger_entity="Entity",
            priority=50
        )

        updated = await repo.update(
            "TestRule",
            priority=200,
            is_active=False
        )

        assert updated is not None
        assert updated.priority == 200
        assert updated.is_active is False

    @pytest.mark.asyncio
    async def test_delete(self, test_session):
        """Test deleting a rule."""
        repo = RuleRepository(test_session)
        await repo.create(
            name="TestRule",
            dsl_content="RULE TestRule PRIORITY 50 { ON UPDATE (Entity.prop) FOR (e: Entity) { } }",
            trigger_type="UPDATE",
            trigger_entity="Entity"
        )

        result = await repo.delete("TestRule")
        assert result is True

        rule = await repo.get_by_name("TestRule")
        assert rule is None

    @pytest.mark.asyncio
    async def test_exists(self, test_session):
        """Test checking if a rule exists."""
        repo = RuleRepository(test_session)

        assert await repo.exists("TestRule") is False

        await repo.create(
            name="TestRule",
            dsl_content="RULE TestRule PRIORITY 50 { ON UPDATE (Entity.prop) FOR (e: Entity) { } }",
            trigger_type="UPDATE",
            trigger_entity="Entity"
        )

        assert await repo.exists("TestRule") is True
