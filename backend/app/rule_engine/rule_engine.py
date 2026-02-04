"""Rule engine for reactive graph updates."""

import asyncio
import logging
from typing import Any, TYPE_CHECKING
from app.rule_engine.rule_registry import RuleRegistry
from app.rule_engine.models import (
    RuleDef,
    UpdateEvent,
    Trigger,
    ForClause,
    SetStatement,
    TriggerStatement,
)
from app.rule_engine.cypher_translator import CypherTranslator

if TYPE_CHECKING:
    from app.rule_engine.action_registry import ActionRegistry
    from neo4j import AsyncDriver

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
        neo4j_driver: "AsyncDriver | None" = None,
        driver_provider: Any = None,
    ):
        """Initialize the rule engine.

        Args:
            action_registry: The action registry to use for executing actions
            registry: The rule registry to use
            neo4j_driver: Initial Neo4j driver (optional)
            driver_provider: Async callable that returns a valid Neo4j driver
        """
        self.action_registry = action_registry
        self.registry = registry
        self.neo4j_driver = neo4j_driver
        self.driver_provider = driver_provider
        self.translator = CypherTranslator()
        self._database = "neo4j"  # Default database

    async def _get_session(self):
        """Get a Neo4j session, refreshing the driver if necessary."""
        if not self.neo4j_driver and self.driver_provider:
            self.neo4j_driver = await self.driver_provider()

        if not self.neo4j_driver:
            return None

        try:
            # Attempt to create a session to check if driver is open
            return self.neo4j_driver.session(database=self._database)
        except Exception as e:
            if "closed" in str(e).lower() and self.driver_provider:
                logger.info("Neo4j driver closed, attempting to refresh...")
                self.neo4j_driver = await self.driver_provider()
                if self.neo4j_driver:
                    return self.neo4j_driver.session(database=self._database)
            raise e

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

        # Match rules to the event
        matched_rules = self._match_rules(event)

        if not matched_rules:
            logger.info(
                f"No rules matched for event: {event.entity_type}.{event.property}"
            )
            return []

        logger.info(
            f"Matched {len(matched_rules)} rules: {[r.name for r in matched_rules]}"
        )

        # Execute each matching rule
        results = []
        for rule in matched_rules:
            result = await self._execute_rule_async(rule, event)
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
        self, rule: RuleDef, event: UpdateEvent
    ) -> dict[str, Any] | None:
        """Execute a rule against an event asynchronously.

        Args:
            rule: The rule to execute
            event: The event that triggered the rule

        Returns:
            Execution result or None if execution failed
        """
        if self.neo4j_driver is None and self.driver_provider is None:
            logger.error("Neo4j driver not available for rule execution")
            return {
                "rule": rule.name,
                "error": "Neo4j driver not available",
                "success": False,
            }

        try:
            # Bind the event entity to the rule's FOR clause variable
            for_clause = rule.body

            # Execute the FOR clause with actual Neo4j queries
            result = await self._execute_for_clause_async(for_clause, event)

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
        self, for_clause: ForClause, event: UpdateEvent
    ) -> dict[str, Any]:
        """Execute a FOR clause with actual Neo4j queries.

        Args:
            for_clause: The FOR clause to execute
            event: The triggering event

        Returns:
            Execution result with counts
        """
        # Build the MATCH query to find entities
        var = for_clause.variable
        entity_type = for_clause.entity_type
        condition = for_clause.condition

        # Build WHERE clause
        where_parts = [f"{var}.__is_instance = true"]

        if condition:
            condition_cypher = self.translator.translate_condition(condition)
            if condition_cypher:
                where_parts.append(condition_cypher)

        where_clause = " AND ".join(where_parts)

        # Build the query to find matching entities
        match_query = f"""
            MATCH ({var}:{entity_type})
            WHERE {where_clause}
            RETURN {var}.name AS entity_id, properties({var}) AS props
        """

        logger.debug(f"Executing match query: {match_query}")

        entities_affected = 0
        statements_executed = 0

        session = await self._get_session()
        if not session:
            logger.error("No Neo4j session available for rule execution")
            return {
                "entities_affected": 0,
                "statements_executed": 0,
            }

        async with session:
            # Find matching entities
            result = await session.run(match_query)
            records = await result.data()

            logger.info(f"Found {len(records)} matching entities for rule")

            # For each matching entity, execute the statements
            for record in records:
                entity_id = record["entity_id"]
                entity_props = record["props"]

                # Execute each statement in the FOR clause
                for stmt in for_clause.statements:
                    executed = await self._execute_statement_async(
                        session, stmt, var, entity_type, entity_id, entity_props
                    )
                    if executed:
                        statements_executed += 1

                entities_affected += 1

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
    ) -> bool:
        """Execute a single statement.

        Args:
            session: Neo4j session
            stmt: Statement to execute (SetStatement, TriggerStatement, or ForClause)
            var: Variable name bound to entity
            entity_type: Entity type
            entity_id: Entity ID
            entity_props: Current entity properties

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
            # Nested FOR clause - execute with parent context
            result = await self._execute_nested_for_clause_async(
                session,
                stmt,
                parent_var=var,
                parent_type=entity_type,
                parent_id=entity_id,
                parent_props=entity_props,
            )
            return result.get("statements_executed", 0) > 0

        return False

    async def _execute_nested_for_clause_async(
        self,
        session: Any,
        for_clause: ForClause,
        parent_var: str,
        parent_type: str,
        parent_id: str,
        parent_props: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a nested FOR clause with parent context.

        Args:
            session: Neo4j session
            for_clause: The nested FOR clause to execute
            parent_var: Parent variable name
            parent_type: Parent entity type
            parent_id: Parent entity ID
            parent_props: Parent entity properties

        Returns:
            Execution result with counts
        """
        var = for_clause.variable
        entity_type = for_clause.entity_type
        condition = for_clause.condition

        # Build the match pattern - check for relationship in condition
        relationship_pattern = self._extract_relationship_pattern(
            condition, var, parent_var
        )

        if relationship_pattern:
            # Use relationship-based query
            rel_type, direction = relationship_pattern
            if direction == "->":
                # var -[rel]-> parent
                match_clause = f"""
                    MATCH ({parent_var}:{parent_type} {{name: $parent_id}})
                    MATCH ({var}:{entity_type})-[:{rel_type}]->({parent_var})
                """
            else:
                # parent -[rel]-> var  OR  var <-[rel]- parent
                match_clause = f"""
                    MATCH ({parent_var}:{parent_type} {{name: $parent_id}})
                    MATCH ({parent_var})-[:{rel_type}]->({var}:{entity_type})
                """
        else:
            # No relationship, just match entity type
            match_clause = f"MATCH ({var}:{entity_type})"

        # Build WHERE clause for additional conditions (excluding relationship)
        where_parts = [f"{var}.__is_instance = true"]

        if condition:
            non_rel_condition = self._translate_non_relationship_condition(
                condition, var, parent_var, parent_props
            )
            if non_rel_condition:
                where_parts.append(non_rel_condition)

        where_clause = " AND ".join(where_parts)

        # Build full query
        query = f"""
            {match_clause}
            WHERE {where_clause}
            RETURN {var}.name AS entity_id, properties({var}) AS props
        """

        logger.info(f"Executing nested FOR query: {query}")

        entities_affected = 0
        statements_executed = 0

        try:
            result = await session.run(query, parent_id=parent_id)
            records = await result.data()

            logger.info(f"Nested FOR found {len(records)} matching entities")

            for record in records:
                nested_entity_id = record["entity_id"]
                nested_entity_props = record["props"]

                # Execute each statement in the nested FOR clause
                for stmt in for_clause.statements:
                    executed = await self._execute_statement_async(
                        session,
                        stmt,
                        var,
                        entity_type,
                        nested_entity_id,
                        nested_entity_props,
                    )
                    if executed:
                        statements_executed += 1

                entities_affected += 1

        except Exception as e:
            logger.error(f"Error executing nested FOR clause: {e}")

        return {
            "entities_affected": entities_affected,
            "statements_executed": statements_executed,
        }

    def _extract_relationship_pattern(
        self, condition: Any, var: str, parent_var: str
    ) -> tuple[str, str] | None:
        """Extract relationship pattern from condition.

        Looks for patterns like: var -[relType]-> parent_var

        Args:
            condition: The condition AST
            var: Current variable name
            parent_var: Parent variable name

        Returns:
            Tuple of (relationship_type, direction) or None
        """
        if condition is None:
            return None

        # Handle AND expressions
        # Handle tuples (AST nodes)
        if isinstance(condition, tuple):
            if condition[0] == "and":
                # Check left and right parts
                left_result = self._extract_relationship_pattern(
                    condition[1], var, parent_var
                )
                if left_result:
                    return left_result
                return self._extract_relationship_pattern(condition[2], var, parent_var)

            if condition[0] == "op":
                op = condition[1]
                left = condition[2]
                right = condition[3]
                
                # Check for relationship pattern in comparison
                # left and right could be ("id", "varname")
                left_var = left[1] if isinstance(left, tuple) and left[0] == "id" else left
                right_var = right[1] if isinstance(right, tuple) and right[0] == "id" else right

                if isinstance(op, list) and len(op) >= 2:
                    rel_type = op[1]
                    direction = op[2] if len(op) > 2 else "->"
                    
                    # Check if this comparison is our relationship between var and parent_var
                    if (left_var == var and right_var == parent_var):
                        return (rel_type, direction)
                    if (left_var == parent_var and right_var == var):
                        # Swap direction if it's the other way
                        new_dir = "<-" if direction == "->" else "->"
                        return (rel_type, new_dir)

        # Check if it's a list (legacy relationship pattern or direct list)
        if isinstance(condition, list):
            if len(condition) >= 3:
                left_var = condition[0][1] if isinstance(condition[0], tuple) and condition[0][0] == "id" else condition[0]
                right_var = condition[2][1] if isinstance(condition[2], tuple) and condition[2][0] == "id" else condition[2]
                rel_info = condition[1]
                
                if isinstance(rel_info, list) and len(rel_info) >= 2:
                    rel_type = rel_info[1]
                    direction = rel_info[2] if len(rel_info) > 2 else "->"
                    
                    if (left_var == var and right_var == parent_var):
                        return (rel_type, direction)
                    if (left_var == parent_var and right_var == var):
                        new_dir = "<-" if direction == "->" else "->"
                        return (rel_type, new_dir)

        return None

    def _translate_non_relationship_condition(
        self,
        condition: Any,
        var: str,
        parent_var: str,
        parent_props: dict[str, Any],
    ) -> str | None:
        """Translate condition to Cypher, excluding relationship patterns.

        Args:
            condition: The condition AST
            var: Current variable name
            parent_var: Parent variable name
            parent_props: Parent entity properties (for substitution)

        Returns:
            Cypher condition string or None
        """
        if condition is None:
            return None

        # Skip list types - these are relationship patterns
        if isinstance(condition, list):
            return None

        # Handle AND expressions
        if isinstance(condition, tuple) and len(condition) >= 3:
            if condition[0] == "and":
                left_cypher = self._translate_non_relationship_condition(
                    condition[1], var, parent_var, parent_props
                )
                right_cypher = self._translate_non_relationship_condition(
                    condition[2], var, parent_var, parent_props
                )
                parts = [p for p in [left_cypher, right_cypher] if p]
                if parts:
                    return " AND ".join(parts)
                return None

            if condition[0] == "op":
                # Standard comparison: ('op', operator, left, right)
                op = condition[1]
                left = condition[2]
                right = condition[3]

                # Skip if operator is not a string (might be a relationship list)
                if isinstance(op, list):
                    return None
                
                if not isinstance(op, str):
                    return None

                # Skip if left or right is also a list (relationship pattern)
                # Account for wrap
                left_val = left[1] if isinstance(left, tuple) and left[0] == "id" else left
                right_val = right[1] if isinstance(right, tuple) and right[0] == "id" else right

                if isinstance(left_val, list) or isinstance(right_val, list):
                    return None

                # Translate to cypher
                left_cypher = self._value_to_cypher(left, var, parent_var, parent_props)
                right_cypher = self._value_to_cypher(
                    right, var, parent_var, parent_props
                )

                # Map operator
                op_map = {"==": "=", "!=": "<>"}
                cypher_op = op_map.get(str(op), str(op))

                return f"{left_cypher} {cypher_op} {right_cypher}"

        return None

    def _value_to_cypher(
        self,
        value: Any,
        var: str,
        parent_var: str,
        parent_props: dict[str, Any],
    ) -> str:
        """Convert a value to Cypher representation.

        Args:
            value: The value to convert
            var: Current variable name
            parent_var: Parent variable name
            parent_props: Parent entity properties

        Returns:
            Cypher representation of the value
        """
        # Handle identifier wrap
        if isinstance(value, tuple) and len(value) > 0 and value[0] == "id":
            value = value[1]

        if isinstance(value, str):
            # Check if it's a property reference
            if "." in value:
                parts = value.split(".")
                if len(parts) == 2:
                    ref_var, prop = parts
                    if ref_var == parent_var:
                        # Substitute parent property value
                        prop_value = parent_props.get(prop)
                        if isinstance(prop_value, str):
                            return f'"{prop_value}"'
                        return str(prop_value)
                    return value  # Keep as property reference
            # It's a string literal
            return f'"{value}"'

        if isinstance(value, (int, float)):
            return str(value)

        if isinstance(value, bool):
            return "true" if value else "false"

        if value is None:
            return "null"

        return str(value)

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
            session: Neo4j session
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

            # Build and execute the update query
            update_query = f"""
                MATCH (n:{entity_type} {{name: $entity_id}})
                SET n.{prop_name} = $value
                RETURN n
            """

            logger.info(f"Executing SET: {entity_id}.{prop_name} = {evaluated_value}")

            result = await session.run(
                update_query, entity_id=entity_id, value=evaluated_value
            )
            await result.consume()

            return True

        except Exception as e:
            logger.error(f"Error executing SET statement: {e}")
            return False

    async def _execute_trigger_statement(
        self, session: Any, stmt: TriggerStatement, entity_type: str, entity_id: str
    ) -> bool:
        """Execute a TRIGGER statement.

        Args:
            session: Neo4j session
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
            # For now, just log - full action execution would be more complex
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
                        if len(parts) == 2 and parts[0] in ("this", "e") or any(parts[0] == var for var in ("this", "e", "s", "po")):
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
