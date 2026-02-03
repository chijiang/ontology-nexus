"""REST API endpoints for rule management."""

from fastapi import APIRouter, Depends, HTTPException
from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.rule_engine.rule_registry import RuleRegistry
from app.rule_engine.parser import RuleParser
from app.rule_engine.models import RuleDef
from app.api.deps import get_current_user
from app.models.user import User
from app.core.database import get_db
from app.repositories.rule_repository import RuleRepository
from app.services.rule_storage import RuleStorage

router = APIRouter(prefix="/api/rules", tags=["rules"])

# Global registries (initialized in main.py)
_rule_registry: RuleRegistry | None = None
_rule_storage: RuleStorage | None = None


def init_rules_api(registry: RuleRegistry, storage: RuleStorage):
    """Initialize the rules API with registries.

    Args:
        registry: RuleRegistry instance
        storage: RuleStorage instance (for file-based migration)
    """
    global _rule_registry, _rule_storage
    _rule_registry = registry
    _rule_storage = storage


def get_rule_registry() -> RuleRegistry:
    """Get the rule registry instance.

    Returns:
        RuleRegistry instance

    Raises:
        HTTPException: If registry is not initialized
    """
    if _rule_registry is None:
        raise HTTPException(status_code=500, detail="Rule registry not initialized")
    return _rule_registry


class RuleUploadRequest(BaseModel):
    """Request model for uploading a rule."""

    name: str = Field(..., description="Unique rule name")
    dsl_content: str = Field(..., description="DSL content of the rule")
    priority: int = Field(default=0, description="Rule priority")
    is_active: bool = Field(default=True, description="Whether the rule is active")


class RuleInfo(BaseModel):
    """Information about a rule."""

    id: int
    name: str
    priority: int
    trigger_type: str
    trigger_entity: str
    trigger_property: str | None
    is_active: bool
    created_at: str
    updated_at: str


class MigrationResponse(BaseModel):
    """Response model for migration operation."""

    migrated: int
    skipped: int
    failed: int
    errors: list[str]


