"""Rule engine for reactive graph updates."""

import asyncio
import logging
import json
from typing import Any, TYPE_CHECKING
from contextlib import asynccontextmanager
from app.rule_engine.rule_registry import RuleRegistry
from app.rule_engine.models import (
    RuleDef,
    UpdateEvent,
    Trigger,
    ForClause,
    SetStatement,
    TriggerStatement,
)
from app.rule_engine.context import EvaluationContext
from app.rule_engine.evaluator import ExpressionEvaluator
from app.rule_engine.persistence import PersistenceService
from app.rule_engine.pgq_translator import PGQTranslator
from sqlalchemy import text

if TYPE_CHECKING:
    from app.rule_engine.action_registry import ActionRegistry
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class RuleEngine:
    """Executes rules in response to graph update events.

    The rule engine monitors graph updates and executes rules whose
    triggers match the event. Rules are executed in priority order.
    """

    def __init__(
        self,
        action_registry: "ActionRegistry",
        registry: RuleRegistry,
        db_session: "AsyncSession | None" = None,
        session_provider: Any = None,
        action_executor: Any = None,
    ):
        """Initialize the rule engine.

        Args:
            action_registry: The action registry to use for executing actions
            registry: The rule registry to use
            db_session: Initial database session (optional)
            session_provider: Async callable that returns a valid database session
        """
        self.action_registry = action_registry
        self.registry = registry
        self.db_session = db_session
        self.session_provider = session_provider
        self.action_executor = action_executor
        self.translator = PGQTranslator()

    @asynccontextmanager
    async def _session_scope(self):
        """Provide a session scope for event handling."""
        if self.db_session:
            yield self.db_session
            return

        if self.session_provider:
            # Check if session_provider is an async generator (like from FastAPI)
            # or a simple factory returning an async context manager
            import inspect

            if inspect.isasyncgenfunction(self.session_provider):
                async for session in self.session_provider():
                    yield session
            else:
                # Assume it returns an async context manager (e.g., async_session())
                async with self.session_provider() as session:
                    yield session
        else:
            yield None

    def on_event(self, event: UpdateEvent) -> list[dict[str, Any]]:
        """Handle a graph update event synchronously.

        This is called by the event emitter. It schedules async execution.

        Args:
            event: The update event to handle

        Returns:
            Empty list (results are processed asynchronously)
        """
        # Run async execution in background
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._handle_event_async(event))
        except RuntimeError:
            # No running loop, try to run in new loop
            asyncio.run(self._handle_event_async(event))

        return []

    async def _handle_event_async(self, event: UpdateEvent) -> list[dict[str, Any]]:
        """Handle a graph update event asynchronously.

        Args:
            event: The update event to handle

        Returns:
            List of results from executed rules
        """
        logger.info(
            f"Rule engine received event: {event.entity_type}.{event.property} on {event.entity_id}"
        )

        # Matched rules to the event
        matched_rules = self._match_rules(event)

        if not matched_rules:
            logger.info(
                f"No rules matched for event: {event.entity_type}.{event.property}"
            )
            return []

        logger.info(
            f"Matched {len(matched_rules)} rules: {[r.name for r in matched_rules]}"
        )

        # Execute each matching rule within a session scope
        results = []
        async with self._session_scope() as session:
            if session is None:
                logger.error("No database session available for rule execution")
                return []

            for rule in matched_rules:
                result = await self._execute_rule_async(rule, event, session)
                if result:
                    results.append(result)
                    logger.info(f"Rule {rule.name} executed: {result}")

        return results

    async def execute_rule_by_id(
        self, rule_id: int, session: "AsyncSession"
    ) -> dict[str, Any]:
        """Execute a rule by its database ID.

        This is typically called by the scheduler for timed rules.
        """
        from app.models.rule import Rule
        from sqlalchemy import select
        from app.rule_engine.parser import RuleParser

        # 1. Fetch rule from DB
        result = await session.execute(select(Rule).where(Rule.id == rule_id))
        db_rule = result.scalar_one_or_none()

        if not db_rule:
            return {"error": f"Rule {rule_id} not found", "success": False}

        if not db_rule.is_active:
            return {"error": f"Rule {rule_id} is inactive", "success": False}

        # 2. Parse into RuleDef
        parser = RuleParser()
        try:
            parsed = parser.parse(db_rule.dsl_content)
            rule_def = next(
                (r for r in parsed if hasattr(r, "name") and r.name == db_rule.name),
                None,
            )
            if not rule_def:
                # Try first rule if name doesn't match perfectly
                rule_def = next((r for r in parsed if hasattr(r, "body")), None)
        except Exception as e:
            return {
                "error": f"Failed to parse DSL for rule {db_rule.name}: {e}",
                "success": False,
            }

        if not rule_def:
            return {
                "error": f"No valid rule definition found in DSL for {db_rule.name}",
                "success": False,
            }

        # 3. Create a mock event for a scheduled trigger
        from app.rule_engine.models import UpdateEvent

        event = UpdateEvent(
            entity_type=(
                rule_def.body.entity_type
                if hasattr(rule_def.body, "entity_type")
                else "System"
            ),
            entity_id="system",  # Scheduled rules might not have a specific trigger entity
            property="scheduler",
            old_value=None,
            new_value="triggered",
            actor_name="scheduler",
            actor_type="SYSTEM",
        )

        # 4. Execute the rule body
        # For scheduled rules, we might want to iterate over ALL entities that match the FOR clause
        # The _execute_rule_async expects an event to bind 'this'.
        # If it's a scheduled rule, 'this' might not be applicable unless we change the logic.
        # But our FOR clause handles searching.

        bindings = {}
        result = await self._execute_for_clause_async(
            rule_def.body, event, session, bindings
        )

        # Record execution log
        try:
            from app.repositories.rule_repository import ExecutionLogRepository

            repo = ExecutionLogRepository(session)
            await repo.create(
                type="RULE_SCHEDULED",
                name=db_rule.name,
                entity_id=None,
                actor_name="scheduler",
                actor_type="SYSTEM",
                success=True,
                detail=result,
            )
        except Exception as log_err:
            logger.error(f"Failed to record scheduled execution log: {log_err}")

        return {
            "rule": db_rule.name,
            "success": True,
            "entities_affected": result.get("entities_affected", 0),
            "statements_executed": result.get("statements_executed", 0),
        }

    def _match_rules(self, event: UpdateEvent) -> list[RuleDef]:
        """Match rules to an event.

        Finds all rules whose triggers match the event type,
        entity type, and property.

        Args:
            event: The update event

        Returns:
            List of matching rules ordered by priority
        """
        from app.rule_engine.models import Trigger, TriggerType

        # Build a trigger from the event
        trigger = Trigger(
            type=TriggerType.UPDATE,
            entity_type=event.entity_type,
            property=event.property,
        )

        # Get matching rules from registry
        return self.registry.get_by_trigger(trigger)

    async def _execute_rule_async(
        self, rule: RuleDef, event: UpdateEvent, session: "AsyncSession"
    ) -> dict[str, Any] | None:
        """Execute a rule against an event asynchronously.

        Args:
            rule: The rule to execute
            event: The event that triggered the rule

        Returns:
            Execution result or None if execution failed
        """
        try:
            # Bind the event entity to the rule's FOR clause variable
            for_clause = rule.body

            # Execute the FOR clause with actual database queries
            # Bind the triggering entity as 'this' and also its variable name (if match)
            # The root FOR clause usually uses 'e' or 'this'
            bindings = {
                "this": ("internal", event.entity_id),
                "e": (
                    "internal",
                    event.entity_id,
                ),  # Support 'e' as default for trigger entity
            }

            result = await self._execute_for_clause_async(
                for_clause, event, session, bindings
            )

            # Record execution log
            try:
                from app.repositories.rule_repository import ExecutionLogRepository

                repo = ExecutionLogRepository(session)
                await repo.create(
                    type="RULE",
                    name=rule.name,
                    entity_id=(
                        str(event.entity_id) if event.entity_id is not None else None
                    ),
                    actor_name=event.actor_name,
                    actor_type=event.actor_type,
                    success=True,
                    detail={
                        "entities_affected": result.get("entities_affected", 0),
                        "statements_executed": result.get("statements_executed", 0),
                    },
                )
            except Exception as log_err:
                logger.error(f"Failed to record execution log: {log_err}")

            return {
                "rule": rule.name,
                "success": True,
                "entities_affected": result.get("entities_affected", 0),
                "statements_executed": result.get("statements_executed", 0),
            }

        except Exception as e:
            logger.exception(f"Error executing rule {rule.name}")
            # Record failed execution log
            try:
                from app.repositories.rule_repository import ExecutionLogRepository

                repo = ExecutionLogRepository(session)
                await repo.create(
                    type="RULE",
                    name=rule.name,
                    entity_id=(
                        str(event.entity_id) if event.entity_id is not None else None
                    ),
                    actor_name=event.actor_name,
                    actor_type=event.actor_type,
                    success=False,
                    detail={"error": str(e)},
                )
            except Exception as log_err:
                logger.error(f"Failed to record execution log: {log_err}")
            return {"rule": rule.name, "error": str(e), "success": False}

    async def _execute_for_clause_async(
        self,
        for_clause: ForClause,
        event: UpdateEvent,
        session: "AsyncSession",
        bindings: dict[str, tuple[str, str]] | None = None,
        scope: dict[str, dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Execute a FOR clause with actual database queries.

        Args:
            for_clause: The FOR clause to execute
            event: The triggering event
            session: Database session
            bindings: Variable bindings from parent scopes (var_name -> (type, entity_id))
            scope: Variable properties from parent scopes (var_name -> props dict)

        Returns:
            Execution result with counts
        """
        # Set up translator with bindings
        self.translator.clear_bound_vars()
        if bindings:
            for var, (vtype, vid) in bindings.items():
                self.translator.bind_variable(var, vtype, vid)

        # Use the PGQ translator to generate SQL query
        sql_query = self.translator.translate_for(for_clause)

        logger.debug(f"Executing SQL query: {sql_query}")

        entities_affected = 0
        statements_executed = 0

        if not session:
            logger.error("No database session provided for rule execution")
            return {
                "entities_affected": 0,
                "statements_executed": 0,
            }

        from sqlalchemy import text

        try:
            result = await session.execute(text(sql_query))
            records = result.mappings().all()

            logger.info(f"Found {len(records)} matching entities for rule")

            # For each matching entity, execute the statements
            for record in records:
                # Access by column name
                entity_id = record.get("id")
                entity_name = record.get("name")
                if not entity_name:
                    entity_name = record.get("_display_name")

                raw_props = record.get("properties") or {}
                source_id = record.get("source_id")

                # Parse JSON string to dict if needed
                if isinstance(raw_props, str):
                    try:
                        entity_props = json.loads(raw_props)
                    except (json.JSONDecodeError, TypeError):
                        entity_props = {}
                else:
                    entity_props = raw_props if raw_props else {}

                # Include basics in props for easy access in rules
                if entity_name:
                    entity_props["name"] = entity_name
                if source_id:
                    entity_props["source_id"] = source_id
                    # Also keep 'id' in props if it exists or for legacy compatibility
                    # But the user wants to avoid confusion with internal ID
                    # If we remove 'id' from properties in sync,
                    # we should probably NOT put it back here under 'id' name
                    # unless a rule specifically asks for it.
                    # For now, let's follow the user's advice and call it source_id.

                # Update scope with this variable's properties
                current_scope = (scope or {}).copy()
                current_scope[for_clause.variable] = entity_props

                # Create evaluation context and evaluator for this iteration
                eval_ctx = EvaluationContext(
                    entity=entity_props,
                    old_values={},  # We don't have old values here easily
                    session=session,
                    variables=current_scope,
                )
                evaluator = ExpressionEvaluator(eval_ctx)

                # Execute each statement in the FOR clause
                for stmt in for_clause.statements:
                    # Update bindings for this iteration
                    current_bindings = (bindings or {}).copy()
                    current_bindings[for_clause.variable] = (
                        for_clause.entity_type,
                        entity_id,
                    )

                    executed = await self._execute_statement_async(
                        session,
                        stmt,
                        for_clause.variable,
                        for_clause.entity_type,
                        entity_id,
                        entity_props,
                        event,
                        current_bindings,
                        current_scope,
                        evaluator,
                    )
                    if executed:
                        statements_executed += 1

                entities_affected += 1

        except Exception as e:
            logger.error(f"Error executing FOR clause: {e}")

        return {
            "entities_affected": entities_affected,
            "statements_executed": statements_executed,
        }

    async def _execute_statement_async(
        self,
        session: Any,
        stmt: Any,
        var: str,
        entity_type: str,
        entity_id: str,
        entity_props: dict[str, Any],
        event: UpdateEvent,
        bindings: dict[str, tuple[str, str]],
        scope: dict[str, dict[str, Any]] | None = None,
        evaluator: ExpressionEvaluator | None = None,
    ) -> bool:
        """Execute a single statement.

        Args:
            session: Database session
            stmt: Statement to execute (SetStatement, TriggerStatement, or ForClause)
            var: Variable name bound to entity
            entity_type: Entity type
            entity_id: Entity ID
            entity_props: Current entity properties
            event: The original update event
            bindings: Current variable bindings
            scope: Variable properties from all scopes (var_name -> props dict)
            evaluator: Expression evaluator

        Returns:
            True if statement executed successfully
        """
        if isinstance(stmt, SetStatement):
            return await self._execute_set_statement(
                session,
                stmt,
                var,
                entity_type,
                entity_id,
                entity_props,
                scope,
                evaluator,
            )
        elif isinstance(stmt, TriggerStatement):
            return await self._execute_trigger_statement(
                session, stmt, entity_type, entity_id
            )
        elif isinstance(stmt, ForClause):
            # Nested FOR clause - recursive execution
            logger.info(f"Executing nested FOR clause for {stmt.variable}")
            result = await self._execute_for_clause_async(
                stmt, event, session, bindings, scope
            )
            return result.get("entities_affected", 0) >= 0  # Always true if it ran

        return False

    async def _execute_set_statement(
        self,
        session: Any,
        stmt: SetStatement,
        var: str,
        entity_type: str,
        entity_id: str,
        entity_props: dict[str, Any],
        scope: dict[str, dict[str, Any]] | None = None,
        evaluator: ExpressionEvaluator | None = None,
    ) -> bool:
        """Execute a SET statement.

        Args:
            session: Database session
            stmt: SetStatement to execute
            var: Variable name
            entity_type: Entity type
            entity_id: Entity ID
            entity_props: Current entity properties
            scope: Variable properties from all scopes (var_name -> props dict)
            evaluator: Expression evaluator

        Returns:
            True if successful
        """
        try:
            # Extract target property from the statement
            target = stmt.target  # e.g., "e.creditLevel"
            value = stmt.value

            # Parse the target to get property name
            parts = target.split(".")
            if len(parts) != 2:
                logger.error(f"Invalid SET target: {target}")
                return False

            target_var, prop_name = parts

            # Evaluate the value with full scope for cross-variable references
            if evaluator:
                evaluated_value = await evaluator.evaluate(value)
            else:
                # Fallback should not happen in rule engine rule execution
                # but good for safety
                eval_ctx = EvaluationContext(
                    entity=entity_props,
                    old_values={},
                    session=session,
                    variables=scope or {},
                )
                evaluator = ExpressionEvaluator(eval_ctx)
                evaluated_value = await evaluator.evaluate(value)

            logger.info(f"Executing SET: {entity_id}.{prop_name} = {evaluated_value}")

            # Use PersistenceService to update the property safely
            success = await PersistenceService.update_property(
                session, entity_type, entity_id, prop_name, evaluated_value
            )

            if success:
                await session.commit()
                return True
            return False

        except Exception as e:
            logger.error(f"Error executing SET statement: {e}")
            return False

    async def _execute_trigger_statement(
        self, session: Any, stmt: TriggerStatement, entity_type: str, entity_id: str
    ) -> bool:
        """Execute a TRIGGER statement.

        Args:
            session: Database session
            stmt: TriggerStatement to execute
            entity_type: Entity type
            entity_id: Entity ID

        Returns:
            True if successful
        """
        try:
            action_name = stmt.action
            target = stmt.target

            logger.info(f"Would trigger action {action_name} on {target}")

            # Look up the action in the registry
            action_def = self.action_registry.lookup(entity_type, action_name)
            if action_def:
                logger.info(f"Found action definition: {action_def.action_name}")

                # Use current action_executor if available, otherwise create one
                executor = self.action_executor
                if not executor:
                    from app.rule_engine.action_executor import ActionExecutor

                    executor = ActionExecutor(self.action_registry)

                # Create evaluation context for the action
                # Note: We use an empty entity dict for now, or we could pass current properties
                from app.rule_engine.context import EvaluationContext

                context = EvaluationContext(
                    entity={
                        "id": entity_id
                    },  # Minimum required for persistence in action executor
                    session=session,
                    variables={},
                )

                # Execute action
                result = await executor.execute(
                    entity_type=entity_type,
                    action_name=action_name,
                    context=context,
                    actor_name="rule_engine",
                    actor_type="SYSTEM",
                )

                if not result.success:
                    logger.error(f"Action {action_name} failed: {result.error}")
                    return False

                logger.info(f"Action {action_name} executed successfully")
            else:
                logger.warning(
                    f"Action {action_name} not found for entity type {entity_type}"
                )

            return True

        except Exception as e:
            logger.error(f"Error executing TRIGGER statement: {e}")
            return False
