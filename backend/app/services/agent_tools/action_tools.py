"""Action tools for the enhanced agent.

These tools enable the agent to execute actions on entity instances.
"""

import logging
from typing import Any, Callable, List
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from app.rule_engine.action_executor import ActionExecutor, ExecutionResult
from app.rule_engine.action_registry import ActionRegistry
from app.rule_engine.context import EvaluationContext
from app.rule_engine.models import ActionDef, Precondition

logger = logging.getLogger(__name__)


class ListAvailableActionsInput(BaseModel):
    """Input for list_available_actions tool."""

    entity_type: str = Field(description="Entity type, e.g., PurchaseOrder, Supplier, Invoice")


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
    params: dict[str, Any] = Field(default_factory=dict, description="Optional action parameters")


class BatchExecuteActionInput(BaseModel):
    """Input for batch_execute_action tool."""

    entity_type: str = Field(description="Entity type, e.g., PurchaseOrder")
    action_name: str = Field(description="Action name, e.g., submit")
    entity_ids: List[str] = Field(description="List of entity IDs")
    params: dict[str, Any] = Field(default_factory=dict, description="Optional shared parameters")


def format_action_def(action: ActionDef) -> str:
    """Format an action definition for display.

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


async def _get_entity_data(
    entity_type: str,
    entity_id: str,
    get_session_func: Callable
) -> dict[str, Any]:
    """Get entity data from PostgreSQL.

    Args:
        entity_type: Entity type
        entity_id: Entity ID (name property)
        get_session_func: Function to get database session

    Returns:
        Entity data dict
    """
    from app.services.pg_graph_storage import PGGraphStorage

    async def _execute(session) -> dict:
        storage = PGGraphStorage(session)
        results = await storage.search_instances(entity_id, entity_type, limit=1)
        if results:
            return results[0].get("properties", {})
        return {}

    return await _execute_with_session(get_session_func, _execute)


async def _execute_with_session(
    get_session_func: Callable,
    func: Callable
) -> Any:
    """Execute a function with a database session.

    Args:
        get_session_func: Function that returns a session
        func: Function to execute with session

    Returns:
        Result of the function
    """
    session = await get_session_func()
    try:
        return await func(session)
    finally:
        pass  # Session managed by caller


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
            return f"类型 '{entity_type}' 没有可用的操作"

        output = [f"类型 '{entity_type}' 的可用操作:\n"]
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
            return f"未找到操作: {entity_type}.{action_name}"

        return format_action_def(action)

    async def validate_action_preconditions(
        entity_type: str,
        action_name: str,
        entity_id: str
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
            return f"错误: 未找到操作 {entity_type}.{action_name}"

        # Get entity data
        try:
            entity_data = await _get_entity_data(entity_type, entity_id, get_session_func)
        except Exception as e:
            return f"错误: 无法获取实体 '{entity_id}' 的数据: {str(e)}"

        if not entity_data:
            return f"错误: 未找到实体 '{entity_id}' (类型: {entity_type})"

        # Create evaluation context
        session = None  # We won't execute, just validate
        context = EvaluationContext(
            entity={"id": entity_id, **entity_data},
            old_values={},
            session=session,
            variables={}
        )

        # Check preconditions
        from app.rule_engine.evaluator import ExpressionEvaluator
        evaluator = ExpressionEvaluator(context)

        output = [f"验证操作 {entity_type}.{action_name} 在实体 {entity_id} 上:\n"]

        all_passed = True
        for i, precond in enumerate(action.preconditions or [], 1):
            try:
                result = await evaluator.evaluate(precond.condition)
                status = "✓ 通过" if result else "✗ 失败"
                name = precond.name or f"前置条件 {i}"
                output.append(f"  {i}. {name}: {status}")
                if not result:
                    output.append(f"     原因: {precond.on_failure}")
                    all_passed = False
            except Exception as e:
                output.append(f"  {i}. {precond.name or f'前置条件 {i}'}: ✗ 错误: {str(e)}")
                all_passed = False

        if all_passed:
            output.append("\n结果: 所有前置条件通过，可以执行操作")
        else:
            output.append("\n结果: 部分前置条件未通过，无法执行操作")

        return "\n".join(output)

    async def execute_action(
        entity_type: str,
        action_name: str,
        entity_id: str,
        params: dict[str, Any] | None = None
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
            entity_data = await _get_entity_data(entity_type, entity_id, get_session_func)
        except Exception as e:
            return f"错误: 无法获取实体 '{entity_id}' 的数据: {str(e)}"

        if not entity_data:
            return f"错误: 未找到实体 '{entity_id}' (类型: {entity_type})"

        # Create evaluation context
        # Execute the action using the session from get_session_func
        session = await get_session_func()
        try:
            context = EvaluationContext(
                entity={"id": entity_id, **entity_data},
                old_values={},
                session=session,
                variables=params
            )
            result = await action_executor.execute(entity_type, action_name, context)
        finally:
            pass  # Session managed by caller

        if result.success:
            changes_str = ", ".join([f"{k}={v}" for k, v in result.changes.items()])
            return f"操作 {entity_type}.{action_name} 在 {entity_id} 上执行成功\n变更: {changes_str}"
        else:
            return f"操作 {entity_type}.{action_name} 在 {entity_id} 上执行失败\n原因: {result.error}"

    async def batch_execute_action(
        entity_type: str,
        action_name: str,
        entity_ids: List[str],
        params: dict[str, Any] | None = None
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
            return "错误: 未提供实体 ID 列表"

        output = [
            f"批量执行 {entity_type}.{action_name} 在 {len(entity_ids)} 个实体上...\n",
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
        results = await executor.execute_batch(executions)

        # Format results
        output.append(f"总计: {results['total']}")
        output.append(f"成功: {results['succeeded']}")
        output.append(f"失败: {results['failed']}")
        output.append("")

        if results["successes"]:
            output.append("成功的实体:")
            for success in results["successes"][:10]:  # Show first 10
                changes_str = ", ".join([f"{k}={v}" for k, v in success["changes"].items()])
                output.append(f"  - {success['entity_id']}: {changes_str}")
            if len(results["successes"]) > 10:
                output.append(f"  ... 还有 {len(results['successes']) - 10} 个")
            output.append("")

        if results["failures"]:
            output.append("失败的实体:")
            for failure in results["failures"][:10]:  # Show first 10
                output.append(f"  - {failure['entity_id']}: {failure['error']}")
            if len(results["failures"]) > 10:
                output.append(f"  ... 还有 {len(results['failures']) - 10} 个")

        return "\n".join(output)

    return [
        StructuredTool.from_function(
            coroutine=list_available_actions,
            name="list_available_actions",
            description="列出实体类型可用的所有操作。返回操作名称、参数和前置条件。",
            args_schema=ListAvailableActionsInput,
        ),
        StructuredTool.from_function(
            coroutine=get_action_details,
            name="get_action_details",
            description="获取特定操作的详细信息，包括所有前置条件。",
            args_schema=GetActionDetailsInput,
        ),
        StructuredTool.from_function(
            coroutine=validate_action_preconditions,
            name="validate_action_preconditions",
            description="验证操作是否可以在实体上执行。检查所有前置条件。",
            args_schema=ValidateActionPreconditionsInput,
        ),
        StructuredTool.from_function(
            coroutine=execute_action,
            name="execute_action",
            description="在单个实体实例上执行操作。检查前置条件并在通过后执行。",
            args_schema=ExecuteActionInput,
        ),
        StructuredTool.from_function(
            coroutine=batch_execute_action,
            name="batch_execute_action",
            description="在多个实体上并发执行操作（批量操作推荐使用）。返回成功/失败汇总。",
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
