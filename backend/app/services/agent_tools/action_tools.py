"""Action tools for the enhanced agent.

These tools enable the agent to execute actions on entity instances.
Business logic is delegated to the shared action_service module.
"""

import logging
from typing import Any, Callable, List
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from app.rule_engine.action_executor import ActionExecutor, ExecutionResult
from app.rule_engine.action_registry import ActionRegistry
from app.rule_engine.context import EvaluationContext
from app.rule_engine.models import ActionDef, Precondition
from app.services import action_service

logger = logging.getLogger(__name__)


class ListAvailableActionsInput(BaseModel):
    """Input for list_available_actions tool."""

    entity_type: str = Field(
        description="Entity type, e.g., PurchaseOrder, Supplier, Invoice"
    )


class GetActionDetailsInput(BaseModel):
    """Input for get_action_details tool."""

    entity_type: str = Field(description="Entity type, e.g., PurchaseOrder")
    action_name: str = Field(description="Action name, e.g., submit, makePayment")


class ValidateActionPreconditionsInput(BaseModel):
    """Input for validate_action_preconditions tool."""

    entity_type: str = Field(description="Entity type, e.g., PurchaseOrder")
    action_name: str = Field(description="Action name, e.g., submit")
    entity_id: str = Field(description="Entity ID (name property)")


class ExecuteActionInput(BaseModel):
    """Input for execute_action tool."""

    entity_type: str = Field(description="Entity type, e.g., PurchaseOrder")
    action_name: str = Field(description="Action name, e.g., submit")
    entity_id: str = Field(description="Entity ID (name property)")
    params: dict[str, Any] = Field(
        default_factory=dict, description="Optional action parameters"
    )


class BatchExecuteActionInput(BaseModel):
    """Input for batch_execute_action tool."""

    entity_type: str = Field(description="Entity type, e.g., PurchaseOrder")
    action_name: str = Field(description="Action name, e.g., submit")
    entity_ids: List[str] = Field(description="List of entity IDs")
    params: dict[str, Any] = Field(
        default_factory=dict, description="Optional shared parameters"
    )


def format_action_def(action: ActionDef) -> str:
    """Format an action definition for display.

    Delegates to action_service.format_action_as_text for consistency.

    Args:
        action: ActionDef to format

    Returns:
        Formatted string representation
    """
    return action_service.format_action_as_text(action)


async def _get_entity_data(
    entity_type: str, entity_id: str, get_session_func: Callable
) -> dict[str, Any]:
    """Get entity data from PostgreSQL.

    Delegates to action_service.get_entity_data.

    Args:
        entity_type: Entity type
        entity_id: Entity ID (name property)
        get_session_func: Function to get database session

    Returns:
        Entity data dict
    """
    session_cm = get_session_func()
    async with session_cm as session:
        data = await action_service.get_entity_data(session, entity_type, entity_id)
        return data or {}


