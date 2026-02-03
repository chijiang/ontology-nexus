"""REST API endpoints for rule management."""

from fastapi import APIRouter, Depends, HTTPException
from typing import Any
from pydantic import BaseModel, Field
from app.rule_engine.rule_registry import RuleRegistry
from app.services.rule_storage import RuleStorage
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/rules", tags=["rules"])

# Global registries (initialized in main.py)
_rule_registry: RuleRegistry | None = None
_rule_storage: RuleStorage | None = None


def init_rules_api(registry: RuleRegistry, storage: RuleStorage):
    """Initialize the rules API with registries.

    Args:
        registry: RuleRegistry instance
        storage: RuleStorage instance
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


def get_rule_storage() -> RuleStorage:
    """Get the rule storage instance.

    Returns:
        RuleStorage instance

    Raises:
        HTTPException: If storage is not initialized
    """
    if _rule_storage is None:
        raise HTTPException(status_code=500, detail="Rule storage not initialized")
    return _rule_storage


class RuleUploadRequest(BaseModel):
    """Request model for uploading a rule."""

    name: str = Field(..., description="Unique rule name")
    dsl_content: str = Field(..., description="DSL content of the rule")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Optional metadata")


class RuleInfo(BaseModel):
    """Information about a rule."""

    name: str
    priority: int
    trigger: dict[str, Any]
    metadata: dict[str, Any]


@router.get("/")
async def list_rules(
    current_user: User = Depends(get_current_user),
    storage: RuleStorage = Depends(get_rule_storage),
) -> dict[str, Any]:
    """List all rules.

    Args:
        current_user: Current authenticated user
        storage: Rule storage instance

    Returns:
        Dictionary with list of all rules
    """
    rules = storage.list_rules()

    return {
        "rules": rules,
        "count": len(rules)
    }


@router.get("/{name}")
async def get_rule(
    name: str,
    current_user: User = Depends(get_current_user),
    storage: RuleStorage = Depends(get_rule_storage),
) -> dict[str, Any]:
    """Get details of a specific rule.

    Args:
        name: Rule name
        current_user: Current authenticated user
        storage: Rule storage instance

    Returns:
        Rule details

    Raises:
        HTTPException: If rule is not found
    """
    rule_data = storage.load_rule(name)

    if rule_data is None:
        raise HTTPException(status_code=404, detail=f"Rule '{name}' not found")

    return rule_data


@router.post("/")
async def upload_rule(
    request: RuleUploadRequest,
    current_user: User = Depends(get_current_user),
    storage: RuleStorage = Depends(get_rule_storage),
    registry: RuleRegistry = Depends(get_rule_registry),
) -> dict[str, Any]:
    """Upload a new rule.

    Args:
        request: Rule upload request
        current_user: Current authenticated user
        storage: Rule storage instance
        registry: Rule registry instance

    Returns:
        Uploaded rule details

    Raises:
        HTTPException: If rule already exists or parsing fails
    """
    # Check if rule already exists
    if storage.rule_exists(request.name):
        raise HTTPException(
            status_code=400,
            detail=f"Rule '{request.name}' already exists"
        )

    try:
        # Save to storage
        rule_data = storage.save_rule(
            name=request.name,
            dsl_content=request.dsl_content,
            metadata=request.metadata
        )

        # Load and register in registry
        from app.rule_engine.parser import RuleParser
        from app.rule_engine.models import RuleDef

        parser = RuleParser()
        parsed = parser.parse(request.dsl_content)
        rule_defs = [item for item in parsed if isinstance(item, RuleDef)]

        if rule_defs:
            # Register in the in-memory registry
            for rule in rule_defs:
                try:
                    registry.register(rule)
                except ValueError:
                    # Rule already in registry, skip
                    pass

        return {
            "message": "Rule uploaded successfully",
            "rule": rule_data
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
    storage: RuleStorage = Depends(get_rule_storage),
) -> dict[str, Any]:
    """Delete a rule.

    Args:
        name: Rule name
        current_user: Current authenticated user
        storage: Rule storage instance

    Returns:
        Success message

    Raises:
        HTTPException: If rule is not found
    """
    if not storage.rule_exists(name):
        raise HTTPException(status_code=404, detail=f"Rule '{name}' not found")

    storage.delete_rule(name)

    return {
        "message": f"Rule '{name}' deleted successfully"
    }
