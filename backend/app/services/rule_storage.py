"""Rule storage service for persisting rules to filesystem."""

import json
from pathlib import Path
from typing import Any
from app.rule_engine.models import RuleDef, ActionDef
from app.rule_engine.parser import RuleParser


class RuleStorage:
    """Storage service for rule definitions.

    The RuleStorage class handles loading, saving, and managing rule
    definitions on the filesystem. Rules are stored as JSON files with
    metadata and DSL content.
    """

    def __init__(self, storage_dir: str | Path):
        """Initialize the rule storage.

        Args:
            storage_dir: Directory where rule files are stored
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._parser = RuleParser()

    def save_rule(self, name: str, dsl_content: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        """Save a rule to storage.

        Args:
            name: Rule name
            dsl_content: DSL content of the rule
            metadata: Optional metadata to store with the rule

        Returns:
            Dictionary with rule metadata

        Raises:
            ValueError: If parsing fails
        """
        # Validate by parsing
        parsed = self._parser.parse(dsl_content)
        rule_defs = [item for item in parsed if isinstance(item, RuleDef)]

        if not rule_defs:
            raise ValueError(f"No valid RULE definition found in content")

        rule = rule_defs[0]

        # Create rule metadata
        rule_data = {
            "name": name,
            "dsl_content": dsl_content,
            "metadata": metadata or {},
            "rule_info": {
                "priority": rule.priority,
                "trigger": {
                    "type": rule.trigger.type.value,
                    "entity_type": rule.trigger.entity_type,
                    "property": rule.trigger.property
                }
            }
        }

        # Save to file
        file_path = self._get_rule_file_path(name)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(rule_data, f, indent=2)

        return rule_data

    def load_rule(self, name: str) -> dict[str, Any] | None:
        """Load a rule from storage.

        Args:
            name: Rule name

        Returns:
            Dictionary with rule data or None if not found
        """
        file_path = self._get_rule_file_path(name)
        if not file_path.exists():
            return None

        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def delete_rule(self, name: str) -> bool:
        """Delete a rule from storage.

        Args:
            name: Rule name

        Returns:
            True if deleted, False if not found
        """
        file_path = self._get_rule_file_path(name)
        if not file_path.exists():
            return False

        file_path.unlink()
        return True

    def list_rules(self) -> list[dict[str, Any]]:
        """List all rules in storage.

        Returns:
            List of rule metadata dictionaries
        """
        rules = []
        for file_path in self.storage_dir.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    rule_data = json.load(f)
                    rules.append({
                        "name": rule_data.get("name"),
                        "metadata": rule_data.get("metadata", {}),
                        "rule_info": rule_data.get("rule_info", {})
                    })
            except (json.JSONDecodeError, KeyError):
                # Skip invalid files
                continue

        return rules

    def rule_exists(self, name: str) -> bool:
        """Check if a rule exists in storage.

        Args:
            name: Rule name

        Returns:
            True if rule exists, False otherwise
        """
        return self._get_rule_file_path(name).exists()

    def _get_rule_file_path(self, name: str) -> Path:
        """Get the file path for a rule.

        Args:
            name: Rule name

        Returns:
            Path to the rule file
        """
        # Sanitize name to be safe for filesystem
        safe_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in name)
        return self.storage_dir / f"{safe_name}.json"
