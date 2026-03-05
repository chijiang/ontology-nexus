"""Action executor for executing ACTION definitions."""

from dataclasses import dataclass, field
from typing import Any
from app.rule_engine.action_registry import ActionRegistry
from app.rule_engine.models import (
    ActionDef,
    SetStatement,
    CallStatement,
    ReturnStatement,
    UpdateEvent,
)
from app.rule_engine.context import EvaluationContext
from app.rule_engine.evaluator import ExpressionEvaluator
from app.rule_engine.event_emitter import GraphEventEmitter
from app.rule_engine.persistence import PersistenceService


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
    return_value: Any | None = None


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
        self,
        entity_type: str,
        action_name: str,
        context: EvaluationContext,
        actor_name: str | None = None,
        actor_type: str | None = None,
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
            actor_name: Name of the actor executing the action
            actor_type: Type of the actor (AI/USER/MCP)

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
                # Record failed execution log
                if context.session:
                    from app.repositories.rule_repository import ExecutionLogRepository

                    repo = ExecutionLogRepository(context.session)
                    await repo.create(
                        type="ACTION",
                        name=f"{entity_type}.{action_name}",
                        entity_id=str(context.entity["id"]),
                        actor_name=actor_name,
                        actor_type=actor_type,
                        success=False,
                        detail={"error": precondition.on_failure},
                    )
                return ExecutionResult(success=False, error=precondition.on_failure)

        # All preconditions passed - apply effect if present
        changes = {}
        return_value = None
        if action.effect is not None:
            changes, return_value = await self._apply_effect(
                action.effect, evaluator, context
            )

        # Persist changes to database if any
        if changes and context.session:
            # Use PersistenceService to update properties safely via jsonb_set
            success = await PersistenceService.update_properties(
                context.session, entity_type, context.entity["id"], changes
            )

            # Emit events for rule engine if persistence succeeded
            if success and self.event_emitter:
                self._emit_update_events(
                    entity_type,
                    context.entity["id"],
                    changes,
                    context_entity=context.entity,
                    actor_name=actor_name,
                    actor_type=actor_type,
                )

        # Record execution log
        if context.session:
            from app.repositories.rule_repository import ExecutionLogRepository

            repo = ExecutionLogRepository(context.session)
            await repo.create(
                type="ACTION",
                name=f"{entity_type}.{action_name}",
                entity_id=str(context.entity["id"]),
                actor_name=actor_name,
                actor_type=actor_type,
                success=True,
                detail={"changes": changes, "return_value": return_value},
            )

        return ExecutionResult(
            success=True, error=None, changes=changes, return_value=return_value
        )

    def _emit_update_events(
        self,
        entity_type: str,
        entity_id: str,
        changes: dict[str, Any],
        context_entity: dict[str, Any] | None = None,
        actor_name: str | None = None,
        actor_type: str | None = None,
    ):
        """Emit UpdateEvent for each changed property.

        Args:
            entity_type: Entity label
            entity_id: Entity name property
            changes: Dictionary of properties that were updated
            context_entity: Original entity properties from context
            actor_name: Actor name
            actor_type: Actor type
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
                actor_name=actor_name,
                actor_type=actor_type,
            )
            self.event_emitter.emit(event)

    async def _apply_effect(
        self, effect: Any, evaluator: ExpressionEvaluator, context: EvaluationContext
    ) -> tuple[dict[str, Any], Any | None]:
        """Apply an effect block to the context.

        Args:
            effect: EffectBlock with statements
            evaluator: ExpressionEvaluator for evaluating values
            context: EvaluationContext to modify

        Returns:
            Tuple of (Dictionary of property changes, Return value if any)
        """
        changes = {}
        return_value = None

        if effect is None:
            return changes, return_value

        statements = getattr(effect, "statements", [])
        if not statements:
            return changes, return_value

        for statement in statements:
            if isinstance(statement, SetStatement):
                change = await self._apply_set_statement(statement, evaluator)
                changes.update(change)
            elif isinstance(statement, CallStatement):
                call_result = await self._apply_call_statement(
                    statement, evaluator, context
                )
                changes.update(call_result)
            elif isinstance(statement, ReturnStatement):
                return_value = await evaluator.evaluate(statement.value)

        return changes, return_value

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

    async def _apply_call_statement(
        self,
        statement: CallStatement,
        evaluator: ExpressionEvaluator,
        context: EvaluationContext,
    ) -> dict[str, Any]:
        """Execute a CALL statement: invoke a data product gRPC method.

        Args:
            statement: CallStatement with service/method/args
            evaluator: ExpressionEvaluator for evaluating argument expressions
            context: EvaluationContext for storing result variables

        Returns:
            Empty dict (CALL itself doesn't modify graph; SET does)
        """
        import logging
        from sqlalchemy import select
        from app.models.data_product import DataProduct
        from app.services.grpc_client import DynamicGrpcClient

        logger = logging.getLogger(__name__)

        session = context.session
        if not session:
            raise RuntimeError("Database session required for CALL statement")

        # 1. Find DataProduct by service_name (exact match, then suffix match)
        result = await session.execute(
            select(DataProduct).where(
                DataProduct.service_name == statement.service_name,
                DataProduct.is_active == True,
            )
        )
        product = result.scalar_one_or_none()

        if not product:
            # Try suffix match: e.g. "OrderService" matches "erp.OrderService"
            result = await session.execute(
                select(DataProduct).where(
                    DataProduct.service_name.endswith(f".{statement.service_name}"),
                    DataProduct.is_active == True,
                )
            )
            product = result.scalar_one_or_none()

        if not product:
            # Try name match for better UX in Business Editor
            result = await session.execute(
                select(DataProduct).where(
                    DataProduct.name == statement.service_name,
                    DataProduct.is_active == True,
                )
            )
            product = result.scalar_one_or_none()

        if not product:
            raise ValueError(
                f"Data product with service '{statement.service_name}' not found"
            )

        # 2. Evaluate argument expressions
        request_data = {}
        for field_name, expr in statement.arguments.items():
            request_data[field_name] = await evaluator.evaluate(expr)

        logger.info(
            f"CALL {statement.service_name}.{statement.method_name} "
            f"args={statement.arguments} request_data={request_data}"
        )

        # 3. Call gRPC method
        async with DynamicGrpcClient(product.grpc_host, product.grpc_port) as client:
            response = await client.call_method(
                product.service_name,
                statement.method_name,
                request_data,
            )

        logger.info(
            f"CALL {statement.service_name}.{statement.method_name} "
            f"response: {response}"
        )

        # 4. Store result in context variables if INTO was specified
        if statement.result_var and response:
            context.variables[statement.result_var] = response

        return {}  # CALL doesn't directly modify graph properties
