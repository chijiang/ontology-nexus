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

            return {
                "rule": rule.name,
                "success": True,
                "entities_affected": result.get("entities_affected", 0),
                "statements_executed": result.get("statements_executed", 0),
            }

        except Exception as e:
            logger.exception(f"Error executing rule {rule.name}")
            return {"rule": rule.name, "error": str(e), "success": False}

    async def _execute_for_clause_async(
        self,
        for_clause: ForClause,
        event: UpdateEvent,
        session: "AsyncSession",
        bindings: dict[str, tuple[str, str]] | None = None,
    ) -> dict[str, Any]:
        """Execute a FOR clause with actual database queries.

        Args:
            for_clause: The FOR clause to execute
            event: The triggering event
            session: Database session
            bindings: Variable bindings from parent scopes (var_name -> (type, entity_id))

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
            records = result.fetchall()

            logger.info(f"Found {len(records)} matching entities for rule")

            # For each matching entity, execute the statements
            for record in records:
                entity_id = record[0]  # First column is entity_id
                entity_props = (
                    record[1] if len(record) > 1 else {}
                )  # Second column is props

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

        Returns:
            True if statement executed successfully
        """
        if isinstance(stmt, SetStatement):
            return await self._execute_set_statement(
                session, stmt, var, entity_type, entity_id, entity_props
            )
        elif isinstance(stmt, TriggerStatement):
            return await self._execute_trigger_statement(
                session, stmt, entity_type, entity_id
            )
        elif isinstance(stmt, ForClause):
            # Nested FOR clause - recursive execution
            logger.info(f"Executing nested FOR clause for {stmt.variable}")
            result = await self._execute_for_clause_async(
                stmt, event, session, bindings
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
    ) -> bool:
        """Execute a SET statement.

        Args:
            session: Database session
            stmt: SetStatement to execute
            var: Variable name
            entity_type: Entity type
            entity_id: Entity ID
            entity_props: Current entity properties

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

            # Evaluate the value
            evaluated_value = self._evaluate_value(value, entity_props)

            # Build and execute the update query for PostgreSQL
            # Use jsonb_set(target, path, new_value)
            # path is an array of text
            update_query = text(
                """
                UPDATE graph_entities
                SET properties = jsonb_set(
                    COALESCE(properties, '{}'::jsonb),
                    ARRAY[:prop_name]::text[],
                    CAST(:json_value AS jsonb)
                )
                WHERE (id = :entity_id OR name = :entity_id_str) AND entity_type = :entity_type
            """
            )

            json_value = json.dumps(evaluated_value)

            logger.info(f"Executing SET: {entity_id}.{prop_name} = {evaluated_value}")

            await session.execute(
                update_query,
                {
                    "entity_id": entity_id,
                    "entity_id_str": str(entity_id),
                    "entity_type": entity_type,
                    "prop_name": prop_name,
                    "json_value": json_value,
                },
            )
            await session.commit()

            return True

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
                # TODO: Execute the action
            else:
                logger.warning(
                    f"Action {action_name} not found for entity type {entity_type}"
                )

            return True

        except Exception as e:
            logger.error(f"Error executing TRIGGER statement: {e}")
            return False

    def _evaluate_value(self, value: Any, entity_props: dict[str, Any]) -> Any:
        """Evaluate a value expression.

        Args:
            value: The value expression (could be literal or function call)
            entity_props: Entity properties for variable resolution

        Returns:
            Evaluated value
        """
        logger.debug(f"Evaluating value: {value} (type: {type(value).__name__})")

        # Handle None
        if value is None:
            logger.debug("Value is None")
            return None

        # Handle numbers directly
        if isinstance(value, (int, float)):
            logger.debug(f"Value is number: {value}")
            return value

        # Handle booleans directly
        if isinstance(value, bool):
            logger.debug(f"Value is boolean: {value}")
            return value

        # Handle string literals
        if isinstance(value, str):
            # The parser already strips quotes, so this is a plain string
            # Check if it's a property reference (e.g., "e.status")
            if "." in value:
                parts = value.split(".")
                if len(parts) == 2 and parts[0] in ("this", "e"):
                    prop_value = entity_props.get(parts[1])
                    logger.debug(
                        f"Value is property reference: {value} -> {prop_value}"
                    )
                    return prop_value
            # It's a plain string value
            logger.debug(f"Value is plain string: {value}")
            return value

        # Handle function calls or identifiers (tuples like ("call", "NOW", []) or ("id", "var.prop"))
        if isinstance(value, tuple):
            if len(value) > 0:
                if value[0] == "call":
                    func_name = value[1] if len(value) > 1 else ""
                    args = value[2] if len(value) > 2 else []
                    logger.debug(f"Value is function call: {func_name}({args})")

                    if func_name.upper() == "NOW":
                        from datetime import datetime

                        return datetime.utcnow().isoformat()
                    # Add more built-in functions as needed

                elif value[0] == "id":
                    path = value[1]
                    # Direct reuse of string logic for simple resolution
                    if "." in path:
                        parts = path.split(".")
                        if (
                            len(parts) == 2
                            and parts[0] in ("this", "e")
                            or any(parts[0] == var for var in ("this", "e", "s", "po"))
                        ):
                            # We might need better variable awareness here,
                            # but for now let's just use entity_props if it's the right prefix
                            # Wait, RuleEngine handles nested FORs by passing entity_props
                            # but it doesn't have a full scope stack.
                            # For now, let's just try to resolve it.
                            prop_value = entity_props.get(parts[1])
                            logger.debug(f"Value is identifier: {path} -> {prop_value}")
                            return prop_value
                    return path

            # Handle other tuple types (AST nodes)
            logger.debug(f"Value is unknown tuple: {value}")
            return None

        # Handle lists
        if isinstance(value, list):
            logger.debug(f"Value is list: {value}")
            return [self._evaluate_value(item, entity_props) for item in value]

        logger.warning(f"Unknown value type: {type(value).__name__} = {value}")
        return value

    def _execute_rule(self, rule: RuleDef, event: UpdateEvent) -> dict[str, Any] | None:
        """Deprecated: Use _execute_rule_async instead."""
        return {
            "rule": rule.name,
            "error": "Synchronous execution not supported",
            "success": False,
        }
