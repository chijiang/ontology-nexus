"""Tests for DSL parser."""

import pytest
from app.rule_engine.parser import RuleParser
from app.rule_engine.models import ForClause


def test_parse_simple_rule():
    """Test parsing a simple RULE definition."""
    dsl_text = """
    RULE SupplierStatusBlocking PRIORITY 100 {
        ON UPDATE(Supplier.status)
        FOR (s: Supplier WHERE s.status IN ["Expired", "Blacklisted"]) {
            SET s.locked = true;
        }
    }
    """

    parser = RuleParser()
    result = parser.parse(dsl_text)

    assert len(result) == 1
    rule = result[0]
    assert rule.name == "SupplierStatusBlocking"
    assert rule.priority == 100
    assert rule.trigger.type.value == "UPDATE"
    assert rule.trigger.entity_type == "Supplier"
    assert rule.trigger.property == "status"


def test_parse_rule_with_nested_for():
    """Test parsing a RULE with nested FOR clauses."""
    dsl_text = """
    RULE SupplierStatusBlocking PRIORITY 100 {
        ON UPDATE(Supplier.status)
        FOR (s: Supplier WHERE s.status IN ["Expired"]) {
            FOR (po: PurchaseOrder WHERE po -[orderedFrom]-> s) {
                SET po.status = "RiskLocked";
            }
        }
    }
    """

    parser = RuleParser()
    result = parser.parse(dsl_text)

    assert len(result) == 1
    rule = result[0]
    assert rule.body.variable == "s"
    assert len(rule.body.statements) == 1
    assert isinstance(rule.body.statements[0], ForClause)


def test_parse_action_with_preconditions():
    """Test parsing an ACTION with PRECONDITIONs."""
    dsl_text = """
    ACTION PurchaseOrder.submit {
        PRECONDITION statusCheck: this.status == "Draft"
            ON_FAILURE: "Only draft orders can be submitted"
        PRECONDITION: this.amount > 0
            ON_FAILURE: "Amount must be positive"
    }
    """

    parser = RuleParser()
    result = parser.parse(dsl_text)

    assert len(result) == 1
    action = result[0]
    assert action.entity_type == "PurchaseOrder"
    assert action.action_name == "submit"
    assert len(action.preconditions) == 2
    assert action.preconditions[0].name == "statusCheck"
    assert action.preconditions[0].on_failure == "Only draft orders can be submitted"


def test_parse_action_with_effect():
    """Test parsing an ACTION with EFFECT block."""
    dsl_text = """
    ACTION PurchaseOrder.cancel {
        PRECONDITION: this.status == "Open"
            ON_FAILURE: "Cannot cancel"
        EFFECT {
            SET this.status = "Cancelled";
            SET this.cancelledAt = NOW();
        }
    }
    """

    parser = RuleParser()
    result = parser.parse(dsl_text)

    assert len(result) == 1
    action = result[0]
    assert action.effect is not None
    assert len(action.effect.statements) == 2


def test_parse_sample_rule():
    """Test parsing the sample SupplierStatusBlocking rule."""
    with open("tests/rule_engine/fixtures/sample_rules.dsl") as f:
        dsl_text = f.read()

    parser = RuleParser()
    result = parser.parse(dsl_text)

    assert len(result) == 1
    rule = result[0]
    assert rule.name == "SupplierStatusBlocking"
    assert rule.priority == 100
