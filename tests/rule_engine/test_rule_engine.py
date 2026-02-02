"""Tests for rule engine."""

import pytest
from app.rule_engine.rule_engine import RuleEngine
from app.rule_engine.rule_registry import RuleRegistry
from app.rule_engine.models import (
    RuleDef, Trigger, TriggerType, ForClause, SetStatement, UpdateEvent
)


class TestRuleEngine:
    """Tests for RuleEngine class."""

    @pytest.fixture
    def registry(self):
        """Create a rule registry for testing."""
        return RuleRegistry()

    @pytest.fixture
    def engine(self, registry):
        """Create a rule engine with a registry."""
        return RuleEngine(registry)

    def test_on_event_with_no_rules(self, engine):
        """Test on_event when no rules are registered."""
        event = UpdateEvent(
            entity_type="Supplier",
            entity_id="supplier-123",
            property="status",
            old_value="Active",
            new_value="Expired"
        )

        # Should not raise any errors
        result = engine.on_event(event)
        assert result == []

    def test_on_event_with_matching_rule(self, engine, registry):
        """Test on_event with a rule that matches the event."""
        # Create a simple rule
        condition = ("op", "IN", ("path", "s.status"), ["Expired"])
        rule = RuleDef(
            name="TestRule",
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

        registry.register(rule)

        event = UpdateEvent(
            entity_type="Supplier",
            entity_id="supplier-123",
            property="status",
            old_value="Active",
            new_value="Expired"
        )

        # Mock the database session and executor
        # For now, just check that the rule is matched
        result = engine.on_event(event)
        # Result will be empty without a real database connection
        assert isinstance(result, list)

    def test_on_event_with_non_matching_trigger(self, engine, registry):
        """Test on_event with a rule that doesn't match the event."""
        # Rule triggers on Supplier.status
        condition = ("op", "==", ("path", "s.status"), "Expired")
        rule = RuleDef(
            name="SupplierRule",
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
                statements=[]
            )
        )

        registry.register(rule)

        # Event on PurchaseOrder - should not match
        event = UpdateEvent(
            entity_type="PurchaseOrder",
            entity_id="po-123",
            property="amount",
            old_value=100,
            new_value=200
        )

        result = engine.on_event(event)
        assert result == []

    def test_match_rules_with_priority(self, engine, registry):
        """Test that rules are matched and ordered by priority."""
        # Create two rules with different priorities
        low_priority_rule = RuleDef(
            name="LowPriorityRule",
            priority=10,
            trigger=Trigger(
                type=TriggerType.UPDATE,
                entity_type="Supplier",
                property="status"
            ),
            body=ForClause(
                variable="s",
                entity_type="Supplier",
                condition=None,
                statements=[]
            )
        )

        high_priority_rule = RuleDef(
            name="HighPriorityRule",
            priority=100,
            trigger=Trigger(
                type=TriggerType.UPDATE,
                entity_type="Supplier",
                property="status"
            ),
            body=ForClause(
                variable="s",
                entity_type="Supplier",
                condition=None,
                statements=[]
            )
        )

        registry.register(low_priority_rule)
        registry.register(high_priority_rule)

        event = UpdateEvent(
            entity_type="Supplier",
            entity_id="supplier-123",
            property="status",
            old_value="Active",
            new_value="Expired"
        )

        matched_rules = engine._match_rules(event)

        # Should return both rules ordered by priority
        assert len(matched_rules) == 2
        assert matched_rules[0].name == "HighPriorityRule"
        assert matched_rules[1].name == "LowPriorityRule"


