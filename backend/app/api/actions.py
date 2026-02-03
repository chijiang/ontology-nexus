"""REST API endpoints for action management."""

from fastapi import APIRouter, Depends, HTTPException
from typing import Any
from pydantic import BaseModel, Field
from app.rule_engine.action_registry import ActionRegistry
from app.rule_engine.action_executor import ActionExecutor
from app.rule_engine.context import EvaluationContext
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/actions", tags=["actions"])

# Global registries (initialized in main.py)
_action_registry: ActionRegistry | None = None
_action_executor: ActionExecutor | None = None


def init_actions_api(registry: ActionRegistry, executor: ActionExecutor):
    """Initialize the actions API with registries.

    Args:
        registry: ActionRegistry instance
        executor: ActionExecutor instance
    """
    global _action_registry, _action_executor
    _action_registry = registry
    _action_executor = executor


def get_action_registry() -> ActionRegistry:
    """Get the action registry instance.

    Returns:
        ActionRegistry instance

    Raises:
        HTTPException: If registry is not initialized
    """
    if _action_registry is None:
        raise HTTPException(status_code=500, detail="Action registry not initialized")
    return _action_registry


def get_action_executor() -> ActionExecutor:
    """Get the action executor instance.

    Returns:
        ActionExecutor instance

    Raises:
        HTTPException: If executor is not initialized
    """
    if _action_executor is None:
        raise HTTPException(status_code=500, detail="Action executor not initialized")
    return _action_executor


class ActionExecutionRequest(BaseModel):
    """Request model for executing an action."""

    entity_id: str = Field(..., description="ID of the entity to execute action on")
    entity_data: dict[str, Any] = Field(default_factory=dict, description="Current entity data")
    params: dict[str, Any] = Field(default_factory=dict, description="Action parameters")


class ActionInfo(BaseModel):
    """Information about an action."""

    entity_type: str
    action_name: str
    parameters: list[dict[str, Any]]
    precondition_count: int
    has_effect: bool


@router.post("/{entity_type}/{action_name}")
async def execute_action(
    entity_type: str,
    action_name: str,
    request: ActionExecutionRequest,
    current_user: User = Depends(get_current_user),
    executor: ActionExecutor = Depends(get_action_executor),
) -> dict[str, Any]:
    """Execute an action on an entity.

    Args:
        entity_type: The entity type (e.g., "PurchaseOrder")
        action_name: The action name (e.g., "submit")
        request: Action execution request
        current_user: Current authenticated user
        executor: Action executor instance

    Returns:
        Execution result with success status and changes

    Raises:
        HTTPException: If action is not found
    """
    # Create evaluation context
    # Build entity dict with id and data
    entity = {
        "id": request.entity_id,
        **request.entity_data
    }

    context = EvaluationContext(
        entity=entity,
        old_values={},
        session=None,
        variables=request.params
    )

    # Execute the action
    result = executor.execute(entity_type, action_name, context)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)

    return {
        "success": True,
        "changes": result.changes,
        "message": f"Action {entity_type}.{action_name} executed successfully"
    }


@router.get("/")
async def list_actions(
    current_user: User = Depends(get_current_user),
    registry: ActionRegistry = Depends(get_action_registry),
) -> dict[str, Any]:
    """List all registered actions.

    Args:
        current_user: Current authenticated user
        registry: Action registry instance

    Returns:
        Dictionary with list of all actions
    """
    actions = registry.list_all()

    action_infos = []
    for action in actions:
        action_infos.append(ActionInfo(
            entity_type=action.entity_type,
            action_name=action.action_name,
            parameters=[
                {
                    "name": p.name,
                    "type": p.param_type,
                    "optional": p.optional
                }
                for p in (action.parameters or [])
            ],
            precondition_count=len(action.preconditions or []),
            has_effect=action.effect is not None
        ))

    return {
        "actions": action_infos,
        "count": len(action_infos)
    }


@router.get("/{entity_type}")
async def list_entity_actions(
    entity_type: str,
    current_user: User = Depends(get_current_user),
    registry: ActionRegistry = Depends(get_action_registry),
) -> dict[str, Any]:
    """List all actions for a specific entity type.

    Args:
        entity_type: The entity type to filter by
        current_user: Current authenticated user
        registry: Action registry instance

    Returns:
        Dictionary with list of actions for the entity type
    """
    actions = registry.list_by_entity(entity_type)

    action_infos = []
    for action in actions:
        action_infos.append(ActionInfo(
            entity_type=action.entity_type,
            action_name=action.action_name,
            parameters=[
                {
                    "name": p.name,
                    "type": p.param_type,
                    "optional": p.optional
                }
                for p in (action.parameters or [])
            ],
            precondition_count=len(action.preconditions or []),
            has_effect=action.effect is not None
        ))

    return {
        "entity_type": entity_type,
        "actions": action_infos,
        "count": len(action_infos)
    }
