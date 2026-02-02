"""Tests for expression evaluator."""

import pytest
from datetime import datetime
from app.rule_engine.context import EvaluationContext
from app.rule_engine.evaluator import ExpressionEvaluator


class TestExpressionEvaluator:
    """Test the ExpressionEvaluator class."""

    def test_evaluate_simple_comparison(self):
        """Test evaluating simple comparison expressions."""
        ctx = EvaluationContext(
            entity={"status": "Active", "amount": 100},
            old_values={},
            session=None
        )
        evaluator = ExpressionEvaluator(ctx)

        # Equality
        assert evaluator.evaluate(("op", "==", "this.status", "Active")) is True
        assert evaluator.evaluate(("op", "==", "this.status", "Inactive")) is False

        # Inequality
        assert evaluator.evaluate(("op", "!=", "this.status", "Active")) is False
        assert evaluator.evaluate(("op", "!=", "this.status", "Inactive")) is True

        # Greater than
        assert evaluator.evaluate(("op", ">", "this.amount", 50)) is True
        assert evaluator.evaluate(("op", ">", "this.amount", 100)) is False
        assert evaluator.evaluate(("op", ">", "this.amount", 150)) is False

        # Less than
        assert evaluator.evaluate(("op", "<", "this.amount", 150)) is True
        assert evaluator.evaluate(("op", "<", "this.amount", 100)) is False
        assert evaluator.evaluate(("op", "<", "this.amount", 50)) is False

        # Greater than or equal
        assert evaluator.evaluate(("op", ">=", "this.amount", 100)) is True
        assert evaluator.evaluate(("op", ">=", "this.amount", 50)) is True
        assert evaluator.evaluate(("op", ">=", "this.amount", 150)) is False

        # Less than or equal
        assert evaluator.evaluate(("op", "<=", "this.amount", 100)) is True
        assert evaluator.evaluate(("op", "<=", "this.amount", 150)) is True
        assert evaluator.evaluate(("op", "<=", "this.amount", 50)) is False

    def test_evaluate_in_operator(self):
        """Test evaluating IN operator."""
        ctx = EvaluationContext(
            entity={"status": "Active"},
            old_values={},
            session=None
        )
        evaluator = ExpressionEvaluator(ctx)

        # Value in list
        assert evaluator.evaluate(("op", "IN", "this.status", ["Active", "Pending"])) is True
        assert evaluator.evaluate(("op", "IN", "this.status", ["Pending", "Expired"])) is False

        # Empty list
        assert evaluator.evaluate(("op", "IN", "this.status", [])) is False

    def test_evaluate_and_expression(self):
        """Test evaluating AND expressions."""
        ctx = EvaluationContext(
            entity={"status": "Active", "amount": 100},
            old_values={},
            session=None
        )
        evaluator = ExpressionEvaluator(ctx)

        # Both true
        assert evaluator.evaluate(("and",
            ("op", "==", "this.status", "Active"),
            ("op", ">", "this.amount", 50)
        )) is True

        # First true, second false
        assert evaluator.evaluate(("and",
            ("op", "==", "this.status", "Active"),
            ("op", ">", "this.amount", 150)
        )) is False

        # First false, second true
        assert evaluator.evaluate(("and",
            ("op", "==", "this.status", "Inactive"),
            ("op", ">", "this.amount", 50)
        )) is False

        # Both false
        assert evaluator.evaluate(("and",
            ("op", "==", "this.status", "Inactive"),
            ("op", ">", "this.amount", 150)
        )) is False

    def test_evaluate_or_expression(self):
        """Test evaluating OR expressions."""
        ctx = EvaluationContext(
            entity={"status": "Active", "amount": 100},
            old_values={},
            session=None
        )
        evaluator = ExpressionEvaluator(ctx)

        # Both true
        assert evaluator.evaluate(("or",
            ("op", "==", "this.status", "Active"),
            ("op", "==", "this.status", "Pending")
        )) is True

        # First true, second false
        assert evaluator.evaluate(("or",
            ("op", "==", "this.status", "Active"),
            ("op", "==", "this.status", "Inactive")
        )) is True

        # First false, second true
        assert evaluator.evaluate(("or",
            ("op", "==", "this.status", "Pending"),
            ("op", "==", "this.status", "Active")
        )) is True

        # Both false
        assert evaluator.evaluate(("or",
            ("op", "==", "this.status", "Pending"),
            ("op", "==", "this.status", "Inactive")
        )) is False

    def test_evaluate_not_expression(self):
        """Test evaluating NOT expressions."""
        ctx = EvaluationContext(
            entity={"status": "Active"},
            old_values={},
            session=None
        )
        evaluator = ExpressionEvaluator(ctx)

        # NOT true = false
        assert evaluator.evaluate(("not", ("op", "==", "this.status", "Active"))) is False

        # NOT false = true
        assert evaluator.evaluate(("not", ("op", "==", "this.status", "Inactive"))) is True

    def test_evaluate_is_null(self):
        """Test evaluating IS NULL expressions."""
        ctx = EvaluationContext(
            entity={"status": "Active", "deletedAt": None},
            old_values={},
            session=None
        )
        evaluator = ExpressionEvaluator(ctx)

        # IS NULL - true
        assert evaluator.evaluate(("is_null", "this.deletedAt", False)) is True

        # IS NULL - false
        assert evaluator.evaluate(("is_null", "this.status", False)) is False

        # IS NOT NULL - true
        assert evaluator.evaluate(("is_null", "this.status", True)) is True

        # IS NOT NULL - false
        assert evaluator.evaluate(("is_null", "this.deletedAt", True)) is False

    def test_now_function(self):
        """Test evaluating NOW() function."""
        ctx = EvaluationContext(
            entity={"createdAt": datetime.now()},
            old_values={},
            session=None
        )
        evaluator = ExpressionEvaluator(ctx)

        # NOW() should return a datetime
        now_result = evaluator.evaluate(("call", "NOW", None))
        assert isinstance(now_result, datetime)

        # Can compare with datetime
        comparison = evaluator.evaluate(("op", "<=", "this.createdAt", ("call", "NOW", None)))
        assert comparison is True

    def test_concat_function(self):
        """Test evaluating CONCAT() function."""
        ctx = EvaluationContext(
            entity={"firstName": "John", "lastName": "Doe"},
            old_values={},
            session=None
        )
        evaluator = ExpressionEvaluator(ctx)

        # CONCAT with multiple arguments
        result = evaluator.evaluate(("call", "CONCAT", ["this.firstName", " ", "this.lastName"]))
        assert result == "John Doe"

        # CONCAT with two arguments
        result = evaluator.evaluate(("call", "CONCAT", ["this.firstName", "this.lastName"]))
        assert result == "JohnDoe"

        # CONCAT with literals
        result = evaluator.evaluate(("call", "CONCAT", ["Hello", " ", "World"]))
        assert result == "Hello World"

    def test_resolve_path(self):
        """Test resolving property paths."""
        ctx = EvaluationContext(
            entity={"name": "Test", "nested": {"value": 42}},
            old_values={},
            session=None
        )
        evaluator = ExpressionEvaluator(ctx)

        # Simple path
        assert evaluator._resolve_value("this.name") == "Test"

        # Nested path
        assert evaluator._resolve_value("this.nested.value") == 42

        # Missing path
        assert evaluator._resolve_value("this.missing") is None
        assert evaluator._resolve_value("this.nested.missing") is None
