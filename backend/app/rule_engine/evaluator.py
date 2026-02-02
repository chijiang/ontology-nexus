"""Expression evaluator for DSL conditions."""

from typing import Any
from app.rule_engine.context import EvaluationContext
from app.rule_engine.functions import evaluate_function


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

    def evaluate(self, ast: Any) -> Any:
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
            return self._evaluate_tuple(ast)

        if isinstance(ast, list):
            return [self.evaluate(item) for item in ast]

        return ast

    def _evaluate_tuple(self, ast: tuple) -> Any:
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
            return self._evaluate_comparison(ast[1], ast[2], ast[3])

        # Logical AND: (and, left, right)
        if op == "and":
            return self._evaluate_and(ast[1], ast[2])

        # Logical OR: (or, left, right)
        if op == "or":
            return self._evaluate_or(ast[1], ast[2])

        # Logical NOT: (not, operand)
        if op == "not":
            return self._evaluate_not(ast[1])

        # IS NULL check: (is_null, path, is_not)
        if op == "is_null":
            return self._evaluate_is_null(ast[1], ast[2])

        # Function call: (call, name, args)
        if op == "call":
            args = ast[2] if ast[2] is not None else []
            return self._evaluate_function_call(ast[1], args)

        raise ValueError(f"Unknown AST node type: {op}")

    def _evaluate_comparison(self, operator: str, left: Any, right: Any) -> bool:
        """Evaluate a comparison operation.

        Args:
            operator: Comparison operator (==, !=, <, >, <=, >=, IN)
            left: Left operand (AST node or value)
            right: Right operand (AST node or value)

        Returns:
            Boolean result of comparison
        """
        left_val = self._resolve_value(left)
        right_val = self.evaluate(right)

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
            # Right side should be a list
            if not isinstance(right_val, list):
                right_val = [right_val]
            return left_val in right_val
        else:
            raise ValueError(f"Unknown comparison operator: {operator}")

    def _evaluate_and(self, left: Any, right: Any) -> bool:
        """Evaluate logical AND.

        Args:
            left: Left operand (AST node)
            right: Right operand (AST node)

        Returns:
            Boolean result
        """
        left_val = self.evaluate(left)
        right_val = self.evaluate(right)
        return bool(left_val and right_val)

    def _evaluate_or(self, left: Any, right: Any) -> bool:
        """Evaluate logical OR.

        Args:
            left: Left operand (AST node)
            right: Right operand (AST node)

        Returns:
            Boolean result
        """
        left_val = self.evaluate(left)
        right_val = self.evaluate(right)
        return bool(left_val or right_val)

    def _evaluate_not(self, operand: Any) -> bool:
        """Evaluate logical NOT.

        Args:
            operand: Operand to negate (AST node)

        Returns:
            Boolean result
        """
        val = self.evaluate(operand)
        return not val

    def _evaluate_is_null(self, path: str, is_not: bool) -> bool:
        """Evaluate IS NULL or IS NOT NULL check.

        Args:
            path: Property path to check
            is_not: If True, check IS NOT NULL; if False, check IS NULL

        Returns:
            Boolean result
        """
        val = self._resolve_value(path)
        is_null = val is None

        if is_not:
            return not is_null
        return is_null

    def _evaluate_function_call(self, name: str, args: list) -> Any:
        """Evaluate a function call.

        Args:
            name: Function name
            args: Function arguments (AST nodes)

        Returns:
            Function result

        Raises:
            AttributeError: If function is not found
        """
        # Evaluate arguments
        evaluated_args = []
        for arg in args:
            if isinstance(arg, str) and arg.startswith("this."):
                # Property path
                evaluated_args.append(self._resolve_value(arg))
            else:
                evaluated_args.append(self.evaluate(arg))

        # Call the function
        return evaluate_function(name, evaluated_args)

    def _resolve_value(self, path: Any) -> Any:
        """Resolve a value from a property path or return the value directly.

        Args:
            path: Property path (string starting with "this.") or direct value

        Returns:
            Resolved value
        """
        if isinstance(path, str) and path.startswith("this."):
            return self.ctx.resolve_path(path)
        return self.evaluate(path)
