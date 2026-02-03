import pytest
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import async_session
from app.models.rule import Rule, ActionDefinition


@pytest.mark.asyncio
async def test_action_definition_crud():
    """Test ActionDefinition CRUD operations with database."""
    async with async_session() as session:
        # Create
        action = ActionDefinition(
            name="PurchaseOrder.submit",
            entity_type="PurchaseOrder",
            dsl_content='ACTION PurchaseOrder.submit { }'
        )
        session.add(action)
        await session.commit()
        await session.refresh(action)

        assert action.id is not None
        assert action.name == "PurchaseOrder.submit"

        # Read
        from sqlalchemy import select
        result = await session.execute(
            select(ActionDefinition).where(ActionDefinition.name == "PurchaseOrder.submit")
        )
        retrieved_action = result.scalar_one_or_none()
        assert retrieved_action is not None
        assert retrieved_action.entity_type == "PurchaseOrder"

        # Update
        retrieved_action.dsl_content = 'ACTION PurchaseOrder.submit { UPDATED }'
        await session.commit()
        await session.refresh(retrieved_action)
        assert "UPDATED" in retrieved_action.dsl_content

        # Cleanup
        await session.delete(retrieved_action)
        await session.commit()


@pytest.mark.asyncio
async def test_rule_crud():
    """Test Rule CRUD operations with database."""
    async with async_session() as session:
        # Create
        rule = Rule(
            name="SupplierStatusBlocking",
            trigger_type="UPDATE",
            trigger_entity="Supplier",
            trigger_property="status",
            dsl_content='RULE SupplierStatusBlocking { }'
        )
        session.add(rule)
        await session.commit()
        await session.refresh(rule)

        assert rule.id is not None
        assert rule.name == "SupplierStatusBlocking"

        # Read
        from sqlalchemy import select
        result = await session.execute(
            select(Rule).where(Rule.name == "SupplierStatusBlocking")
        )
        retrieved_rule = result.scalar_one_or_none()
        assert retrieved_rule is not None
        assert retrieved_rule.trigger_entity == "Supplier"

        # Update
        retrieved_rule.priority = 100
        await session.commit()
        await session.refresh(retrieved_rule)
        assert retrieved_rule.priority == 100

        # Cleanup
        await session.delete(retrieved_rule)
        await session.commit()
