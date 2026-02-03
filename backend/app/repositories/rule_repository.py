"""Repository classes for rule and action database operations."""

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.rule import ActionDefinition, Rule


class ActionDefinitionRepository:
    """Repository for ActionDefinition database operations.

    Provides CRUD operations for managing action definitions
    stored in the database.
    """

    def __init__(self, session: AsyncSession):
        """Initialize the repository with a database session.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def create(
        self,
        name: str,
        entity_type: str,
        dsl_content: str,
        is_active: bool = True
    ) -> ActionDefinition:
        """Create a new action definition.

        Args:
            name: Action name (e.g., "PurchaseOrder.submit")
            entity_type: Entity type (e.g., "PurchaseOrder")
            dsl_content: Full ACTION DSL content
            is_active: Whether the action is active

        Returns:
            Created ActionDefinition instance
        """
        action = ActionDefinition(
            name=name,
            entity_type=entity_type,
            dsl_content=dsl_content,
            is_active=is_active
        )
        self.session.add(action)
        await self.session.commit()
        await self.session.refresh(action)
        return action

    async def get_by_id(self, action_id: int) -> Optional[ActionDefinition]:
        """Get an action definition by ID.

        Args:
            action_id: Action ID

        Returns:
            ActionDefinition instance or None
        """
        result = await self.session.execute(
            select(ActionDefinition).where(ActionDefinition.id == action_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Optional[ActionDefinition]:
        """Get an action definition by name.

        Args:
            name: Action name

        Returns:
            ActionDefinition instance or None
        """
        result = await self.session.execute(
            select(ActionDefinition).where(ActionDefinition.name == name)
        )
        return result.scalar_one_or_none()

    async def list_active(self) -> List[ActionDefinition]:
        """List all active action definitions.

        Returns:
            List of active ActionDefinition instances
        """
        result = await self.session.execute(
            select(ActionDefinition).where(ActionDefinition.is_active == True)
        )
        return list(result.scalars().all())

    async def list_by_entity_type(self, entity_type: str) -> List[ActionDefinition]:
        """List all active action definitions for an entity type.

        Args:
            entity_type: Entity type to filter by

        Returns:
            List of ActionDefinition instances for the entity type
        """
        result = await self.session.execute(
            select(ActionDefinition).where(
                ActionDefinition.entity_type == entity_type,
                ActionDefinition.is_active == True
            )
        )
        return list(result.scalars().all())

    async def list_all(self) -> List[ActionDefinition]:
        """List all action definitions.

        Returns:
            List of all ActionDefinition instances
        """
        result = await self.session.execute(select(ActionDefinition))
        return list(result.scalars().all())

    async def update(
        self,
        name: str,
        dsl_content: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> Optional[ActionDefinition]:
        """Update an action definition.

        Args:
            name: Action name to update
            dsl_content: New DSL content (optional)
            is_active: New active status (optional)

        Returns:
            Updated ActionDefinition or None if not found
        """
        action = await self.get_by_name(name)
        if action is None:
            return None

        if dsl_content is not None:
            action.dsl_content = dsl_content
        if is_active is not None:
            action.is_active = is_active

        await self.session.commit()
        await self.session.refresh(action)
        return action

    async def delete(self, name: str) -> bool:
        """Delete an action definition.

        Args:
            name: Action name to delete

        Returns:
            True if deleted, False if not found
        """
        action = await self.get_by_name(name)
        if action:
            await self.session.delete(action)
            await self.session.commit()
            return True
        return False

    async def exists(self, name: str) -> bool:
        """Check if an action definition exists.

        Args:
            name: Action name to check

        Returns:
            True if exists, False otherwise
        """
        return await self.get_by_name(name) is not None


class RuleRepository:
    """Repository for Rule database operations.

    Provides CRUD operations for managing business rules
    stored in the database.
    """

    def __init__(self, session: AsyncSession):
        """Initialize the repository with a database session.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def create(
        self,
        name: str,
        dsl_content: str,
        trigger_type: str,
        trigger_entity: str,
        trigger_property: Optional[str] = None,
        priority: int = 0,
        is_active: bool = True
    ) -> Rule:
        """Create a new rule.

        Args:
            name: Rule name
            dsl_content: Full RULE DSL content
            trigger_type: Trigger type (UPDATE/CREATE/DELETE)
            trigger_entity: Trigger entity type
            trigger_property: Trigger property (optional)
            priority: Rule priority (default 0)
            is_active: Whether the rule is active

        Returns:
            Created Rule instance
        """
        rule = Rule(
            name=name,
            dsl_content=dsl_content,
            trigger_type=trigger_type,
            trigger_entity=trigger_entity,
            trigger_property=trigger_property,
            priority=priority,
            is_active=is_active
        )
        self.session.add(rule)
        await self.session.commit()
        await self.session.refresh(rule)
        return rule

    async def get_by_id(self, rule_id: int) -> Optional[Rule]:
        """Get a rule by ID.

        Args:
            rule_id: Rule ID

        Returns:
            Rule instance or None
        """
        result = await self.session.execute(
            select(Rule).where(Rule.id == rule_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Optional[Rule]:
        """Get a rule by name.

        Args:
            name: Rule name

        Returns:
            Rule instance or None
        """
        result = await self.session.execute(
            select(Rule).where(Rule.name == name)
        )
        return result.scalar_one_or_none()

    async def list_active(self) -> List[Rule]:
        """List all active rules ordered by priority.

        Returns:
            List of active Rule instances
        """
        result = await self.session.execute(
            select(Rule)
            .where(Rule.is_active == True)
            .order_by(Rule.priority.desc())
        )
        return list(result.scalars().all())

    async def list_all(self) -> List[Rule]:
        """List all rules.

        Returns:
            List of all Rule instances
        """
        result = await self.session.execute(
            select(Rule).order_by(Rule.priority.desc())
        )
        return list(result.scalars().all())

    async def update(
        self,
        name: str,
        dsl_content: Optional[str] = None,
        priority: Optional[int] = None,
        is_active: Optional[bool] = None
    ) -> Optional[Rule]:
        """Update a rule.

        Args:
            name: Rule name to update
            dsl_content: New DSL content (optional)
            priority: New priority (optional)
            is_active: New active status (optional)

        Returns:
            Updated Rule or None if not found
        """
        rule = await self.get_by_name(name)
        if rule is None:
            return None

        if dsl_content is not None:
            rule.dsl_content = dsl_content
        if priority is not None:
            rule.priority = priority
        if is_active is not None:
            rule.is_active = is_active

        await self.session.commit()
        await self.session.refresh(rule)
        return rule

    async def delete(self, name: str) -> bool:
        """Delete a rule.

        Args:
            name: Rule name to delete

        Returns:
            True if deleted, False if not found
        """
        rule = await self.get_by_name(name)
        if rule:
            await self.session.delete(rule)
            await self.session.commit()
            return True
        return False

    async def exists(self, name: str) -> bool:
        """Check if a rule exists.

        Args:
            name: Rule name to check

        Returns:
            True if exists, False otherwise
        """
        return await self.get_by_name(name) is not None
