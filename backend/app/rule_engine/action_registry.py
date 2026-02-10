"""Action registry for storing and looking up ACTION definitions."""

from pathlib import Path
from typing import Any
from app.rule_engine.models import ActionDef
from app.rule_engine.parser import RuleParser


class ActionRegistry:
    """Registry for ACTION definitions.

    The registry stores ActionDef objects and provides methods for
    looking them up by entity type and action name. It can also load
    actions from DSL files or text.
    """

    def __init__(self):
        """Initialize an empty registry."""
        self._actions: dict[tuple[str, str], ActionDef] = {}
        self._parser = RuleParser()

    def register(self, action: ActionDef) -> None:
        """Register an ACTION definition.

        Args:
            action: ActionDef to register

        Note:
            If an action with the same entity_type and action_name
            already exists, it will be overwritten.
        """
        key = (action.entity_type, action.action_name)
        self._actions[key] = action

    def lookup(self, entity_type: str, action_name: str) -> ActionDef | None:
        """Look up an ACTION by entity type and name.

        Args:
            entity_type: The entity type (e.g., "PurchaseOrder")
            action_name: The action name (e.g., "submit")

        Returns:
            ActionDef if found, None otherwise
        """
        key = (entity_type, action_name)
        return self._actions.get(key)

    def list_by_entity(self, entity_type: str) -> list[ActionDef]:
        """List all actions for a specific entity type.

        Args:
            entity_type: The entity type to filter by

        Returns:
            List of ActionDef objects for the entity type
        """
        return [
            action for (et, _), action in self._actions.items() if et == entity_type
        ]

    def list_all(self) -> list[ActionDef]:
        """List all registered actions.

        Returns:
            List of all ActionDef objects in the registry
        """
        return list(self._actions.values())

    def load_from_file(self, file_path: str) -> None:
        """Load actions from a DSL file.

        Parses the DSL file and registers all ACTION definitions found.
        RULE definitions are ignored.

        Args:
            file_path: Path to the DSL file
        """
        parsed = self._parser.parse_file(file_path)
        self._register_actions_from_parsed(parsed)

    def load_from_text(self, dsl_text: str) -> None:
        """Load actions from DSL text.

        Parses the DSL text and registers all ACTION definitions found.
        RULE definitions are ignored.

        Args:
            dsl_text: DSL source text containing ACTION definitions
        """
        parsed = self._parser.parse(dsl_text)
        self._register_actions_from_parsed(parsed)

    def _register_actions_from_parsed(self, parsed: list[Any]) -> None:
        """Register ActionDef objects from parsed output.

        Args:
            parsed: List of parsed objects (ActionDef or RuleDef)
        """
        for item in parsed:
            if isinstance(item, ActionDef):
                self.register(item)
