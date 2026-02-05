"""Evaluation context for expressions."""

from dataclasses import dataclass, field
from typing import Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession as SQLAsyncSession


@dataclass
class EvaluationContext:
    """Context for evaluating expressions against entity data."""

    entity: dict[str, Any]
    old_values: dict[str, Any]
    session: Optional[SQLAsyncSession] = None  # PostgreSQL DB session (renamed from Neo4j session)
    variables: dict[str, Any] = field(default_factory=dict)

    @property
    def db(self) -> Optional[SQLAsyncSession]:
        """Alias for session for PostgreSQL compatibility."""
        return self.session

    def get_variable(self, name: str) -> Any:
        """Get a variable by name.

        Special variables:
        - "this" returns the current entity

        Args:
            name: Variable name

        Returns:
            Variable value or None if not found
        """
        if name == "this":
            return self.entity
        return self.variables.get(name)

    def resolve_path(self, path: str) -> Any:
        """Resolve a property path to a value.

        Paths can be:
        - "this.prop" -> entity["prop"]
        - "this.nested.prop" -> entity["nested"]["prop"]
        - "varName.prop" -> variables["varName"]["prop"]

        Args:
            path: Dot-separated property path

        Returns:
            Resolved value or None if path is invalid
        """
        parts = path.split(".")
        if not parts:
            return None

        # Get the root object
        root_name = parts[0]
        if root_name == "this":
            obj = self.entity
        else:
            obj = self.variables.get(root_name)
            if obj is None:
                return None

        # Navigate through nested properties
        for part in parts[1:]:
            if isinstance(obj, dict):
                obj = obj.get(part)
            else:
                return None
            if obj is None:
                return None

        return obj
