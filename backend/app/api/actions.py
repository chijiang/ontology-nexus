"""REST API endpoints for action management."""

from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Any
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.rule_engine.action_registry import ActionRegistry
from app.rule_engine.action_executor import ActionExecutor
from app.rule_engine.context import EvaluationContext
from app.services.pg_graph_storage import PGGraphStorage
from app.services.permission_service import PermissionService
from app.rule_engine.parser import RuleParser
from app.rule_engine.models import ActionDef, CallStatement
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

    entity_id: str | int = Field(
        ..., description="ID of the entity to execute action on"
    )
    entity_data: dict[str, Any] = Field(
        default_factory=dict, description="Current entity data"
    )
    params: dict[str, Any] = Field(
        default_factory=dict, description="Action parameters"
    )


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
    has_call: bool = False
    description: str | None = None


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
    fastapi_request: Request,
    current_user: User = Depends(get_current_user),
    executor: ActionExecutor = Depends(get_action_executor),
    db: AsyncSession = Depends(get_db),
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
        HTTPException: If action is not found or user lacks permission
    """
    # 检查权限
    has_permission = await PermissionService.check_action_permission(
        db, current_user, entity_type, action_name
    )
    if not has_permission:
        raise HTTPException(
            status_code=403, detail="No permission to execute this action"
        )
    # Create evaluation context
    # Build entity dict with id and data

    # Resolve entity_id (strictly database ID)
    entity_id_str = str(request.entity_id)
    if not entity_id_str.isdigit():
        raise HTTPException(
            status_code=400,
            detail=f"Invalid entity_id: '{request.entity_id}'. Must be a numeric database ID.",
        )

    storage = PGGraphStorage(db)
    resolved_entity = await storage.get_entity_by_id(int(request.entity_id))

    if not resolved_entity or resolved_entity.get("entity_type") != entity_type:
        raise HTTPException(
            status_code=404,
            detail=f"Entity {entity_type} with ID {request.entity_id} not found",
        )

    # Use resolved entity data and ensure ID is integer
    entity = {
        **resolved_entity["properties"],
        **request.entity_data,
        "id": resolved_entity["id"],
        "__type__": entity_type,
    }

    # Get database session from app state
    session = db

    context = EvaluationContext(
        entity=entity, old_values={}, session=session, variables=request.params
    )

    # Execute the action
    result = await executor.execute(
        entity_type,
        action_name,
        context,
        actor_name=current_user.username,
        actor_type="USER",
    )

    import logging

    logger = logging.getLogger(__name__)

    if not result.success:
        logger.warning(f"Action {entity_type}.{action_name} failed: {result.error}")
        return {
            "success": False,
            "message": result.error,
            "error": result.error,
            "changes": {},
        }

    logger.info(f"Action {entity_type}.{action_name} succeeded on {request.entity_id}")

    # Success! Now persist changes if any
    if result.changes:

        # Get event emitter
        event_emitter = getattr(fastapi_request.app.state, "event_emitter", None)

        # Apply updates via PGGraphStorage to trigger rules
        storage = PGGraphStorage(db, event_emitter=event_emitter)
        await storage.update_entity(entity_type, request.entity_id, result.changes)

    return {
        "success": True,
        "changes": result.changes,
        "message": f"Action {entity_type}.{action_name} executed successfully",
    }


@router.post("")
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
            status_code=400, detail=f"Action '{request.name}' already exists"
        )

    try:
        # Validate by parsing
        parser = RuleParser()
        parsed = parser.parse(request.dsl_content)
        action_defs = [item for item in parsed if isinstance(item, ActionDef)]

        if not action_defs:
            raise HTTPException(
                status_code=400, detail="No valid ACTION definition found in content"
            )

        # Save to database
        action = await repo.create(
            name=request.name,
            entity_type=request.entity_type,
            dsl_content=request.dsl_content,
            is_active=request.is_active,
            description=action_defs[0].description if action_defs else None,
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
                "is_active": action.is_active,
            },
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Check if it's a parsing error from Lark
        error_type = type(e).__name__
        if "Unexpected" in error_type or "Visit" in error_type:
            raise HTTPException(status_code=400, detail=f"Invalid DSL: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to upload action: {str(e)}"
        )


@router.get("")
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
        # Check if effect contains CALL statements
        _has_call = False
        if action.effect and hasattr(action.effect, "statements"):
            _has_call = any(
                isinstance(s, CallStatement) for s in action.effect.statements
            )

        action_infos.append(
            ActionInfo(
                entity_type=action.entity_type,
                action_name=action.action_name,
                parameters=[
                    {"name": p.name, "type": p.param_type, "optional": p.optional}
                    for p in (action.parameters or [])
                    if p is not None
                ],
                precondition_count=len(action.preconditions or []),
                has_effect=action.effect is not None,
                has_call=_has_call,
                description=(
                    action.description if hasattr(action, "description") else None
                ),
            )
        )

    return {"actions": action_infos, "count": len(action_infos)}


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
                "updated_at": action.updated_at.isoformat(),
                "description": action.description,
            }
            for action in actions
        ],
        "count": len(actions),
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
        "description": action.description,
        "created_at": action.created_at.isoformat(),
        "updated_at": action.updated_at.isoformat(),
    }


class ActionUpdateRequest(BaseModel):
    """Request model for updating an action definition."""

    dsl_content: str = Field(..., description="DSL content of the action")
    is_active: bool = Field(default=True, description="Whether the action is active")


@router.put("/definitions/{name}")
async def update_action_definition(
    name: str,
    request: ActionUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    registry: ActionRegistry = Depends(get_action_registry),
) -> dict[str, Any]:
    """Update an existing action definition.

    Args:
        name: Action name
        request: Action update request
        current_user: Current authenticated user
        db: Database session
        registry: Action registry instance

    Returns:
        Updated action details

    Raises:
        HTTPException: If action is not found or parsing fails
    """
    repo = ActionDefinitionRepository(db)

    # Check if action exists
    existing = await repo.get_by_name(name)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Action '{name}' not found")

    try:
        # Validate by parsing
        parser = RuleParser()
        parsed = parser.parse(request.dsl_content)
        action_defs = [item for item in parsed if isinstance(item, ActionDef)]

        if not action_defs:
            raise HTTPException(
                status_code=400, detail="No valid ACTION definition found in content"
            )

        # Unregister the existing action from memory to prevent stale cache
        # if the entity type or action name changed in the new DSL.
        registry.unregister(existing.entity_type, existing.name)

        # Update in database
        action = await repo.update(
            name=name,
            dsl_content=request.dsl_content,
            is_active=request.is_active,
            description=action_defs[0].description if action_defs else None,
        )

        # Re-register in the in-memory registry
        for action_def in action_defs:
            registry.register(action_def)  # This will overwrite existing

        return {
            "message": "Action updated successfully",
            "action": {
                "id": action.id,
                "name": action.name,
                "entity_type": action.entity_type,
                "is_active": action.is_active,
            },
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Check if it's a parsing error from Lark
        error_type = type(e).__name__
        if "Unexpected" in error_type or "Visit" in error_type:
            raise HTTPException(status_code=400, detail=f"Invalid DSL: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to update action: {str(e)}"
        )


@router.delete("/definitions/{name}")
async def delete_action_definition(
    name: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    registry: ActionRegistry = Depends(get_action_registry),
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

    # Get the action info before deleting so we can unregister it
    action = await repo.get_by_name(name)
    if action:
        registry.unregister(action.entity_type, action.name)

    await repo.delete(name)

    return {"message": f"Action '{name}' deleted successfully"}


@router.get("/{entity_type}")
async def list_entity_actions(
    entity_type: str,
    current_user: User = Depends(get_current_user),
    registry: ActionRegistry = Depends(get_action_registry),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List all actions for a specific entity type.

    Args:
        entity_type: The entity type to filter by
        current_user: Current authenticated user
        registry: Action registry instance
        db: Database session

    Returns:
        Dictionary with list of actions for the entity type (filtered by permissions)
    """
    # 获取用户可执行的actions
    user_actions = await PermissionService.get_accessible_actions(db, current_user)

    # 获取该实体类型的所有actions
    actions = registry.list_by_entity(entity_type)

    # 获取用户对该实体类型有权限的actions
    allowed_actions = (
        user_actions.get(entity_type, []) if not current_user.is_admin else []
    )

    action_infos = []
    for action in actions:
        # 如果不是admin且用户没有该action权限，跳过
        if not current_user.is_admin and action.action_name not in allowed_actions:
            continue

        # Check if effect contains CALL statements
        _has_call = False
        if action.effect and hasattr(action.effect, "statements"):
            _has_call = any(
                isinstance(s, CallStatement) for s in action.effect.statements
            )

        action_infos.append(
            ActionInfo(
                entity_type=action.entity_type,
                action_name=action.action_name,
                parameters=[
                    {"name": p.name, "type": p.param_type, "optional": p.optional}
                    for p in (action.parameters or [])
                    if p is not None
                ],
                precondition_count=len(action.preconditions or []),
                has_effect=action.effect is not None,
                has_call=_has_call,
                description=action.description,
            )
        )

    return {
        "entity_type": entity_type,
        "actions": action_infos,
        "count": len(action_infos),
    }