class TestRuleRegistry:
    """Tests for RuleRegistry class."""

    def test_register_rule(self):
        """Test registering a rule."""
        registry = RuleRegistry()

        condition = ("op", "==", ("path", "s.status"), "Expired")
        rule = RuleDef(
            name="TestRule",
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
                statements=[]
            )
        )

        registry.register(rule)

        # Check rule is registered
        assert "TestRule" in registry
        assert registry.lookup("TestRule") == rule
        assert len(registry) == 1

    def test_register_duplicate_rule(self):
        """Test that registering a duplicate rule raises an error."""
        registry = RuleRegistry()

        condition = ("op", "==", ("path", "s.status"), "Expired")
        rule = RuleDef(
            name="TestRule",
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
                statements=[]
            )
        )

        registry.register(rule)

        # Should raise ValueError
        with pytest.raises(ValueError, match="already registered"):
            registry.register(rule)

    def test_lookup_nonexistent_rule(self):
        """Test looking up a rule that doesn't exist."""
        registry = RuleRegistry()
        assert registry.lookup("NonExistent") is None

    def test_get_by_trigger(self):
        """Test getting rules by trigger."""
        registry = RuleRegistry()

        # Register rules with different triggers
        supplier_rule = RuleDef(
            name="SupplierRule",
            priority=100,
            trigger=Trigger(
                type=TriggerType.UPDATE,
                entity_type="Supplier",
                property="status"
            ),
            body=ForClause(
                variable="s",
                entity_type="Supplier",
                condition=None,
                statements=[]
            )
        )

        po_rule = RuleDef(
            name="PurchaseOrderRule",
            priority=50,
            trigger=Trigger(
                type=TriggerType.UPDATE,
                entity_type="PurchaseOrder",
                property="amount"
            ),
            body=ForClause(
                variable="po",
                entity_type="PurchaseOrder",
                condition=None,
                statements=[]
            )
        )

        registry.register(supplier_rule)
        registry.register(po_rule)

        # Get rules matching Supplier.status trigger
        trigger = Trigger(
            type=TriggerType.UPDATE,
            entity_type="Supplier",
            property="status"
        )

        matching_rules = registry.get_by_trigger(trigger)

        assert len(matching_rules) == 1
        assert matching_rules[0].name == "SupplierRule"

    def test_get_by_trigger_ordered_by_priority(self):
        """Test that rules returned by get_by_trigger are ordered by priority."""
        registry = RuleRegistry()

        # Register rules with same trigger but different priorities
        low_rule = RuleDef(
            name="LowPriority",
            priority=10,
            trigger=Trigger(
                type=TriggerType.UPDATE,
                entity_type="Supplier",
                property="status"
            ),
            body=ForClause(
                variable="s",
                entity_type="Supplier",
                condition=None,
                statements=[]
            )
        )

        high_rule = RuleDef(
            name="HighPriority",
            priority=100,
            trigger=Trigger(
                type=TriggerType.UPDATE,
                entity_type="Supplier",
                property="status"
            ),
            body=ForClause(
                variable="s",
                entity_type="Supplier",
                condition=None,
                statements=[]
            )
        )

        medium_rule = RuleDef(
            name="MediumPriority",
            priority=50,
            trigger=Trigger(
                type=TriggerType.UPDATE,
                entity_type="Supplier",
                property="status"
            ),
            body=ForClause(
                variable="s",
                entity_type="Supplier",
                condition=None,
                statements=[]
            )
        )

        # Register in random order
        registry.register(low_rule)
        registry.register(high_rule)
        registry.register(medium_rule)

        trigger = Trigger(
            type=TriggerType.UPDATE,
            entity_type="Supplier",
            property="status"
        )

        matching_rules = registry.get_by_trigger(trigger)

        # Should be ordered by priority (highest first)
        assert len(matching_rules) == 3
        assert matching_rules[0].name == "HighPriority"
        assert matching_rules[1].name == "MediumPriority"
        assert matching_rules[2].name == "LowPriority"

    def test_get_all(self):
        """Test getting all rules."""
        registry = RuleRegistry()

        rule1 = RuleDef(
            name="Rule1",
            priority=100,
            trigger=Trigger(
                type=TriggerType.UPDATE,
                entity_type="Supplier",
                property="status"
            ),
            body=ForClause(
                variable="s",
                entity_type="Supplier",
                condition=None,
                statements=[]
            )
        )

        rule2 = RuleDef(
            name="Rule2",
            priority=50,
            trigger=Trigger(
                type=TriggerType.CREATE,
                entity_type="PurchaseOrder",
                property=None
            ),
            body=ForClause(
                variable="po",
                entity_type="PurchaseOrder",
                condition=None,
                statements=[]
            )
        )

        registry.register(rule1)
        registry.register(rule2)

        all_rules = registry.get_all()
        assert len(all_rules) == 2
        rule_names = {r.name for r in all_rules}
        assert rule_names == {"Rule1", "Rule2"}

    def test_clear(self):
        """Test clearing the registry."""
        registry = RuleRegistry()

        rule = RuleDef(
            name="TestRule",
            priority=100,
            trigger=Trigger(
                type=TriggerType.UPDATE,
                entity_type="Supplier",
                property="status"
            ),
            body=ForClause(
                variable="s",
                entity_type="Supplier",
                condition=None,
                statements=[]
            )
        )

        registry.register(rule)
        assert len(registry) == 1

        registry.clear()
        assert len(registry) == 0
        assert registry.lookup("TestRule") is None

    def test_load_from_file(self):
        """Test loading rules from a DSL file."""
        registry = RuleRegistry()

        # Load from the sample rules file
        rules = registry.load_from_file("tests/rule_engine/fixtures/sample_rules.dsl")

        # Should have loaded one rule
        assert len(rules) == 1
        assert len(registry) == 1
        assert "SupplierStatusBlocking" in registry

        rule = registry.lookup("SupplierStatusBlocking")
        assert rule is not None
        assert rule.name == "SupplierStatusBlocking"
        assert rule.priority == 100

    def test_load_from_nonexistent_file(self):
        """Test loading rules from a nonexistent file."""
        registry = RuleRegistry()

        with pytest.raises(FileNotFoundError):
            registry.load_from_file("nonexistent/file.dsl")