def create_action_tools(
    get_session_func: Callable,
    action_executor: ActionExecutor,
    action_registry: ActionRegistry,
) -> List[StructuredTool]:
    """Create LangChain-compatible action tools.

    Args:
        get_session_func: Async function that returns a database session
        action_executor: ActionExecutor instance
        action_registry: ActionRegistry instance

    Returns:
        List of StructuredTool instances
    """

    async def list_available_actions(entity_type: str) -> str:
        """List all available actions for an entity type.

        Use this to understand what actions can be performed on entities.

        Args:
            entity_type: Entity type (e.g., PurchaseOrder, Supplier)

        Returns:
            List of available actions with their parameters and preconditions
        """
        actions = action_registry.list_by_entity(entity_type)

        if not actions:
            return f"No available actions for type '{entity_type}'"

        output = [f"Available actions for type '{entity_type}':\n"]
        for action in actions:
            output.append(format_action_def(action))
            output.append("")  # Empty line between actions

        return "\n".join(output)

    async def get_action_details(entity_type: str, action_name: str) -> str:
        """Get detailed information about a specific action.

        Args:
            entity_type: Entity type
            action_name: Action name

        Returns:
            Detailed action definition
        """
        action = action_registry.lookup(entity_type, action_name)

        if not action:
            return f"Action not found: {entity_type}.{action_name}"

        return format_action_def(action)

    async def validate_action_preconditions(
        entity_type: str, action_name: str, entity_id: str
    ) -> str:
        """Validate if an action can be executed on an entity.

        Checks all preconditions without executing the action.

        Args:
            entity_type: Entity type
            action_name: Action name
            entity_id: Entity ID

        Returns:
            Validation result with reasons for any failures
        """
        action = action_registry.lookup(entity_type, action_name)

        if not action:
            return f"Error: Action {entity_type}.{action_name} not found"

        # Get entity data
        try:
            entity_data = await _get_entity_data(
                entity_type, entity_id, get_session_func
            )
        except Exception as e:
            return f"Error: Unable to fetch data for entity '{entity_id}': {str(e)}"

        if not entity_data:
            return f"Error: Entity '{entity_id}' not found (Type: {entity_type})"

        # Create evaluation context
        session = None  # We won't execute, just validate
        context = EvaluationContext(
            entity={**entity_data, "id": entity_id},
            old_values={},
            session=session,
            variables={},
        )

        # Check preconditions
        from app.rule_engine.evaluator import ExpressionEvaluator

        evaluator = ExpressionEvaluator(context)

        output = [
            f"Validating action {entity_type}.{action_name} on entity {entity_id}:\n"
        ]

        all_passed = True
        for i, precond in enumerate(action.preconditions or [], 1):
            try:
                result = await evaluator.evaluate(precond.condition)
                status = "✓ Passed" if result else "✗ Failed"
                name = precond.name or f"Precondition {i}"
                output.append(f"  {i}. {name}: {status}")
                if not result:
                    output.append(f"     Reason: {precond.on_failure}")
                    all_passed = False
            except Exception as e:
                output.append(
                    f"  {i}. {precond.name or f'Precondition {i}'}: ✗ Error: {str(e)}"
                )
                all_passed = False

        if all_passed:
            output.append("\nResult: All preconditions passed, action can be executed")
        else:
            output.append("\nResult: Some preconditions failed, cannot execute action")

        return "\n".join(output)

    async def execute_action(
        entity_type: str,
        action_name: str,
        entity_id: str,
        params: dict[str, Any] | None = None,
    ) -> str:
        """Execute a single action on an entity instance.

        This checks all preconditions and executes the action if they pass.

        Args:
            entity_type: Entity type
            action_name: Action name
            entity_id: Entity ID
            params: Optional action parameters

        Returns:
            Execution result with success/failure and any changes
        """
        params = params or {}

        # Get entity data
        try:
            entity_data = await _get_entity_data(
                entity_type, entity_id, get_session_func
            )
        except Exception as e:
            return f"Error: Unable to fetch data for entity '{entity_id}': {str(e)}"

        if not entity_data:
            return f"Error: Entity '{entity_id}' not found (Type: {entity_type})"

        # Execute the action using the session from get_session_func
        session_cm = get_session_func()
        async with session_cm as session:
            context = EvaluationContext(
                entity={**entity_data, "id": entity_id},
                old_values={},
                session=session,
                variables=params,
            )
            result = await action_executor.execute(
                entity_type,
                action_name,
                context,
                actor_name="AI Assistant",
                actor_type="AI",
            )
            if result.success:
                await session.commit()
                parts = [
                    f"Action {entity_type}.{action_name} executed successfully on {entity_id}"
                ]
                if result.changes:
                    changes_str = ", ".join(
                        [f"{k}={v}" for k, v in result.changes.items()]
                    )
                    parts.append(f"Changes: {changes_str}")
                if result.return_value is not None:
                    import json

                    try:
                        rv_str = json.dumps(
                            result.return_value, ensure_ascii=False, indent=2
                        )
                    except Exception:
                        rv_str = str(result.return_value)
                    parts.append(f"Returned: {rv_str}")
                return "\n".join(parts)
            else:
                return f"Action {entity_type}.{action_name} failed on {entity_id}\nReason: {result.error}"

    async def batch_execute_action(
        entity_type: str,
        action_name: str,
        entity_ids: List[str],
        params: dict[str, Any] | None = None,
    ) -> str:
        """Execute an action on multiple entities concurrently (preferred for bulk).

        This is the recommended method for performing actions on multiple entities.
        Executes actions concurrently and returns a summary of results.

        Args:
            entity_type: Entity type
            action_name: Action name
            entity_ids: List of entity IDs
            params: Optional shared parameters

        Returns:
            Summary with success/failure breakdown
        """
        params = params or {}

        if not entity_ids:
            return "Error: No entity IDs provided"

        output = [
            f"Batch executing {entity_type}.{action_name} on {len(entity_ids)} entities...\n",
        ]

        # Import batch executor
        from app.services.batch_executor import BatchActionExecutor

        executor = BatchActionExecutor(
            action_executor=action_executor,
            get_session_func=get_session_func,
        )

        # Create execution specs
        executions = [
            {
                "entity_type": entity_type,
                "action_name": action_name,
                "entity_id": eid,
                "params": params,
            }
            for eid in entity_ids
        ]

        # Execute batch
        results = await executor.execute_batch(
            executions, actor_name="AI Assistant", actor_type="AI"
        )

        # Format results
        output.append(f"Total: {results.total}")
        output.append(f"Succeeded: {results.succeeded}")
        output.append(f"Failed: {results.failed}")
        output.append("")

        if results.successes:
            output.append("Successful entities:")
            for success in results.successes[:10]:  # Show first 10
                changes_str = ", ".join(
                    [f"{k}={v}" for k, v in success["changes"].items()]
                )
                output.append(f"  - {success['entity_id']}: {changes_str}")
            if len(results.successes) > 10:
                output.append(f"  ... and {len(results.successes) - 10} more")
            output.append("")

        if results.failures:
            output.append("Failed entities:")
            for failure in results.failures[:10]:  # Show first 10
                output.append(f"  - {failure['entity_id']}: {failure['error']}")
            if len(results.failures) > 10:
                output.append(f"  ... and {len(results.failures) - 10} more")

        return "\n".join(output)

    return [
        StructuredTool.from_function(
            coroutine=list_available_actions,
            name="list_available_actions",
            description="List all available actions for an entity type. Returns names, parameters, and preconditions.",
            args_schema=ListAvailableActionsInput,
        ),
        StructuredTool.from_function(
            coroutine=get_action_details,
            name="get_action_details",
            description="Get detailed information for a specific action, including all preconditions.",
            args_schema=GetActionDetailsInput,
        ),
        # 移除validate_action_preconditions工具，因为execute_action已经包含了前置条件校验
        # StructuredTool.from_function(
        #     coroutine=validate_action_preconditions,
        #     name="validate_action_preconditions",
        #     description="Validate if an action can be executed on an entity. Checks all preconditions.",
        #     args_schema=ValidateActionPreconditionsInput,
        # ),
        StructuredTool.from_function(
            coroutine=execute_action,
            name="execute_action",
            description="Execute an action on a single entity instance. Checks preconditions and executes if passed.",
            args_schema=ExecuteActionInput,
        ),
        StructuredTool.from_function(
            coroutine=batch_execute_action,
            name="batch_execute_action",
            description="Execute an action concurrently on multiple entities (preferred for bulk operations). Returns a summary of success/failure.",
            args_schema=BatchExecuteActionInput,
        ),
    ]


class ActionToolRegistry:
    """Registry for action tools.

    This class manages the lifecycle of action tools.
    """

    def __init__(
        self,
        get_session_func: Callable,
        action_executor: ActionExecutor,
        action_registry: ActionRegistry,
    ):
        """Initialize the action tool registry.

        Args:
            get_session_func: Async function that returns a database session
            action_executor: ActionExecutor instance
            action_registry: ActionRegistry instance
        """
        self.get_session_func = get_session_func
        self.action_executor = action_executor
        self.action_registry = action_registry
        self._tools: List[StructuredTool] | None = None

    @property
    def tools(self) -> List[StructuredTool]:
        """Get the list of action tools."""
        if self._tools is None:
            self._tools = create_action_tools(
                self.get_session_func,
                self.action_executor,
                self.action_registry,
            )
        return self._tools

    def get_tool_names(self) -> List[str]:
        """Get the names of all action tools."""
        return [tool.name for tool in self.tools]
