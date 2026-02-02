"""Shared data models for rule engine."""

from dataclasses import dataclass, field
from typing import Any, Callable
from enum import Enum


class TriggerType(Enum):
    UPDATE = "UPDATE"
    CREATE = "CREATE"
    DELETE = "DELETE"
    LINK = "LINK"
    SCAN = "SCAN"


@dataclass
class Trigger:
    type: TriggerType
    entity_type: str
    property: str | None = None


@dataclass
class Precondition:
    name: str | None
    condition: Any  # AST Expression node
    on_failure: str


@dataclass
class Parameter:
    name: str
    param_type: str
    optional: bool = False


@dataclass
class ActionDef:
    entity_type: str
    action_name: str
    parameters: list[Parameter]
    preconditions: list[Precondition]
    effect: Any | None  # AST EffectBlock node


@dataclass
class SetStatement:
    target: str  # property path
    value: Any  # AST Expression node


@dataclass
class TriggerStatement:
    entity_type: str
    action_name: str
    target: str  # variable name
    params: dict[str, Any] | None = None


@dataclass
class ForClause:
    variable: str
    entity_type: str
    condition: Any | None  # AST Expression node
    statements: list[Any]  # SetStatement, TriggerStatement, or ForClause


@dataclass
class RuleDef:
    name: str
    priority: int
    trigger: Trigger
    body: ForClause


@dataclass
class UpdateEvent:
    entity_type: str
    entity_id: str
    property: str
    old_value: Any
    new_value: Any


@dataclass
class ActionResult:
    success: bool
    error: str | None = None
    changes: dict[str, Any] = field(default_factory=dict)
