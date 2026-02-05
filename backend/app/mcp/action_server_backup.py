from contextlib import asynccontextmanager
from typing import AsyncIterator, Any, List
import logging

from mcp.server.fastmcp import FastMCP
from neo4j import AsyncGraphDatabase

from app.core.config import settings
from app.services.agent_tools.action_tools import (
    ActionRegistry,
    ActionExecutor,
)
from app.rule_engine.models import ActionDef

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("Action Server")

# Initialize shared driver
driver = AsyncGraphDatabase.driver(
    settings.NEO4J_URI,
    auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD)
)

@asynccontextmanager
async def get_session():
    async with driver.session(database=settings.NEO4J_DATABASE) as session:
        yield session

# Initialize services
action_registry = ActionRegistry()
rules_dir = Path("backend/rules")
if rules_dir.exists():
    for dsl_file in rules_dir.glob("*.dsl"):
        try:
            action_registry.load_from_file(str(dsl_file))
            logger.info(f"Loaded rules from {dsl_file}")
        except Exception as e:
            logger.error(f"Failed to load rules from {dsl_file}: {e}")
else:
    logger.warning(f"Rules directory {rules_dir} not found")

async def get_executor() -> ActionExecutor:
     # We pass None for event_emitter for now as we don't have a global one here
     # If needed, we can instantiate one, but it might need more setup
     return ActionExecutor(registry=action_registry)

async def _get_entity_data(tx, entity_type: str, entity_id: str) -> dict[str, Any] | None:
    query = f"MATCH (n:`{entity_type}` {{name: $name}}) RETURN n"
    result = await tx.run(query, name=entity_id)
    record = await result.single()
    if record:
        node = record["n"]
        return dict(node)
    return None

# Helper to format action def to dict for serialization
def _format_action(action: ActionDef) -> dict[str, Any]:
    return {
        "name": action.name,
        "description": action.description,
        "parameters": action.parameters,
        "preconditions": [p.dict() for p in action.preconditions] if action.preconditions else []
    }

@mcp.tool()
async def list_available_actions(entity_type: str) -> list[dict[str, Any]]:
    """List available actions for a given entity type.

    Args:
        entity_type: The type of entity (e.g., PurchaseOrder, Supplier)
    """
    actions = action_registry.list_by_entity(entity_type)
    return [_format_action(a) for a in actions]

@mcp.tool()
async def get_action_details(entity_type: str, action_name: str) -> dict[str, Any] | None:
    """Get details for a specific action.

    Args:
        entity_type: The type of entity
        action_name: The name of the action
    """
    action = action_registry.lookup(entity_type, action_name)
    if action:
        return _format_action(action)
    return None

@mcp.tool()
async def validate_action_preconditions(entity_type: str, action_name: str, entity_id: str) -> dict[str, Any]:
    """Validate if an action can be executed on an entity.

    Args:
        entity_type: The type of entity
        action_name: The name of the action
        entity_id: The ID of the entity instance
    """
    executor = await get_executor()
    
    async with get_session() as session:
        # Get entity data
        entity_data = await session.execute_read(_get_entity_data, entity_type, entity_id)
        if not entity_data:
            return {"valid": False, "error": f"Entity {entity_type} {entity_id} not found"}
            
        # Create context
        from app.rule_engine.context import EvaluationContext
        context = EvaluationContext(
            entity=entity_data,
            extras={},
            session=session
        )
        
        # Check preconditions only (need to access executor internals or modify it)
        # ActionExecutor.execute does everything. 
        # We need a validate method on ActionExecutor or manually check.
        # Since I can't easily modify ActionExecutor right now, I'll replicate the check logic here
        
        action = action_registry.lookup(entity_type, action_name)
        if not action:
             return {"valid": False, "error": f"Action not found"}

        from app.rule_engine.evaluator import ExpressionEvaluator
        evaluator = ExpressionEvaluator(context)
        
        failures = []
        for precondition in action.preconditions:
            result = await evaluator.evaluate(precondition.condition)
            if not result:
                failures.append(precondition.on_failure)
                
        if failures:
            return {"valid": False, "errors": failures}
            
        return {"valid": True}

@mcp.tool()
async def execute_action(entity_type: str, action_name: str, entity_id: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Execute an action on an entity.

    Args:
        entity_type: The type of entity
        action_name: The name of the action
        entity_id: The ID of the entity instance
        params: Optional parameters for the action
    """
    executor = await get_executor()
    
    async with get_session() as session:
        # Get entity data
        entity_data = await session.execute_read(_get_entity_data, entity_type, entity_id)
        if not entity_data:
            return {"success": False, "error": f"Entity {entity_type} {entity_id} not found"}
            
        # Create context
        from app.rule_engine.context import EvaluationContext
        context = EvaluationContext(
            entity=entity_data,
            extras=params or {},
            session=session
        )
        
        result = await executor.execute(entity_type, action_name, context)
        return {
            "success": result.success, 
            "error": result.error, 
            "changes": result.changes
        }

@mcp.tool()
async def batch_execute_action(entity_type: str, action_name: str, entity_ids: List[str], params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Execute an action on multiple entities.

    Args:
        entity_type: The type of entity
        action_name: The name of the action
        entity_ids: List of entity IDs
        params: Optional parameters for the action
    """
    executor = await get_executor()
    results = []
    
    # Simple serial execution
    async with get_session() as session:
        for eid in entity_ids:
            try:
                # Get entity data
                entity_data = await session.execute_read(_get_entity_data, entity_type, eid)
                if not entity_data:
                    results.append({"id": eid, "success": False, "error": "Entity not found"})
                    continue

                # Create context
                from app.rule_engine.context import EvaluationContext
                context = EvaluationContext(
                    entity=entity_data,
                    extras=params or {},
                    session=session
                )
                
                res = await executor.execute(entity_type, action_name, context)
                results.append({
                    "id": eid, 
                    "success": res.success, 
                    "error": res.error,
                    "changes": res.changes
                })
            except Exception as e:
                 results.append({"id": eid, "success": False, "error": str(e)})
            
    return {"summary": "Batch execution completed", "results": results}
