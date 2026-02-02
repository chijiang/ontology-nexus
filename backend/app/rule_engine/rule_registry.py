"""Rule registry for managing rule definitions."""

from typing import Any
from pathlib import Path
from app.rule_engine.models import RuleDef, Trigger, TriggerType


class RuleRegistry:
    """Registry for managing rule definitions.

    The rule registry stores RuleDef objects and provides lookup
    functionality by rule name or trigger type.
    """

    def __init__(self):
        """Initialize an empty registry."""
        self._rules: dict[str, RuleDef] = {}
        self._trigger_index: dict[str, list[str]] = {}

    def register(self, rule: RuleDef) -> None:
        """Register a rule definition.

        Args:
            rule: The rule definition to register

        Raises:
            ValueError: If a rule with the same name already exists
        """
        if rule.name in self._rules:
            raise ValueError(f"Rule '{rule.name}' is already registered")

        self._rules[rule.name] = rule

        # Index by trigger for efficient lookup
        trigger_key = self._make_trigger_key(rule.trigger)
        if trigger_key not in self._trigger_index:
            self._trigger_index[trigger_key] = []
        self._trigger_index[trigger_key].append(rule.name)

    def lookup(self, rule_name: str) -> RuleDef | None:
        """Look up a rule by name.

        Args:
            rule_name: The name of the rule to look up

        Returns:
            The rule definition or None if not found
        """
        return self._rules.get(rule_name)

    def get_by_trigger(self, trigger: Trigger) -> list[RuleDef]:
        """Get rules matching a trigger.

        Args:
            trigger: The trigger to match against

        Returns:
            List of matching rule definitions, ordered by priority (highest first)
        """
        trigger_key = self._make_trigger_key(trigger)
        rule_names = self._trigger_index.get(trigger_key, [])

        # Get the rules and sort by priority (descending)
        rules = [self._rules[name] for name in rule_names if name in self._rules]
        rules.sort(key=lambda r: r.priority, reverse=True)

        return rules

    def get_all(self) -> list[RuleDef]:
        """Get all registered rules.

        Returns:
            List of all rule definitions
        """
        return list(self._rules.values())

    def load_from_file(self, file_path: str | Path) -> list[RuleDef]:
        """Load rules from a DSL file.

        Args:
            file_path: Path to the DSL file

        Returns:
            List of loaded rule definitions

        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If parsing fails
        """
        from app.rule_engine.parser import RuleParser

        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Rule file not found: {file_path}")

        parser = RuleParser()
        parsed = parser.parse_file(str(file_path))

        # Filter only RuleDef objects (exclude ActionDef)
        rules = [item for item in parsed if isinstance(item, RuleDef)]

        # Register each rule
        for rule in rules:
            self.register(rule)

        return rules

    def clear(self) -> None:
        """Clear all registered rules."""
        self._rules.clear()
        self._trigger_index.clear()

    def _make_trigger_key(self, trigger: Trigger) -> str:
        """Create a key for trigger indexing.

        Args:
            trigger: The trigger to create a key for

        Returns:
            A string key for indexing
        """
        parts = [trigger.type.value, trigger.entity_type]
        if trigger.property:
            parts.append(trigger.property)
        return ":".join(parts)

    def __len__(self) -> int:
        """Return the number of registered rules."""
        return len(self._rules)

    def __contains__(self, rule_name: str) -> bool:
        """Check if a rule is registered."""
        return rule_name in self._rules
