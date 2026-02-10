"""MCP Action Server.

Exposes action operations as MCP tools using FastMCP.
Business logic is delegated to the shared action_service module.
"""

import logging
from typing import Any, List

from fastmcp import FastMCP

from app.core.database import async_session
from app.rule_engine.action_registry import ActionRegistry
from app.rule_engine.action_executor import ActionExecutor
from app.services import action_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("Action Server")

# Shared registry & executor — lazily loaded from DB
_action_registry: ActionRegistry | None = None
_action_executor: ActionExecutor | None = None
_loaded = False


async def _ensure_loaded():
    """Ensure the action registry is populated from the database."""
    global _action_registry, _action_executor, _loaded
    if _loaded:
        return
    _action_registry = ActionRegistry()
    _action_executor = ActionExecutor(registry=_action_registry)
    count = await action_service.load_actions_from_db(_action_registry)
    logger.info(f"MCP Action Server: loaded {count} actions from database")
    _loaded = True


def _get_registry() -> ActionRegistry:
    assert _action_registry is not None, "Registry not loaded"
    return _action_registry


def _get_executor() -> ActionExecutor:
    assert _action_executor is not None, "Executor not loaded"
    return _action_executor


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def list_available_actions(entity_type: str) -> list[dict[str, Any]]:
    """List available actions for a given entity type.

    Args:
        entity_type: The type of entity (e.g., PurchaseOrder, Supplier)
    """
    await _ensure_loaded()
    actions = action_service.list_actions(_get_registry(), entity_type)
    return [action_service.format_action_as_dict(a) for a in actions]


@mcp.tool()
async def get_action_details(
    entity_type: str, action_name: str
) -> dict[str, Any] | None:
    """Get details for a specific action.

    Args:
        entity_type: The type of entity
        action_name: The name of the action
    """
    await _ensure_loaded()
    action = action_service.get_action_detail(_get_registry(), entity_type, action_name)
    if action:
        return action_service.format_action_as_dict(action)
    return None


@mcp.tool()
async def validate_action_preconditions(
    entity_type: str, action_name: str, entity_id: str
) -> dict[str, Any]:
    """Validate if an action can be executed on an entity.

    Args:
        entity_type: The type of entity
        action_name: The name of the action
        entity_id: The ID of the entity instance
    """
    await _ensure_loaded()
    async with async_session() as session:
        return await action_service.validate_preconditions(
            _get_registry(), session, entity_type, action_name, entity_id
        )


@mcp.tool()
async def execute_action(
    entity_type: str,
    action_name: str,
    entity_id: str,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute an action on an entity.

    Args:
        entity_type: The type of entity
        action_name: The name of the action
        entity_id: The ID of the entity instance
        params: Optional parameters for the action
    """
    await _ensure_loaded()
    async with async_session() as session:
        result = await action_service.execute_single_action(
            _get_executor(), session, entity_type, action_name, entity_id, params
        )
        if result["success"]:
            await session.commit()
        return result


@mcp.tool()
async def batch_execute_action(
    entity_type: str,
    action_name: str,
    entity_ids: List[str],
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute an action on multiple entities.

    Args:
        entity_type: The type of entity
        action_name: The name of the action
        entity_ids: List of entity IDs
        params: Optional parameters for the action
    """
    await _ensure_loaded()
    results = []

    async with async_session() as session:
        for eid in entity_ids:
            res = await action_service.execute_single_action(
                _get_executor(), session, entity_type, action_name, eid, params
            )
            results.append({"id": eid, **res})

        await session.commit()

    return {"summary": "Batch execution completed", "results": results}
