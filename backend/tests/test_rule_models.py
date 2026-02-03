import pytest
from app.models.rule import Rule, ActionDefinition


def test_action_definition_model():
    """Test ActionDefinition model creation and defaults."""
    action = ActionDefinition(
        name="PurchaseOrder.submit",
        entity_type="PurchaseOrder",
        dsl_content='ACTION PurchaseOrder.submit { }'
    )
    assert action.name == "PurchaseOrder.submit"
    assert action.entity_type == "PurchaseOrder"
    assert action.dsl_content == 'ACTION PurchaseOrder.submit { }'
    assert action.is_active is True  # default value
    assert action.id is None  # not saved yet


def test_action_definition_model_with_is_active():
    """Test ActionDefinition model with explicit is_active."""
    action = ActionDefinition(
        name="Invoice.approve",
        entity_type="Invoice",
        dsl_content='ACTION Invoice.approve { }',
        is_active=False
    )
    assert action.name == "Invoice.approve"
    assert action.entity_type == "Invoice"
    assert action.is_active is False


def test_rule_model():
    """Test Rule model creation and defaults."""
    rule = Rule(
        name="SupplierStatusBlocking",
        trigger_type="UPDATE",
        trigger_entity="Supplier",
        trigger_property="status",
        dsl_content='RULE SupplierStatusBlocking { }'
    )
    assert rule.name == "SupplierStatusBlocking"
    assert rule.trigger_type == "UPDATE"
    assert rule.trigger_entity == "Supplier"
    assert rule.trigger_property == "status"
    assert rule.dsl_content == 'RULE SupplierStatusBlocking { }'
    assert rule.priority == 0  # default value
    assert rule.is_active is True  # default value
    assert rule.id is None  # not saved yet


def test_rule_model_with_optional_trigger_property():
    """Test Rule model without trigger_property (optional field)."""
    rule = Rule(
        name="AnySupplierChange",
        trigger_type="UPDATE",
        trigger_entity="Supplier",
        dsl_content='RULE AnySupplierChange { }'
    )
    assert rule.name == "AnySupplierChange"
    assert rule.trigger_type == "UPDATE"
    assert rule.trigger_entity == "Supplier"
    assert rule.trigger_property is None  # optional field


def test_rule_model_with_explicit_priority_and_is_active():
    """Test Rule model with explicit priority and is_active."""
    rule = Rule(
        name="HighPriorityRule",
        trigger_type="CREATE",
        trigger_entity="PurchaseOrder",
        dsl_content='RULE HighPriorityRule { }',
        priority=100,
        is_active=False
    )
    assert rule.name == "HighPriorityRule"
    assert rule.priority == 100
    assert rule.is_active is False


def test_rule_trigger_types():
    """Test that Rule accepts valid trigger types."""
    valid_trigger_types = ["UPDATE", "CREATE", "DELETE"]
    for trigger_type in valid_trigger_types:
        rule = Rule(
            name=f"TestRule{trigger_type}",
            trigger_type=trigger_type,
            trigger_entity="TestEntity",
            dsl_content=f'RULE TestRule{trigger_type} {{ }}'
        )
        assert rule.trigger_type == trigger_type
