"""Cypher query translator for rule engine FOR clauses."""

from typing import Any
from app.rule_engine.models import ForClause


class CypherTranslator:
    """Translates rule engine AST nodes to Cypher queries.

    This class converts FOR clauses and their conditions into Cypher queries
    that can be executed against Neo4j. It handles variable binding for nested
    queries and translates various expression types.
    """

    def __init__(self):
        """Initialize the translator with empty bound variables."""
        self._bound_vars: dict[str, tuple[str, str]] = {}
        self._param_counter = 0

    def translate_for(self, for_clause: ForClause) -> str:
        """Convert a FOR clause to a Cypher query.

        Args:
            for_clause: The FOR clause to translate

        Returns:
            A Cypher query string
        """
        var = for_clause.variable
        entity_type = for_clause.entity_type
        condition = for_clause.condition

        # Start with MATCH clause
        cypher = f"MATCH ({var}:{entity_type})"

        # Add WHERE clause if there's a condition
        if condition:
            where_cypher = self.translate_condition(condition)
            if where_cypher:
                cypher += f"\nWHERE {where_cypher}"

        # Add RETURN clause
        cypher += f"\nRETURN {var}"

        return cypher

    def translate_condition(self, condition: Any) -> str:
        """Convert a WHERE condition to Cypher.

        Args:
            condition: AST expression node

        Returns:
            Cypher WHERE clause fragment (without the WHERE keyword)
        """
        if condition is None:
            return ""

        # Handle different expression types
        if isinstance(condition, tuple):
            op = condition[0]

            if op == "op":
                # Binary operation: ("op", operator, left, right)
                _, operator, left, right = condition
                return self._translate_binary_op(operator, left, right)

            elif op == "and":
                # AND: ("and", left, right)
                _, left, right = condition
                left_cypher = self.translate_condition(left)
                right_cypher = self.translate_condition(right)
                return f"({left_cypher} AND {right_cypher})"

            elif op == "or":
                # OR: ("or", left, right)
                _, left, right = condition
                left_cypher = self.translate_condition(left)
                right_cypher = self.translate_condition(right)
                return f"({left_cypher} OR {right_cypher})"

            elif op == "not":
                # NOT: ("not", expr)
                _, expr = condition
                expr_cypher = self.translate_condition(expr)
                return f"NOT ({expr_cypher})"

            elif op == "is_null":
                # IS NULL / IS NOT NULL: ("is_null", expr, is_not)
                _, expr, is_not = condition
                expr_cypher = self._translate_value(expr)
                if is_not:
                    return f"{expr_cypher} IS NOT NULL"
                return f"{expr_cypher} IS NULL"

            elif op == "id":
                # Identifier/Path: ("id", path)
                _, path = condition
                return self._translate_path(path)

            elif op == "exists":
                # Existence check: ("exists", pattern)
                _, pattern = condition
                pattern_cypher = self._translate_pattern(pattern)
                return f"EXISTS {{ {pattern_cypher} }}"

            elif op == "call":
                # Function call: ("call", function_name, args)
                _, func_name, args = condition
                return self._translate_function_call(func_name, args)

        # Handle literal values
        return self._translate_value(condition)

    def bind_variable(self, var: str, entity_type: str, entity_id: str) -> None:
        """Bind an outer scope variable for use in nested queries.

        When executing nested FOR clauses, variables from outer scopes need
        to be bound so they can be referenced in inner queries.

        Args:
            var: Variable name
            entity_type: Entity type (label)
            entity_id: Entity ID
        """
        self._bound_vars[var] = (entity_type, entity_id)

    def unbind_variable(self, var: str) -> None:
        """Remove a bound variable.

        Args:
            var: Variable name to unbind
        """
        if var in self._bound_vars:
            del self._bound_vars[var]

    def clear_bound_vars(self) -> None:
        """Clear all bound variables."""
        self._bound_vars.clear()

    def _translate_binary_op(self, operator: str, left: Any, right: Any) -> str:
        """Translate a binary operation to Cypher.

        Args:
            operator: The operator (e.g., "==", "!=", "<", ">", IN)
            left: Left operand
            right: Right operand

        Returns:
            Cypher expression
        """
        left_cypher = self._translate_value(left)
        right_cypher = self._translate_value(right)

        # Handle IN operator specially
        if operator == "IN":
            if isinstance(right, list) or isinstance(right, tuple):
                # Convert list to Cypher list literal
                items = [self._translate_value(item) for item in right]
                right_cypher = "[" + ", ".join(items) + "]"
            return f"{left_cypher} IN {right_cypher}"

        # Handle relationship operator (list from parser)
        # e.g. ["-", "relName", "->"]
        if isinstance(operator, list) and len(operator) >= 2:
            rel_name = operator[1] if len(operator) > 1 else ""
            direction = operator[2] if len(operator) > 2 else (operator[0] if len(operator) > 0 else "->")
            label = f":{rel_name}" if rel_name else ""
            
            # po -[orderedFrom]-> s
            if direction == "->":
                return f"({left_cypher})-[{label}]->({right_cypher})"
            elif direction == "<-":
                return f"({left_cypher})<-[{label}]-({right_cypher})"
            else:
                return f"({left_cypher})-[{label}]-({right_cypher})"

        # Map operators to Cypher
        op_map = {
            "==": "=",
            "!=": "<>",
            "<": "<",
            ">": ">",
            "<=": "<=",
            ">=": ">=",
        }

        cypher_op = op_map.get(str(operator), str(operator))
        return f"{left_cypher} {cypher_op} {right_cypher}"

    def _translate_path(self, path: str) -> str:
        """Translate a property path to Cypher.

        Args:
            path: Dot-separated property path (e.g., "s.status")

        Returns:
            Cypher property access expression
        """
        # Split path into variable and properties
        parts = path.split(".")
        if not parts:
            return "null"

        var = parts[0]
        if len(parts) == 1:
            return var

        # Access properties
        return f"{'.'.join(parts)}"

    def _translate_pattern(self, pattern: Any) -> str:
        """Translate a graph pattern to Cypher.

        Args:
            pattern: Pattern list [node1, rel1, node2, ..., WHERE expr]

        Returns:
            Cypher relationship pattern
        """
        if not isinstance(pattern, (list, tuple)):
            return ""

        parts = []
        where_expr = None

        # Check for WHERE at the end
        if len(pattern) >= 2 and pattern[-2] == "WHERE":
            where_expr = pattern[-1]
            pattern_core = pattern[:-2]
        else:
            pattern_core = pattern

        # Translate nodes and relationships
        for item in pattern_core:
            if isinstance(item, tuple) and item[0] == "node":
                # node: ("node", var, type)
                _, var, type_name = item
                # Ensure type_name is not "None" string or None object
                if type_name and str(type_name) != "None":
                    label = f":{type_name}"
                else:
                    label = ""
                parts.append(f"({var}{label})")
            elif isinstance(item, list) and len(item) >= 2:
                # rel: ["-", "orderedFrom", "->"]
                # item[0] is "-", item[1] is name, item[2] is "->"
                rel_name = item[1] if len(item) > 1 else ""
                direction = item[2] if len(item) > 2 else "->"
                label = f":{rel_name}" if rel_name else ""
                if direction == "->":
                    parts.append(f"-[{label}]->")
                elif direction == "<-":
                    parts.append(f"<-[{label}]-")
                else:
                    parts.append(f"-[{label}]-")
            elif isinstance(item, str):
                parts.append(item)

        cypher = "".join(parts)
        if where_expr:
            where_cypher = self.translate_condition(where_expr)
            if where_cypher:
                cypher += f" WHERE {where_cypher}"

        return cypher

    def _translate_function_call(self, func_name: str, args: list[Any]) -> str:
        """Translate a function call to Cypher.

        Args:
            func_name: Function name
            args: List of arguments

        Returns:
            Cypher function call expression
        """
        arg_list = [self._translate_value(arg) for arg in args]
        return f"{func_name}({', '.join(arg_list)})"

    def _translate_value(self, value: Any) -> str:
        """Translate a value to Cypher literal.

        Args:
            value: The value to translate

        Returns:
            Cypher literal expression
        """
        if value is None:
            return "null"

        if isinstance(value, str):
            # Check if it's a path reference
            if "." in value or value in self._bound_vars:
                return self._translate_path(value)
            # Otherwise it's a string literal
            return f"'{value}'"

        if isinstance(value, bool):
            return "true" if value else "false"

        if isinstance(value, (int, float)):
            return str(value)

        if isinstance(value, list):
            items = [self._translate_value(item) for item in value]
            return "[" + ", ".join(items) + "]"

        if isinstance(value, tuple):
            # Handle nested tuples (AST nodes)
            op = value[0] if value else ""
            if op == "path" or op == "id":
                return self._translate_path(value[1])
            elif op == "call":
                return self._translate_function_call(value[1], value[2])
            # Try to translate as condition
            return self.translate_condition(value)

        # Fallback: convert to string
        return str(value)

    def _get_next_param(self) -> str:
        """Get the next parameter name for parameterized queries.

        Returns:
            Parameter name like $param0, $param1, etc.
        """
        param_name = f"$param{self._param_counter}"
        self._param_counter += 1
        return param_name
