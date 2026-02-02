"""Tests for Cypher translator."""

import pytest
from app.rule_engine.cypher_translator import CypherTranslator
from app.rule_engine.models import ForClause, Trigger, TriggerType, RuleDef, SetStatement


class TestTranslateFor:
    """Tests for translate_for method."""

    def test_simple_for_clause(self):
        """Test translating a simple FOR clause without conditions."""
        for_clause = ForClause(
            variable="s",
            entity_type="Supplier",
            condition=None,
            statements=[]
        )

        translator = CypherTranslator()
        query = translator.translate_for(for_clause)

        # Should match all Supplier nodes
        assert "MATCH" in query
        assert "(s:Supplier)" in query
        assert "RETURN" in query
        assert "s" in query

    def test_for_clause_with_in_condition(self):
        """Test translating FOR clause with IN condition."""
        # IN condition AST: ("op", "IN", left, right)
        # where left is a path like "s.status" and right is a list
        condition = ("op", "IN", ("path", "s.status"), ["Expired", "Blacklisted"])

        for_clause = ForClause(
            variable="s",
            entity_type="Supplier",
            condition=condition,
            statements=[]
        )

        translator = CypherTranslator()
        query = translator.translate_for(for_clause)

        assert "MATCH" in query
        assert "(s:Supplier)" in query
        assert "WHERE" in query
        # IN operator should be translated to Cypher's IN
        assert "IN" in query

    def test_for_clause_with_equals_condition(self):
        """Test translating FOR clause with equality condition."""
        condition = ("op", "==", ("path", "s.status"), "Active")

        for_clause = ForClause(
            variable="po",
            entity_type="PurchaseOrder",
            condition=condition,
            statements=[]
        )

        translator = CypherTranslator()
        query = translator.translate_for(for_clause)

        assert "MATCH" in query
        assert "(po:PurchaseOrder)" in query
        assert "WHERE" in query
        # Should contain the status value
        assert "Active" in query

    def test_for_clause_with_and_condition(self):
        """Test translating FOR clause with AND condition."""
        # AND condition AST: ("and", left, right)
        condition = ("and",
                     ("op", "==", ("path", "s.status"), "Active"),
                     ("op", ">", ("path", "s.rating"), 5))

        for_clause = ForClause(
            variable="s",
            entity_type="Supplier",
            condition=condition,
            statements=[]
        )

        translator = CypherTranslator()
        query = translator.translate_for(for_clause)

        assert "MATCH" in query
        assert "(s:Supplier)" in query
        assert "WHERE" in query
        assert "AND" in query


class TestTranslateCondition:
    """Tests for translate_condition method."""

    def test_translate_simple_equality(self):
        """Test translating simple equality condition."""
        condition = ("op", "==", ("path", "s.status"), "Active")

        translator = CypherTranslator()
        cypher = translator.translate_condition(condition)

        assert "s.status" in cypher
        assert "=" in cypher

    def test_translate_in_condition(self):
        """Test translating IN condition."""
        condition = ("op", "IN", ("path", "s.status"), ["Expired", "Blacklisted"])

        translator = CypherTranslator()
        cypher = translator.translate_condition(condition)

        assert "s.status" in cypher
        assert "IN" in cypher

    def test_translate_and_condition(self):
        """Test translating AND condition."""
        condition = ("and",
                     ("op", "==", ("path", "s.status"), "Active"),
                     ("op", ">", ("path", "s.rating"), 5))

        translator = CypherTranslator()
        cypher = translator.translate_condition(condition)

        assert "AND" in cypher

    def test_translate_or_condition(self):
        """Test translating OR condition."""
        condition = ("or",
                     ("op", "==", ("path", "s.status"), "Active"),
                     ("op", "==", ("path", "s.status"), "Pending"))

        translator = CypherTranslator()
        cypher = translator.translate_condition(condition)

        assert "OR" in cypher

    def test_translate_not_condition(self):
        """Test translating NOT condition."""
        condition = ("not", ("op", "==", ("path", "s.status"), "Active"))

        translator = CypherTranslator()
        cypher = translator.translate_condition(condition)

        assert "NOT" in cypher


class TestBindVariable:
    """Tests for bind_variable method."""

    def test_bind_variable_with_entity_id(self):
        """Test binding a variable with specific entity ID."""
        translator = CypherTranslator()
        translator.bind_variable("s", "Supplier", "supplier-123")

        # Check that the variable is stored
        assert "s" in translator._bound_vars
        assert translator._bound_vars["s"] == ("Supplier", "supplier-123")

    def test_bind_multiple_variables(self):
        """Test binding multiple variables."""
        translator = CypherTranslator()
        translator.bind_variable("s", "Supplier", "supplier-123")
        translator.bind_variable("po", "PurchaseOrder", "po-456")

        assert len(translator._bound_vars) == 2
        assert translator._bound_vars["s"] == ("Supplier", "supplier-123")
        assert translator._bound_vars["po"] == ("PurchaseOrder", "po-456")


class TestRelationshipTraversal:
    """Tests for relationship-based queries."""

    def test_for_clause_with_relationship(self):
        """Test translating FOR clause that uses a relationship."""
        # Relationship condition: po -[orderedFrom]-> s
        # This is represented as a pattern in the AST
        condition = ("pattern", ("po", "orderedFrom", "s"))

        for_clause = ForClause(
            variable="po",
            entity_type="PurchaseOrder",
            condition=condition,
            statements=[]
        )

        # Bind the outer variable 's'
        translator = CypherTranslator()
        translator.bind_variable("s", "Supplier", "supplier-123")

        query = translator.translate_for(for_clause)

        # Should include relationship pattern
        assert "MATCH" in query
        assert "(po:PurchaseOrder)" in query
        assert "orderedFrom" in query or "ORDERED_FROM" in query

    def test_nested_for_with_relationship(self):
        """Test nested FOR clauses with relationship."""
        # Outer FOR clause
        outer_for = ForClause(
            variable="s",
            entity_type="Supplier",
            condition=("op", "IN", ("path", "s.status"), ["Expired"]),
            statements=[]
        )

        # Inner FOR clause with relationship
        condition = ("pattern", ("po", "orderedFrom", "s"))
        inner_for = ForClause(
            variable="po",
            entity_type="PurchaseOrder",
            condition=condition,
            statements=[]
        )

        translator = CypherTranslator()
        outer_query = translator.translate_for(outer_for)
        inner_query = translator.translate_for(inner_for)

        assert "Supplier" in outer_query
        assert "PurchaseOrder" in inner_query


class TestCompleteRuleTranslation:
    """Tests for translating complete rules."""

    def test_translate_complete_rule(self):
        """Test translating a complete rule with trigger and body."""
        condition = ("op", "IN", ("path", "s.status"), ["Expired", "Blacklisted"])

        rule = RuleDef(
            name="SupplierStatusBlocking",
            priority=100,
            trigger=Trigger(
                type=TriggerType.UPDATE,
                entity_type="Supplier",
                property="status"
            ),
            body=ForClause(
                variable="s",
                entity_type="Supplier",
                condition=condition,
                statements=[
                    SetStatement(target="s.locked", value=True)
                ]
            )
        )

        translator = CypherTranslator()
        query = translator.translate_for(rule.body)

        assert "MATCH" in query
        assert "(s:Supplier)" in query
        assert "WHERE" in query
