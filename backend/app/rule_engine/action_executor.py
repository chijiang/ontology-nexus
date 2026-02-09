"""Action executor for executing ACTION definitions."""

from dataclasses import dataclass, field
from typing import Any
from app.rule_engine.action_registry import ActionRegistry
from app.rule_engine.models import ActionDef, SetStatement, UpdateEvent
from app.rule_engine.context import EvaluationContext
from app.rule_engine.evaluator import ExpressionEvaluator
from app.rule_engine.event_emitter import GraphEventEmitter


@dataclass
class ExecutionResult:
    """Result of executing an ACTION.

    Attributes:
        success: Whether the action executed successfully
        error: Error message if execution failed, None otherwise
        changes: Dictionary of property changes made by the action
    """

    success: bool
    error: str | None = None
    changes: dict[str, Any] = field(default_factory=dict)


class ActionExecutor:
    """Executor for ACTION definitions.

    The executor checks preconditions and applies effects for actions.
    It uses the ExpressionEvaluator to evaluate precondition expressions
    and applies SET statements from the effect block.
    """

    def __init__(
        self, registry: ActionRegistry, event_emitter: GraphEventEmitter | None = None
    ):
        """Initialize the executor.

        Args:
            registry: ActionRegistry containing action definitions
            event_emitter: Optional GraphEventEmitter for triggering rules
        """
        self.registry = registry
        self.event_emitter = event_emitter

    async def execute(
        self, entity_type: str, action_name: str, context: EvaluationContext
    ) -> ExecutionResult:
        """Execute an ACTION.

        This method:
        1. Looks up the action definition
        2. Checks all preconditions in order
        3. If all preconditions pass, applies the effect

        Args:
            entity_type: The entity type (e.g., "PurchaseOrder")
            action_name: The action name (e.g., "submit")
            context: Evaluation context containing entity data

        Returns:
            ExecutionResult with success status and any changes
        """
        # Look up the action definition
        action = self.registry.lookup(entity_type, action_name)
        if action is None:
            return ExecutionResult(
                success=False, error=f"Action {entity_type}.{action_name} not found"
            )

        # Create evaluator for this execution
        evaluator = ExpressionEvaluator(context)

        # Check all preconditions
        for precondition in action.preconditions:
            result = await evaluator.evaluate(precondition.condition)
            if not result:
                return ExecutionResult(success=False, error=precondition.on_failure)

        # All preconditions passed - apply effect if present
        changes = {}
        if action.effect is not None:
            changes = await self._apply_effect(action.effect, evaluator, context)

        # Persist changes to database if any
        if changes and context.session:
            await self._persist_changes(
                entity_type,
                context.entity["id"],
                changes,
                context.session,
                context_entity=context.entity,
            )

        return ExecutionResult(success=True, error=None, changes=changes)

    async def _persist_changes(
        self,
        entity_type: str,
        entity_id: str,
        changes: dict[str, Any],
        session: Any,
        context_entity: dict[str, Any] | None = None,
    ):
        """Persist property changes to PostgreSQL.

        Args:
            entity_type: Entity type/label
            entity_id: Entity name property
            changes: Dictionary of properties to update
            session: Active PostgreSQL DB session
        """
        from sqlalchemy import update
        from app.models.graph import GraphEntity

        # Build the update query
        # We need to merge changes with existing properties
        # Note: We'll reconstruct the update based on found entity to be safe

        # Execute query to get current entity, then update properties
        from sqlalchemy import select

        stmt = select(GraphEntity)
        if isinstance(entity_id, int):
            stmt = stmt.where(GraphEntity.id == entity_id)
        else:
            stmt = stmt.where(
                GraphEntity.name == entity_id, GraphEntity.entity_type == entity_type
            )

        result = await session.execute(stmt)
        entity = result.scalar_one_or_none()

        if entity:
            # Merge properties
            current_props = entity.properties or {}
            merged_props = {**current_props, **changes}

            # Update with merged properties
            await session.execute(
                update(GraphEntity)
                .where(GraphEntity.id == entity.id)
                .values(properties=merged_props)
            )

        # Emit events for rule engine
        if self.event_emitter:
            self._emit_update_events(
                entity_type, entity_id, changes, context_entity=context_entity
            )

    def _emit_update_events(
        self,
        entity_type: str,
        entity_id: str,
        changes: dict[str, Any],
        context_entity: dict[str, Any] | None = None,
    ):
        """Emit UpdateEvent for each changed property.

        Args:
            entity_type: Entity label
            entity_id: Entity name property
            changes: Dictionary of properties that were updated
            context_entity: Original entity properties from context
        """
        if not self.event_emitter:
            return

        for key, new_val in changes.items():
            old_val = context_entity.get(key) if context_entity else None

            # Skip if value hasn't actually changed
            if old_val == new_val:
                continue

            event = UpdateEvent(
                entity_type=entity_type,
                entity_id=entity_id,
                property=key,
                old_value=old_val,
                new_value=new_val,
            )
            self.event_emitter.emit(event)

    async def _apply_effect(
        self, effect: Any, evaluator: ExpressionEvaluator, context: EvaluationContext
    ) -> dict[str, Any]:
        """Apply an effect block to the context.

        Args:
            effect: EffectBlock with statements
            evaluator: ExpressionEvaluator for evaluating values
            context: EvaluationContext to modify

        Returns:
            Dictionary of property changes
        """
        changes = {}

        if effect is None:
            return changes

        statements = getattr(effect, "statements", [])
        if not statements:
            return changes

        for statement in statements:
            if isinstance(statement, SetStatement):
                change = await self._apply_set_statement(statement, evaluator)
                changes.update(change)

        return changes

    async def _apply_set_statement(
        self, statement: SetStatement, evaluator: ExpressionEvaluator
    ) -> dict[str, Any]:
        """Apply a SET statement.

        Args:
            statement: SetStatement to apply
            evaluator: ExpressionEvaluator for evaluating the value

        Returns:
            Dictionary with the property change
        """
        # Evaluate the value
        value = await evaluator.evaluate(statement.value)

        # Extract the property name from the target path
        # e.g., "this.status" -> "status"
        if statement.target.startswith("this."):
            prop_name = statement.target[len("this.") :]
        else:
            prop_name = statement.target

        return {prop_name: value}