@router.get("/")
async def list_rules(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List all rules.

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        Dictionary with list of all rules
    """
    repo = RuleRepository(db)
    rules = await repo.list_all()

    return {
        "rules": [
            {
                "id": rule.id,
                "name": rule.name,
                "priority": rule.priority,
                "trigger": {
                    "type": rule.trigger_type,
                    "entity": rule.trigger_entity,
                    "property": rule.trigger_property
                },
                "is_active": rule.is_active,
                "created_at": rule.created_at.isoformat(),
                "updated_at": rule.updated_at.isoformat()
            }
            for rule in rules
        ],
        "count": len(rules)
    }


@router.get("/{name}")
async def get_rule(
    name: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get details of a specific rule.

    Args:
        name: Rule name
        current_user: Current authenticated user
        db: Database session

    Returns:
        Rule details

    Raises:
        HTTPException: If rule is not found
    """
    repo = RuleRepository(db)
    rule = await repo.get_by_name(name)

    if rule is None:
        raise HTTPException(status_code=404, detail=f"Rule '{name}' not found")

    return {
        "id": rule.id,
        "name": rule.name,
        "dsl_content": rule.dsl_content,
        "priority": rule.priority,
        "trigger": {
            "type": rule.trigger_type,
            "entity": rule.trigger_entity,
            "property": rule.trigger_property
        },
        "is_active": rule.is_active,
        "created_at": rule.created_at.isoformat(),
        "updated_at": rule.updated_at.isoformat()
    }


@router.post("/")
async def upload_rule(
    request: RuleUploadRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    registry: RuleRegistry = Depends(get_rule_registry),
) -> dict[str, Any]:
    """Upload a new rule.

    Args:
        request: Rule upload request
        current_user: Current authenticated user
        db: Database session
        registry: Rule registry instance

    Returns:
        Uploaded rule details

    Raises:
        HTTPException: If rule already exists or parsing fails
    """
    repo = RuleRepository(db)

    # Check if rule already exists
    if await repo.exists(request.name):
        raise HTTPException(
            status_code=400,
            detail=f"Rule '{request.name}' already exists"
        )

    try:
        # Validate by parsing
        parser = RuleParser()
        parsed = parser.parse(request.dsl_content)
        rule_defs = [item for item in parsed if isinstance(item, RuleDef)]

        if not rule_defs:
            raise HTTPException(
                status_code=400,
                detail="No valid RULE definition found in content"
            )

        rule_def = rule_defs[0]

        # Extract trigger information
        trigger_type = rule_def.trigger.type.value
        trigger_entity = rule_def.trigger.entity_type
        trigger_property = rule_def.trigger.property

        # Save to database
        rule = await repo.create(
            name=request.name,
            dsl_content=request.dsl_content,
            trigger_type=trigger_type,
            trigger_entity=trigger_entity,
            trigger_property=trigger_property,
            priority=request.priority,
            is_active=request.is_active
        )

        # Register in the in-memory registry
        try:
            registry.register(rule_def)
        except ValueError:
            # Rule already in registry, skip
            pass

        return {
            "message": "Rule uploaded successfully",
            "rule": {
                "id": rule.id,
                "name": rule.name,
                "priority": rule.priority,
                "trigger": {
                    "type": rule.trigger_type,
                    "entity": rule.trigger_entity,
                    "property": rule.trigger_property
                },
                "is_active": rule.is_active
            }
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Check if it's a parsing error from Lark
        error_type = type(e).__name__
        if "Unexpected" in error_type or "Visit" in error_type:
            raise HTTPException(status_code=400, detail=f"Invalid DSL: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to upload rule: {str(e)}")


@router.delete("/{name}")
async def delete_rule(
    name: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Delete a rule.

    Args:
        name: Rule name
        current_user: Current authenticated user
        db: Database session

    Returns:
        Success message

    Raises:
        HTTPException: If rule is not found
    """
    repo = RuleRepository(db)

    if not await repo.exists(name):
        raise HTTPException(status_code=404, detail=f"Rule '{name}' not found")

    await repo.delete(name)

    return {
        "message": f"Rule '{name}' deleted successfully"
    }


@router.post("/migrate", response_model=MigrationResponse)
async def migrate_rules(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    registry: RuleRegistry = Depends(get_rule_registry),
) -> dict[str, Any]:
    """Migrate rules from file storage to database.

    This endpoint reads all rule files from the rules directory
    and imports them into the database. Existing rules in the
    database with the same name will be skipped.

    Args:
        current_user: Current authenticated user
        db: Database session
        registry: Rule registry instance

    Returns:
        Migration summary with counts and any errors
    """
    if _rule_storage is None:
        raise HTTPException(
            status_code=500,
            detail="Rule storage not initialized"
        )

    repo = RuleRepository(db)
    parser = RuleParser()

    migrated = 0
    skipped = 0
    failed = 0
    errors = []

    # Get all rules from file storage
    file_rules = _rule_storage.list_rules()

    for rule_data in file_rules:
        name = rule_data.get("name")
        if not name:
            failed += 1
            errors.append(f"Rule missing name: {rule_data}")
            continue

        # Check if already in database
        if await repo.exists(name):
            skipped += 1
            continue

        try:
            # Load full rule details
            rule_details = _rule_storage.load_rule(name)
            if not rule_details:
                failed += 1
                errors.append(f"Could not load rule: {name}")
                continue

            dsl_content = rule_details.get("dsl_content")
            if not dsl_content:
                failed += 1
                errors.append(f"Rule missing DSL content: {name}")
                continue

            # Parse and extract trigger info
            parsed = parser.parse(dsl_content)
            rule_defs = [item for item in parsed if isinstance(item, RuleDef)]

            if not rule_defs:
                failed += 1
                errors.append(f"No valid RULE definition found: {name}")
                continue

            rule_def = rule_defs[0]

            # Get priority from file or use default
            rule_info = rule_data.get("rule_info", {})
            priority = rule_info.get("priority", 0)

            # Create in database
            await repo.create(
                name=name,
                dsl_content=dsl_content,
                trigger_type=rule_def.trigger.type.value,
                trigger_entity=rule_def.trigger.entity_type,
                trigger_property=rule_def.trigger.property,
                priority=priority,
                is_active=True
            )

            # Register in memory
            try:
                registry.register(rule_def)
            except ValueError:
                pass  # Already registered

            migrated += 1

        except Exception as e:
            failed += 1
            errors.append(f"{name}: {str(e)}")

    return {
        "migrated": migrated,
        "skipped": skipped,
        "failed": failed,
        "errors": errors
    }


@router.post("/reload")
async def reload_rules(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    registry: RuleRegistry = Depends(get_rule_registry),
) -> dict[str, Any]:
    """Reload all rules from database into the in-memory registry.

    This endpoint clears the current registry and reloads all
    active rules from the database.

    Args:
        current_user: Current authenticated user
        db: Database session
        registry: Rule registry instance

    Returns:
        Reload summary
    """
    repo = RuleRepository(db)
    parser = RuleParser()

    # Get all active rules from database
    rules = await repo.list_active()

    loaded = 0
    failed = 0
    errors = []

    for rule in rules:
        try:
            parsed = parser.parse(rule.dsl_content)
            rule_defs = [item for item in parsed if isinstance(item, RuleDef)]

            if rule_defs:
                try:
                    registry.register(rule_defs[0])
                    loaded += 1
                except ValueError:
                    # Already registered
                    loaded += 1
            else:
                failed += 1
                errors.append(f"Failed to parse rule: {rule.name}")

        except Exception as e:
            failed += 1
            errors.append(f"{rule.name}: {str(e)}")

    return {
        "loaded": loaded,
        "failed": failed,
        "errors": errors,
        "message": f"Reloaded {loaded} rules from database"
    }
