from typing import Any
from app.rule_engine.base_registry import BaseRegistry
from app.rule_engine.models import ActionDef


class ActionRegistry(BaseRegistry):
    """Registry for ACTION definitions.

    The registry stores ActionDef objects and provides methods for
    looking them up by entity type and action name.
    """

    def __init__(self):
        """Initialize an empty registry."""
        super().__init__()
        self._actions: dict[tuple[str, str], ActionDef] = {}

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

    def unregister(self, entity_type: str, action_name: str) -> bool:
        """Unregister an ACTION definition.

        Args:
            entity_type: The entity type
            action_name: The action name

        Returns:
            True if action was unregistered, False if not found
        """
        key = (entity_type, action_name)
        if key in self._actions:
            del self._actions[key]
            return True
        return False

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

    def _register_parsed_items(self, parsed: list[Any]) -> None:
        """Register ActionDef objects from parsed output.

        Args:
            parsed: List of parsed objects (ActionDef or RuleDef)
        """
        for item in parsed:
            if isinstance(item, ActionDef):
                self.register(item)
