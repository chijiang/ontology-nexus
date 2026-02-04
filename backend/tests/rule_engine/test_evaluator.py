"""Tests for expression evaluator."""

import pytest
from datetime import datetime
from app.rule_engine.context import EvaluationContext
from app.rule_engine.evaluator import ExpressionEvaluator


@pytest.mark.asyncio
class TestExpressionEvaluator:
    """Test the ExpressionEvaluator class."""

    async def test_evaluate_simple_comparison(self):
        """Test evaluating simple comparison expressions."""
        ctx = EvaluationContext(
            entity={"status": "Active", "amount": 100},
            old_values={},
            session=None
        )
        evaluator = ExpressionEvaluator(ctx)

        # Equality
        assert await evaluator.evaluate(("op", "==", ("id", "this.status"), "Active")) is True
        assert await evaluator.evaluate(("op", "==", ("id", "this.status"), "Inactive")) is False

        # Inequality
        assert await evaluator.evaluate(("op", "!=", ("id", "this.status"), "Active")) is False
        assert await evaluator.evaluate(("op", "!=", ("id", "this.status"), "Inactive")) is True

        # Greater than
        assert await evaluator.evaluate(("op", ">", ("id", "this.amount"), 50)) is True
        assert await evaluator.evaluate(("op", ">", ("id", "this.amount"), 100)) is False
        assert await evaluator.evaluate(("op", ">", ("id", "this.amount"), 150)) is False

        # Less than
        assert await evaluator.evaluate(("op", "<", ("id", "this.amount"), 150)) is True
        assert await evaluator.evaluate(("op", "<", ("id", "this.amount"), 100)) is False
        assert await evaluator.evaluate(("op", "<", ("id", "this.amount"), 50)) is False

        # Greater than or equal
        assert await evaluator.evaluate(("op", ">=", ("id", "this.amount"), 100)) is True
        assert await evaluator.evaluate(("op", ">=", ("id", "this.amount"), 50)) is True
        assert await evaluator.evaluate(("op", ">=", ("id", "this.amount"), 150)) is False

        # Less than or equal
        assert await evaluator.evaluate(("op", "<=", ("id", "this.amount"), 100)) is True
        assert await evaluator.evaluate(("op", "<=", ("id", "this.amount"), 150)) is True
        assert await evaluator.evaluate(("op", "<=", ("id", "this.amount"), 50)) is False

    async def test_evaluate_in_operator(self):
        """Test evaluating IN operator."""
        ctx = EvaluationContext(
            entity={"status": "Active"},
            old_values={},
            session=None
        )
        evaluator = ExpressionEvaluator(ctx)

        # Value in list
        assert await evaluator.evaluate(("op", "IN", ("id", "this.status"), ["Active", "Pending"])) is True
        assert await evaluator.evaluate(("op", "IN", ("id", "this.status"), ["Pending", "Expired"])) is False

        # Empty list
        assert await evaluator.evaluate(("op", "IN", ("id", "this.status"), [])) is False

    async def test_evaluate_and_expression(self):
        """Test evaluating AND expressions."""
        ctx = EvaluationContext(
            entity={"status": "Active", "amount": 100},
            old_values={},
            session=None
        )
        evaluator = ExpressionEvaluator(ctx)

        # Both true
        assert await evaluator.evaluate(("and",
            ("op", "==", ("id", "this.status"), "Active"),
            ("op", ">", ("id", "this.amount"), 50)
        )) is True

        # First true, second false
        assert await evaluator.evaluate(("and",
            ("op", "==", ("id", "this.status"), "Active"),
            ("op", ">", ("id", "this.amount"), 150)
        )) is False

        # First false, second true
        assert await evaluator.evaluate(("and",
            ("op", "==", ("id", "this.status"), "Inactive"),
            ("op", ">", ("id", "this.amount"), 50)
        )) is False

        # Both false
        assert await evaluator.evaluate(("and",
            ("op", "==", ("id", "this.status"), "Inactive"),
            ("op", ">", ("id", "this.amount"), 150)
        )) is False

    async def test_evaluate_or_expression(self):
        """Test evaluating OR expressions."""
        ctx = EvaluationContext(
            entity={"status": "Active", "amount": 100},
            old_values={},
            session=None
        )
        evaluator = ExpressionEvaluator(ctx)

        # Both true
        assert await evaluator.evaluate(("or",
            ("op", "==", ("id", "this.status"), "Active"),
            ("op", "==", ("id", "this.status"), "Pending")
        )) is True

        # First true, second false
        assert await evaluator.evaluate(("or",
            ("op", "==", ("id", "this.status"), "Active"),
            ("op", "==", ("id", "this.status"), "Inactive")
        )) is True

        # First false, second true
        assert await evaluator.evaluate(("or",
            ("op", "==", ("id", "this.status"), "Pending"),
            ("op", "==", ("id", "this.status"), "Active")
        )) is True

        # Both false
        assert await evaluator.evaluate(("or",
            ("op", "==", ("id", "this.status"), "Pending"),
            ("op", "==", ("id", "this.status"), "Inactive")
        )) is False

    async def test_evaluate_not_expression(self):
        """Test evaluating NOT expressions."""
        ctx = EvaluationContext(
            entity={"status": "Active"},
            old_values={},
            session=None
        )
        evaluator = ExpressionEvaluator(ctx)

        # NOT true = false
        assert await evaluator.evaluate(("not", ("op", "==", ("id", "this.status"), "Active"))) is False

        # NOT false = true
        assert await evaluator.evaluate(("not", ("op", "==", ("id", "this.status"), "Inactive"))) is True

    async def test_evaluate_is_null(self):
        """Test evaluating IS NULL expressions."""
        ctx = EvaluationContext(
            entity={"status": "Active", "deletedAt": None},
            old_values={},
            session=None
        )
        evaluator = ExpressionEvaluator(ctx)

        # IS NULL - true
        assert await evaluator.evaluate(("is_null", ("id", "this.deletedAt"), False)) is True

        # IS NULL - false
        assert await evaluator.evaluate(("is_null", ("id", "this.status"), False)) is False

        # IS NOT NULL - true
        assert await evaluator.evaluate(("is_null", ("id", "this.status"), True)) is True

        # IS NOT NULL - false
        assert await evaluator.evaluate(("is_null", ("id", "this.deletedAt"), True)) is False

    async def test_now_function(self):
        """Test evaluating NOW() function."""
        ctx = EvaluationContext(
            entity={"createdAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
            old_values={},
            session=None
        )
        evaluator = ExpressionEvaluator(ctx)

        # NOW() should return a string
        now_result = await evaluator.evaluate(("call", "NOW", None))
        assert isinstance(now_result, str)

        # Can compare with datetime (implicitly handled by functions if strings are used)
        comparison = await evaluator.evaluate(("op", "<=", ("id", "this.createdAt"), ("call", "NOW", None)))
        assert comparison is True

    async def test_concat_function(self):
        """Test evaluating CONCAT() function."""
        ctx = EvaluationContext(
            entity={"firstName": "John", "lastName": "Doe"},
            old_values={},
            session=None
        )
        evaluator = ExpressionEvaluator(ctx)

        # CONCAT with multiple arguments
        result = await evaluator.evaluate(("call", "CONCAT", [("id", "this.firstName"), " ", ("id", "this.lastName")]))
        assert result == "John Doe"

        # CONCAT with two arguments
        result = await evaluator.evaluate(("call", "CONCAT", [("id", "this.firstName"), ("id", "this.lastName")]))
        assert result == "JohnDoe"

        # CONCAT with literals
        result = await evaluator.evaluate(("call", "CONCAT", ["Hello", " ", "World"]))
        assert result == "Hello World"

    async def test_resolve_path(self):
        """Test resolving property paths."""
        ctx = EvaluationContext(
            entity={"name": "Test", "nested": {"value": 42}},
            old_values={},
            session=None
        )
        evaluator = ExpressionEvaluator(ctx)

        # Simple path
        assert await evaluator._resolve_value("this.name") == "Test"

        # Nested path
        assert await evaluator._resolve_value("this.nested.value") == 42

        # Missing path
        assert await evaluator._resolve_value("this.missing") is None
        assert await evaluator._resolve_value("this.nested.missing") is None
