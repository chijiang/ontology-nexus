"""Rule engine package for reactive state management over PostgreSQL graph.

This package provides a complete DSL-based rule engine for defining and
executing reactive rules over a PostgreSQL knowledge graph. It supports:

- ACTION definitions with preconditions and effects
- RULE definitions triggered by graph events
- Expression evaluation with built-in functions
- SQL/PGQ translation for graph queries
- Event-driven rule execution
"""

# Parser
from app.rule_engine.parser import RuleParser

# Action registry and executor
from app.rule_engine.action_registry import ActionRegistry
from app.rule_engine.action_executor import ActionExecutor, ExecutionResult

# Rule registry and engine
from app.rule_engine.rule_registry import RuleRegistry
from app.rule_engine.rule_engine import RuleEngine

# Evaluation context and expression evaluator
from app.rule_engine.context import EvaluationContext
from app.rule_engine.evaluator import ExpressionEvaluator

# SQL/PGQ translator (replaces CypherTranslator)
from app.rule_engine.pgq_translator import PGQTranslator

# Event emitter
from app.rule_engine.event_emitter import GraphEventEmitter

# Built-in functions
from app.rule_engine.functions import BuiltinFunctions, evaluate_function

# Data models
from app.rule_engine.models import (
    # Trigger types
    TriggerType,
    Trigger,
    # Action definition
    ActionDef,
    Precondition,
    Parameter,
    # Rule definition
    RuleDef,
    ForClause,
    SetStatement,
    TriggerStatement,
    # Event types
    UpdateEvent,
    ActionResult,
)

# Parser AST node
from app.rule_engine.parser import EffectBlock

__all__ = [
    # Parser
    "RuleParser",
    # Action registry and executor
    "ActionRegistry",
    "ActionExecutor",
    "ExecutionResult",
    # Rule registry and engine
    "RuleRegistry",
    "RuleEngine",
    # Evaluation context and expression evaluator
    "EvaluationContext",
    "ExpressionEvaluator",
    # SQL/PGQ translator (replaces CypherTranslator)
    "PGQTranslator",
    # Event emitter
    "GraphEventEmitter",
    # Built-in functions
    "BuiltinFunctions",
    "evaluate_function",
    # Data models
    "TriggerType",
    "Trigger",
    "ActionDef",
    "Precondition",
    "Parameter",
    "RuleDef",
    "ForClause",
    "SetStatement",
    "TriggerStatement",
    "UpdateEvent",
    "ActionResult",
    "EffectBlock",
]
