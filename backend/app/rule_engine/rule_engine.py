"""Rule engine for reactive graph updates."""

from typing import Any
from app.rule_engine.rule_registry import RuleRegistry
from app.rule_engine.models import RuleDef, UpdateEvent, Trigger, ForClause
from app.rule_engine.cypher_translator import CypherTranslator


class RuleEngine:
    """Executes rules in response to graph update events.

    The rule engine monitors graph updates and executes rules whose
    triggers match the event. Rules are executed in priority order.
    """

    def __init__(self, registry: RuleRegistry):
        """Initialize the rule engine.

        Args:
            registry: The rule registry to use
        """
        self.registry = registry
        self.translator = CypherTranslator()

    def on_event(self, event: UpdateEvent) -> list[dict[str, Any]]:
        """Handle a graph update event.

        When an entity is updated, this method finds all rules whose
        triggers match the event and executes them.

        Args:
            event: The update event to handle

        Returns:
            List of results from executed rules
        """
        # Match rules to the event
        matched_rules = self._match_rules(event)

        # Execute each matching rule
        results = []
        for rule in matched_rules:
            result = self._execute_rule(rule, event)
            if result:
                results.append(result)

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
            property=event.property
        )

        # Get matching rules from registry
        return self.registry.get_by_trigger(trigger)

    def _execute_rule(self, rule: RuleDef, event: UpdateEvent) -> dict[str, Any] | None:
        """Execute a rule against an event.

        Args:
            rule: The rule to execute
            event: The event that triggered the rule

        Returns:
            Execution result or None if execution failed
        """
        try:
            # Bind the event entity to the rule's FOR clause variable
            # The rule body is a ForClause
            for_clause = rule.body

            # Prepare outer scope variables
            # The event entity becomes the starting point for the query
            outer_vars = {
                "entity_type": event.entity_type,
                "entity_id": event.entity_id,
                "property": event.property,
                "old_value": event.old_value,
                "new_value": event.new_value
            }

            # Execute the FOR clause
            return self._execute_for_clause(for_clause, outer_vars)

        except Exception as e:
            # Log error but don't propagate
            # In production, this would be logged
            return {
                "rule": rule.name,
                "error": str(e),
                "success": False
            }

    def _execute_for_clause(
        self,
        for_clause: ForClause,
        outer_vars: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Execute a FOR clause.

        FOR clauses are translated to Cypher queries and executed
        against the database. The results are then used to execute
        the statements within the FOR clause.

        Args:
            for_clause: The FOR clause to execute
            outer_vars: Variables from outer scope

        Returns:
            Execution result or None
        """
        # Translate the FOR clause to Cypher
        query = self.translator.translate_for(for_clause)

        # In a real implementation, we would:
        # 1. Execute the Cypher query against Neo4j
        # 2. For each result, execute the statements in the FOR clause
        # 3. Use the ActionExecutor to handle SET and TRIGGER statements

        # For now, return a placeholder result
        # This would be replaced with actual query execution
        return {
            "query": query,
            "variable": for_clause.variable,
            "entity_type": for_clause.entity_type,
            "statement_count": len(for_clause.statements)
        }

    def _execute_statements(
        self,
        statements: list[Any],
        entity: dict[str, Any],
        context: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Execute statements for a matched entity.

        Args:
            statements: List of statements to execute
            entity: The entity data
            context: Execution context

        Returns:
            List of statement execution results
        """
        results = []

        for stmt in statements:
            # In a real implementation, we would:
            # 1. Use ActionExecutor to handle SET statements
            # 2. Recursively execute nested FOR clauses
            # 3. Trigger actions for TRIGGER statements

            # For now, track the statement
            results.append({
                "type": type(stmt).__name__,
                "executed": True
            })

        return results
