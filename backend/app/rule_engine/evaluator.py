"""Expression evaluator for DSL conditions."""

from typing import Any
import logging
from app.rule_engine.context import EvaluationContext
from app.rule_engine.functions import evaluate_function

# Use PGQ translator instead of Cypher translator
from app.rule_engine.pgq_translator import PGQTranslator


class ExpressionEvaluator:
    """Evaluator for rule expression AST nodes.

    The evaluator processes AST nodes produced by the parser and
    evaluates them against entity data in the evaluation context.
    """

    def __init__(self, context: EvaluationContext):
        """Initialize the evaluator.

        Args:
            context: Evaluation context containing entity data and variables
        """
        self.ctx = context
        self.translator = PGQTranslator()

    async def evaluate(self, ast: Any) -> Any:
        """Evaluate an AST node to a value.

        Args:
            ast: AST node to evaluate

        Returns:
            Evaluated result (typically bool for conditions)

        Raises:
            ValueError: If AST node is not recognized
        """
        if ast is None:
            return None

        if isinstance(ast, (str, int, float, bool)):
            return ast

        if isinstance(ast, tuple):
            return await self._evaluate_tuple(ast)

        if isinstance(ast, list):
            return [await self.evaluate(item) for item in ast]

        return ast

    async def _evaluate_tuple(self, ast: tuple) -> Any:
        """Evaluate a tuple AST node.

        Args:
            ast: Tuple AST node

        Returns:
            Evaluated result

        Raises:
            ValueError: If tuple format is not recognized
        """
        if not ast:
            return None

        op = ast[0]

        # Comparison operations: (op, operator, left, right)
        if op == "op":
            return await self._evaluate_comparison(ast[1], ast[2], ast[3])

        # Logical AND: (and, left, right)
        if op == "and":
            return await self._evaluate_and(ast[1], ast[2])

        # Logical OR: (or, left, right)
        if op == "or":
            return await self._evaluate_or(ast[1], ast[2])

        # Logical NOT: (not, operand)
        if op == "not":
            return await self._evaluate_not(ast[1])

        # IS NULL check: (is_null, path, is_not)
        if op == "is_null":
            return await self._evaluate_is_null(ast[1], ast[2])

        # Function call: (call, name, args)
        if op == "call":
            args = ast[2] if ast[2] is not None else []
            return await self._evaluate_function_call(ast[1], args)

        # Identifier resolution: (id, path)
        if op == "id":
            return await self._resolve_value(ast[1])

        # Existence check: (exists, pattern)
        if op == "exists":
            return await self._evaluate_exists(ast[1])

        raise ValueError(f"Unknown AST node type: {op}")

    async def _evaluate_comparison(
        self, operator: str | None, left: Any, right: Any
    ) -> bool | Any:
        """Evaluate a comparison operation.

        Args:
            operator: Comparison operator (==, !=, <, >, <=, >=, IN) or None for simple value
            left: Left operand (AST node or value)
            right: Right operand (AST node or value)

        Returns:
            Boolean result of comparison, or the value itself if operator is None
        """
        if operator is None:
            return await self._resolve_value(left)

        left_val = await self._resolve_value(left)
        right_val = await self.evaluate(right)

        if operator == "==":
            return left_val == right_val
        elif operator == "!=":
            return left_val != right_val
        elif operator == "<":
            return left_val < right_val
        elif operator == ">":
            return left_val > right_val
        elif operator == "<=":
            return left_val <= right_val
        elif operator == ">=":
            return left_val >= right_val
        elif operator == "IN":
            if not isinstance(right_val, list):
                right_val = [right_val]
            return left_val in right_val
        else:
            raise ValueError(f"Unknown comparison operator: {operator}")

    async def _evaluate_and(self, left: Any, right: Any) -> bool:
        """Evaluate logical AND."""
        left_val = await self.evaluate(left)
        right_val = await self.evaluate(right)
        return bool(left_val and right_val)

    async def _evaluate_or(self, left: Any, right: Any) -> bool:
        """Evaluate logical OR."""
        left_val = await self.evaluate(left)
        right_val = await self.evaluate(right)
        return bool(left_val or right_val)

    async def _evaluate_not(self, operand: Any) -> bool:
        """Evaluate logical NOT."""
        val = await self.evaluate(operand)
        return not val

    async def _evaluate_is_null(self, path: str, is_not: bool) -> bool:
        """Evaluate IS NULL or IS NOT NULL check."""
        val = await self._resolve_value(path)
        is_null = val is None
        return not is_null if is_not else is_null

    async def _evaluate_function_call(self, name: str, args: list) -> Any:
        """Evaluate a function call."""
        evaluated_args = [await self.evaluate(arg) for arg in args]
        return evaluate_function(name, evaluated_args)

    async def _evaluate_exists(self, pattern: Any) -> bool:
        """Evaluate EXISTS check via PostgreSQL.

        Args:
            pattern: Graph pattern AST node

        Returns:
            True if pattern exists, False otherwise
        """
        if not self.ctx.db:
            # If no session, we can't check the graph
            # This might happen in dry-runs or local-only evaluations
            return False

        # Bind 'this' context for the query
        entity_id = self.ctx.entity.get("id") or self.ctx.entity.get("name")
        entity_type = self.ctx.entity.get("__type__")

        if entity_id:
            self.translator.bind_variable("this", entity_type, str(entity_id))

        try:
            # Translate pattern to SQL/PGQ
            pattern_sql = self.translator._translate_pattern(pattern)
            query = f"SELECT EXISTS ({pattern_sql}) as exists"

            # Execute query
            from sqlalchemy import text

            result = await self.ctx.db.execute(text(query))
            record = result.first()
            return record[0] if record else False
        finally:
            self.translator.unbind_variable("this")

    async def _resolve_value(self, path: Any) -> Any:
        """Resolve a value from a property path or return the value directly."""
        if isinstance(path, str):
            # Try resolving via context (handles 'this.' and variables/parameters)
            return self.ctx.resolve_path(path)

        return await self.evaluate(path)
