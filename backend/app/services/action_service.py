"""Shared action service layer.

Provides common business logic for action operations, used by both
the MCP action server and the agent_tools action tools to ensure
consistency and avoid code duplication.
"""

import logging
from typing import Any

from app.rule_engine.action_registry import ActionRegistry
from app.rule_engine.action_executor import ActionExecutor, ExecutionResult
from app.rule_engine.context import EvaluationContext
from app.rule_engine.evaluator import ExpressionEvaluator
from app.rule_engine.models import ActionDef
from app.services.pg_graph_storage import PGGraphStorage

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Registry loading
# ---------------------------------------------------------------------------


async def load_actions_from_db(registry: ActionRegistry) -> int:
    """Load active ActionDefinition records from the database into a registry.

    Args:
        registry: ActionRegistry to populate

    Returns:
        Number of actions loaded
    """
    from app.core.database import async_session
    from app.models.rule import ActionDefinition
    from app.rule_engine.models import ActionDef
    from app.rule_engine.parser import RuleParser
    from sqlalchemy import select

    count = 0
    parser = RuleParser()

    async with async_session() as session:
        result = await session.execute(
            select(ActionDefinition).where(ActionDefinition.is_active == True)
        )
        db_actions = result.scalars().all()

        for db_action in db_actions:
            try:
                parsed = parser.parse(db_action.dsl_content)
                for item in parsed:
                    if isinstance(item, ActionDef):
                        registry.register(item)
                        count += 1
                logger.info(f"Loaded action '{db_action.name}' from database")
            except Exception as e:
                logger.warning(f"Failed to load action '{db_action.name}': {e}")

    logger.info(f"Loaded {count} actions from database into registry")
    return count


# ---------------------------------------------------------------------------
# Entity data retrieval
# ---------------------------------------------------------------------------


async def get_entity_data(
    session: Any,
    entity_type: str,
    entity_id: str,
) -> dict[str, Any] | None:
    """Retrieve entity data from the database.

    Args:
        session: Active database session
        entity_type: Entity type/label
        entity_id: Entity name/identifier

    Returns:
        Entity properties dict, or None if not found
    """
    storage = PGGraphStorage(session)
    results = await storage.search_instances(entity_id, entity_type, limit=1)
    if results:
        return results[0].get("properties", {})
    return None


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def format_action_as_dict(action: ActionDef) -> dict[str, Any]:
    """Format an ActionDef as a serializable dict (for MCP / API).

    Args:
        action: ActionDef to format

    Returns:
        Dictionary representation of the action
    """
    return {
        "name": action.action_name,
        "entity_type": action.entity_type,
        "description": action.description,
        "parameters": [
            {"name": p.name, "type": p.param_type, "optional": p.optional}
            for p in (action.parameters or [])
        ],
        "preconditions": [
            {"condition": p.condition, "on_failure": p.on_failure}
            for p in (action.preconditions or [])
        ],
        "has_effect": action.effect is not None,
    }


def format_action_as_text(action: ActionDef) -> str:
    """Format an ActionDef as human-readable text (for LLM agent).

    Args:
        action: ActionDef to format

    Returns:
        Formatted string representation
    """
    output = [f"Action: {action.entity_type}.{action.action_name}"]

    # Parameters
    if action.parameters:
        output.append("  Parameters:")
        for param in action.parameters:
            optional = "optional" if param.optional else "required"
            output.append(f"    - {param.name} ({param.param_type}, {optional})")
    else:
        output.append("  Parameters: None")

    # Preconditions
    if action.preconditions:
        output.append("  Preconditions:")
        for i, precond in enumerate(action.preconditions, 1):
            name = precond.name or f"Precondition {i}"
            output.append(f"    {i}. {name}: {precond.on_failure}")
    else:
        output.append("  Preconditions: None")

    # Effect
    if action.effect:
        output.append("  Effect: Yes (modifies state)")
    else:
        output.append("  Effect: None (read-only)")

    return "\n".join(output)


# ---------------------------------------------------------------------------
# Action listing / lookup
# ---------------------------------------------------------------------------


def list_actions(
    registry: ActionRegistry,
    entity_type: str,
) -> list[ActionDef]:
    """List actions for an entity type.

    Args:
        registry: ActionRegistry to query
        entity_type: Entity type to filter by

    Returns:
        List of ActionDef objects
    """
    return registry.list_by_entity(entity_type)


def get_action_detail(
    registry: ActionRegistry,
    entity_type: str,
    action_name: str,
) -> ActionDef | None:
    """Look up a single action.

    Args:
        registry: ActionRegistry to query
        entity_type: Entity type
        action_name: Action name

    Returns:
        ActionDef or None
    """
    return registry.lookup(entity_type, action_name)


# ---------------------------------------------------------------------------
# Precondition validation
# ---------------------------------------------------------------------------


async def validate_preconditions(
    registry: ActionRegistry,
    session: Any,
    entity_type: str,
    action_name: str,
    entity_id: str,
) -> dict[str, Any]:
    """Validate action preconditions against an entity.

    Args:
        registry: ActionRegistry to look up the action
        session: Database session for entity data
        entity_type: Entity type
        action_name: Action name
        entity_id: Entity identifier

    Returns:
        Dict with 'valid' bool, optional 'error' or 'errors' list
    """
    action = registry.lookup(entity_type, action_name)
    if not action:
        return {
            "valid": False,
            "error": f"Action {entity_type}.{action_name} not found",
        }

    entity_data = await get_entity_data(session, entity_type, entity_id)
    if not entity_data:
        return {"valid": False, "error": f"Entity {entity_type} {entity_id} not found"}

    context = EvaluationContext(
        entity={"id": entity_id, **entity_data},
        session=session,
    )
    evaluator = ExpressionEvaluator(context)

    failures = []
    for precondition in action.preconditions or []:
        try:
            result = await evaluator.evaluate(precondition.condition)
            if not result:
                failures.append(precondition.on_failure)
        except Exception as e:
            failures.append(f"Error evaluating: {e}")

    if failures:
        return {"valid": False, "errors": failures}
    return {"valid": True}


# ---------------------------------------------------------------------------
# Action execution
# ---------------------------------------------------------------------------


async def execute_single_action(
    executor: ActionExecutor,
    session: Any,
    entity_type: str,
    action_name: str,
    entity_id: str,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute a single action on an entity.

    Args:
        executor: ActionExecutor instance
        session: Active database session (will be committed on success)
        entity_type: Entity type
        action_name: Action name
        entity_id: Entity identifier
        params: Optional action parameters

    Returns:
        Dict with 'success', 'error', 'changes' keys
    """
    entity_data = await get_entity_data(session, entity_type, entity_id)
    if not entity_data:
        return {
            "success": False,
            "error": f"Entity {entity_type} {entity_id} not found",
        }

    context = EvaluationContext(
        entity={"id": entity_id, **entity_data},
        variables=params or {},
        session=session,
    )

    try:
        result = await executor.execute(entity_type, action_name, context)
        return {
            "success": result.success,
            "error": result.error,
            "changes": result.changes,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
