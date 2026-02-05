"""Batch Action Executor for concurrent action execution.

This module provides the BatchActionExecutor class which handles
concurrent execution of actions on multiple entities with controlled
parallelism and progress tracking.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable
from datetime import datetime

from app.rule_engine.action_executor import ActionExecutor, ExecutionResult
from app.rule_engine.context import EvaluationContext

logger = logging.getLogger(__name__)


@dataclass
class BatchExecutionConfig:
    """Configuration for batch execution.

    Attributes:
        max_concurrent: Maximum number of concurrent action executions
        timeout_per_action: Timeout in seconds for each action
        retry_on_failure: Whether to retry failed actions
        max_retries: Maximum number of retry attempts
    """

    max_concurrent: int = 10
    timeout_per_action: int = 30
    retry_on_failure: bool = False
    max_retries: int = 1


@dataclass
class BatchExecutionResult:
    """Result of a batch action execution.

    Attributes:
        total: Total number of actions attempted
        succeeded: Number of successful executions
        failed: Number of failed executions
        successes: List of successful results with entity_id and changes
        failures: List of failed results with entity_id and error
        duration_seconds: Total execution time in seconds
    """

    total: int
    succeeded: int
    failed: int
    successes: list[dict] = field(default_factory=list)
    failures: list[dict] = field(default_factory=list)
    duration_seconds: float = 0.0


class StreamingBatchExecutor:
    """Batch executor with real-time progress streaming.

    This executor executes actions concurrently and yields progress
    updates via a callback function for each completed action.
    """

    def __init__(
        self,
        action_executor: ActionExecutor,
        get_session_func: Callable,
        get_entity_data_func: Callable | None = None,
    ):
        """Initialize the streaming batch executor.

        Args:
            action_executor: ActionExecutor instance
            get_session_func: Async function to get Neo4j session
            get_entity_data_func: Optional function to get entity data
        """
        self.action_executor = action_executor
        self.get_session_func = get_session_func
        self.get_entity_data_func = get_entity_data_func

    async def execute_batch(
        self,
        executions: list[dict],
        config: BatchExecutionConfig | None = None,
        progress_callback: Callable[[dict], Awaitable] | None = None,
    ) -> BatchExecutionResult:
        """Execute actions concurrently with controlled parallelism.

        Args:
            executions: List of execution specs with entity_type, action_name, entity_id, params
            config: Optional batch execution configuration
            progress_callback: Optional async callback for progress updates

        Returns:
            BatchExecutionResult with success/failure breakdown
        """
        config = config or BatchExecutionConfig()
        start_time = datetime.now()

        total = len(executions)
        completed = 0
        successes = []
        failures = []

        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(config.max_concurrent)

        # Define a wrapper function that creates closures correctly
        async def process_one(execution: dict) -> tuple[dict, Any]:
            """Process a single execution with semaphore control."""

            async def _execute():
                return await self._execute_single_action(execution)

            async with semaphore:
                try:
                    result = await asyncio.wait_for(
                        _execute(),
                        timeout=config.timeout_per_action
                    )
                    return execution, result
                except asyncio.TimeoutError:
                    result = ExecutionResult(
                        success=False,
                        error=f"Timeout after {config.timeout_per_action}s"
                    )
                    return execution, result
                except Exception as e:
                    return execution, e

        # Create all tasks by explicitly calling the wrapper for each execution
        tasks = [process_one(exec) for exec in executions]

        # Process tasks as they complete
        for task in asyncio.as_completed(tasks):
            execution, result_or_error = await task

            completed += 1

            if isinstance(result_or_error, Exception):
                # Handle exception
                error_msg = str(result_or_error)
                failures.append({
                    "entity_id": execution["entity_id"],
                    "error": error_msg
                })

                logger.warning(
                    f"Action {execution['entity_type']}.{execution['action_name']} "
                    f"on {execution['entity_id']} failed: {error_msg}"
                )

                # Send progress update
                if progress_callback:
                    await progress_callback({
                        "type": "action_progress",
                        "completed": completed,
                        "total": total,
                        "entity_id": execution["entity_id"],
                        "success": False,
                        "error": error_msg,
                    })
            elif result_or_error.success:
                successes.append({
                    "entity_id": execution["entity_id"],
                    "changes": result_or_error.changes
                })

                logger.info(
                    f"Action {execution['entity_type']}.{execution['action_name']} "
                    f"on {execution['entity_id']} succeeded"
                )

                # Send progress update
                if progress_callback:
                    await progress_callback({
                        "type": "action_progress",
                        "completed": completed,
                        "total": total,
                        "entity_id": execution["entity_id"],
                        "success": True,
                        "changes": result_or_error.changes,
                    })
            else:
                # Execution failed but not due to exception
                failures.append({
                    "entity_id": execution["entity_id"],
                    "error": result_or_error.error or "Unknown error"
                })

                logger.warning(
                    f"Action {execution['entity_type']}.{execution['action_name']} "
                    f"on {execution['entity_id']} failed: {result_or_error.error}"
                )

                # Send progress update
                if progress_callback:
                    await progress_callback({
                        "type": "action_progress",
                        "completed": completed,
                        "total": total,
                        "entity_id": execution["entity_id"],
                        "success": False,
                        "error": result_or_error.error,
                    })

        duration = (datetime.now() - start_time).total_seconds()

        return BatchExecutionResult(
            total=total,
            succeeded=len(successes),
            failed=len(failures),
            successes=successes,
            failures=failures,
            duration_seconds=duration,
        )

    async def _execute_single_action(
        self,
        execution: dict
    ) -> ExecutionResult:
        """Execute a single action.

        Args:
            execution: Execution spec with entity_type, action_name, entity_id, params

        Returns:
            ExecutionResult with success status and changes
        """
        entity_type = execution["entity_type"]
        action_name = execution["action_name"]
        entity_id = execution["entity_id"]
        params = execution.get("params", {})

        # Get entity data
        entity_data = await self._get_entity_data(entity_type, entity_id)

        if not entity_data:
            return ExecutionResult(
                success=False,
                error=f"Entity '{entity_id}' not found (type: {entity_type})"
            )

        # Execute the action with session
        async with self.get_session_func() as session:
            # Create evaluation context with session
            context = EvaluationContext(
                entity={"id": entity_id, **entity_data},
                old_values={},
                session=session,
                variables=params
            )

            # Execute the action
            return await self.action_executor.execute(entity_type, action_name, context)

    async def _get_entity_data(self, entity_type: str, entity_id: str) -> dict[str, Any]:
        """Get entity data from Neo4j.

        Args:
            entity_type: Entity type
            entity_id: Entity ID

        Returns:
            Entity data dict
        """
        if self.get_entity_data_func:
            return await self.get_entity_data_func(entity_type, entity_id)

        # Default implementation
        async def _query(session) -> dict:
            query = f"""
                MATCH (n:`{entity_type}` {{name: $id}})
                RETURN properties(n) AS props
            """
            result = await session.run(query, id=entity_id)
            record = await result.single()
            if record:
                return dict(record["props"])
            return {}

        # Execute with session
        async with self.get_session_func() as session:
            return await _query(session)


class BatchActionExecutor(StreamingBatchExecutor):
    """Batch action executor (alias for StreamingBatchExecutor).

    This class maintains backward compatibility while the StreamingBatchExecutor
    provides the full functionality.
    """

    pass


async def execute_with_progress(
    executor: StreamingBatchExecutor,
    executions: list[dict],
    progress_callback: Callable[[dict], Awaitable],
    config: BatchExecutionConfig | None = None,
) -> BatchExecutionResult:
    """Execute actions with progress updates.

    Convenience function for executing actions with progress tracking.

    Args:
        executor: Batch executor instance
        executions: List of execution specs
        progress_callback: Async callback for progress updates
        config: Optional batch configuration

    Returns:
        BatchExecutionResult
    """
    return await executor.execute_batch(executions, config, progress_callback)
