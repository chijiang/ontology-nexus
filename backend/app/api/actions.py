"""REST API endpoints for action management."""

from fastapi import APIRouter, Depends, HTTPException
from typing import Any
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.rule_engine.action_registry import ActionRegistry
from app.rule_engine.action_executor import ActionExecutor
from app.rule_engine.context import EvaluationContext
from app.rule_engine.parser import RuleParser
from app.rule_engine.models import ActionDef
from app.api.deps import get_current_user
from app.models.user import User
from app.core.database import get_db
from app.repositories.rule_repository import ActionDefinitionRepository

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


class ActionUploadRequest(BaseModel):
    """Request model for uploading an action definition."""

    name: str = Field(..., description="Action name (e.g., 'PurchaseOrder.submit')")
    entity_type: str = Field(..., description="Entity type (e.g., 'PurchaseOrder')")
    dsl_content: str = Field(..., description="DSL content of the action")
    is_active: bool = Field(default=True, description="Whether the action is active")


class ActionInfo(BaseModel):
    """Information about an action."""

    entity_type: str
    action_name: str
    parameters: list[dict[str, Any]]
    precondition_count: int
    has_effect: bool


class ActionDefinitionResponse(BaseModel):
    """Response model for action definition."""

    id: int
    name: str
    entity_type: str
    is_active: bool


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


@router.post("/")
async def upload_action(
    request: ActionUploadRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    registry: ActionRegistry = Depends(get_action_registry),
) -> dict[str, Any]:
    """Upload a new action definition.

    Args:
        request: Action upload request
        current_user: Current authenticated user
        db: Database session
        registry: Action registry instance

    Returns:
        Uploaded action details

    Raises:
        HTTPException: If action already exists or parsing fails
    """
    repo = ActionDefinitionRepository(db)

    # Check if action already exists
    if await repo.exists(request.name):
        raise HTTPException(
            status_code=400,
            detail=f"Action '{request.name}' already exists"
        )

    try:
        # Validate by parsing
        parser = RuleParser()
        parsed = parser.parse(request.dsl_content)
        action_defs = [item for item in parsed if isinstance(item, ActionDef)]

        if not action_defs:
            raise HTTPException(
                status_code=400,
                detail="No valid ACTION definition found in content"
            )

        # Save to database
        action = await repo.create(
            name=request.name,
            entity_type=request.entity_type,
            dsl_content=request.dsl_content,
            is_active=request.is_active
        )

        # Load and register in memory
        for action_def in action_defs:
            try:
                registry.register(action_def)
            except ValueError:
                # Action already in registry, skip
                pass

        return {
            "message": "Action uploaded successfully",
            "action": {
                "id": action.id,
                "name": action.name,
                "entity_type": action.entity_type,
                "is_active": action.is_active
            }
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Check if it's a parsing error from Lark
        error_type = type(e).__name__
        if "Unexpected" in error_type or "Visit" in error_type:
            raise HTTPException(status_code=400, detail=f"Invalid DSL: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to upload action: {str(e)}")


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


@router.get("/definitions")
async def list_action_definitions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List all action definitions from database.

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        Dictionary with list of all action definitions
    """
    repo = ActionDefinitionRepository(db)
    actions = await repo.list_all()

    return {
        "actions": [
            {
                "id": action.id,
                "name": action.name,
                "entity_type": action.entity_type,
                "is_active": action.is_active,
                "created_at": action.created_at.isoformat(),
                "updated_at": action.updated_at.isoformat()
            }
            for action in actions
        ],
        "count": len(actions)
    }


@router.get("/definitions/{name}")
async def get_action_definition(
    name: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get an action definition by name.

    Args:
        name: Action name
        current_user: Current authenticated user
        db: Database session

    Returns:
        Action definition details

    Raises:
        HTTPException: If action is not found
    """
    repo = ActionDefinitionRepository(db)
    action = await repo.get_by_name(name)

    if action is None:
        raise HTTPException(status_code=404, detail=f"Action '{name}' not found")

    return {
        "id": action.id,
        "name": action.name,
        "entity_type": action.entity_type,
        "dsl_content": action.dsl_content,
        "is_active": action.is_active,
        "created_at": action.created_at.isoformat(),
        "updated_at": action.updated_at.isoformat()
    }


@router.delete("/definitions/{name}")
async def delete_action_definition(
    name: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Delete an action definition.

    Args:
        name: Action name
        current_user: Current authenticated user
        db: Database session

    Returns:
        Success message

    Raises:
        HTTPException: If action is not found
    """
    repo = ActionDefinitionRepository(db)

    if not await repo.exists(name):
        raise HTTPException(status_code=404, detail=f"Action '{name}' not found")

    await repo.delete(name)

    return {
        "message": f"Action '{name}' deleted successfully"
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
