"""DSL Parser using Lark."""

from lark import Lark, Transformer, Token
from pathlib import Path
from app.rule_engine.models import (
    ActionDef,
    RuleDef,
    Precondition,
    Parameter,
    Trigger,
    TriggerType,
    ForClause,
    SetStatement,
    TriggerStatement,
)
from typing import Any, Union


class EffectBlock:
    """Effect block with statements."""

    def __init__(self, statements):
        self.statements = statements


class ASTTransformer(Transformer):
    """Transform Lark parse tree into AST nodes."""

    # Token handlers - these receive the token directly
    def CNAME(self, token: Token) -> str:
        return str(token)

    def STRING(self, token: Token) -> str:
        # Strip quotes from string
        s = str(token)
        if s.startswith('"') and s.endswith('"'):
            return s[1:-1]
        return s

    def NUMBER(self, token: Token) -> int | float:
        s = str(token)
        return float(s) if "." in s else int(s)

    def UPDATE(self, token: Token) -> str:
        return "UPDATE"

    def CREATE(self, token: Token) -> str:
        return "CREATE"

    def DELETE(self, token: Token) -> str:
        return "DELETE"

    def LINK(self, token: Token) -> str:
        return "LINK"

    def SCAN(self, token: Token) -> str:
        return "SCAN"

    # Comparison operator token handlers
    def EQ(self, token: Token) -> str:
        return "=="

    def NEQ(self, token: Token) -> str:
        return "!="

    def LT(self, token: Token) -> str:
        return "<"

    def GT(self, token: Token) -> str:
        return ">"

    def LTE(self, token: Token) -> str:
        return "<="

    def GTE(self, token: Token) -> str:
        return ">="

    def IN(self, token: Token) -> str:
        return "IN"

    def IS(self, token: Token) -> str:
        return "IS"

    def NOT(self, token: Token) -> str:
        return "NOT"

    def NULL(self, token: Token) -> None:
        return None

    def MATCHES(self, token: Token) -> str:
        return "MATCHES"

    def CHANGED(self, token: Token) -> str:
        return "CHANGED"

    def FROM(self, token: Token) -> str:
        return "FROM"

    def TO(self, token: Token) -> str:
        return "TO"

    def EXISTS(self, token: Token) -> str:
        return "EXISTS"

    def AND(self, token: Token) -> str:
        return "AND"

    def OR(self, token: Token) -> str:
        return "OR"

    # Rule handlers
    def start(self, items):
        # Return items as a list
        return list(items)

    def action_def(self, items):
        # items: [entity_action, precondition+, effect?]
        # The grammar is: action_def: "ACTION" entity_action "{" precondition+ effect? "}"
        # So after filtering keywords, we get: entity_action, then all preconditions, then optional effect
        entity_action = items[0]

        # Find where preconditions end and effect begins
        # Preconditions are Precondition objects, effect is None or an EffectBlock
        preconditions = []
        effect = None

        for item in items[1:]:
            if isinstance(item, Precondition):
                preconditions.append(item)
            elif isinstance(item, EffectBlock) or item is None:
                effect = item

        # If there's no effect, check if the last item could be it
        if (
            effect is None
            and len(items) > 1
            and not isinstance(items[-1], Precondition)
        ):
            effect = items[-1]

        entity_type, action_name, parameters = entity_action
        return ActionDef(
            entity_type=entity_type,
            action_name=action_name,
            parameters=parameters,
            preconditions=preconditions,
            effect=effect,
        )

    def entity_action(self, items):
        # items: [CNAME, CNAME] or [CNAME, CNAME, param_list]
        entity_type = items[0]
        action_name = items[1]
        params = items[2] if len(items) > 2 else []
        return (entity_type, action_name, params)

    def param_list(self, items):
        return items

    def param(self, items):
        # items: [CNAME, CNAME] or [CNAME, CNAME, "?"]
        name = items[0]
        param_type = items[1]
        optional = len(items) > 2 and items[2] == "?"
        return Parameter(name=name, param_type=param_type, optional=optional)

    def precondition(self, items):
        # items can be [CNAME, expression, STRING] or [expression, STRING]
        # precondition: "PRECONDITION" [CNAME] ":" expression "ON_FAILURE" ":" STRING
        # After filtering out keywords, we get: [name?, expression, on_failure]
        if len(items) == 3:
            name = items[0]
            condition = items[1]
            on_failure = items[2]
        else:
            # name is optional
            name = None
            condition = items[0]
            on_failure = items[1]
        return Precondition(name=name, condition=condition, on_failure=on_failure)

    def effect(self, items):
        if not items:
            return None
        return EffectBlock(statements=items)

    def rule_def(self, items):
        # items: [CNAME, priority?, trigger, for_clause]
        name = items[0]
        priority_idx = 1
        trigger_idx = 2

        # Check if priority is present
        if isinstance(items[1], int):
            priority = items[1]
            trigger_idx = 2
        else:
            priority = 0  # default priority
            trigger_idx = 1

        trigger = items[trigger_idx]
        body = items[trigger_idx + 1]

        return RuleDef(name=name, priority=priority, trigger=trigger, body=body)

    def priority(self, items):
        return int(items[0])

    def trigger(self, items):
        # items: [trigger_type, trigger_target]
        trigger_type = items[0]
        target = items[1]

        # Split target into entity_type and property
        parts = target.split(".")
        entity_type = parts[0]
        property = parts[1] if len(parts) > 1 else None

        return Trigger(
            type=TriggerType(trigger_type), entity_type=entity_type, property=property
        )

    def trigger_type(self, items):
        # Now that we have named terminals (UPDATE, CREATE, etc.),
        # this method receives the token value.
        if items:
            return str(items[0])
        return "UPDATE"  # fallback

    def trigger_target(self, items):
        # items: [CNAME] or [CNAME, CNAME]
        if len(items) == 1:
            return items[0]
        return f"{items[0]}.{items[1]}"

    def for_clause(self, items):
        # items: [binding, statement*]
        binding = items[0]
        statements = items[1:] if len(items) > 1 else []

        var, entity_type, condition = binding
        return ForClause(
            variable=var,
            entity_type=entity_type,
            condition=condition,
            statements=statements,
        )

    def binding(self, items):
        # items: [CNAME, CNAME] or [CNAME, CNAME, expression]
        var = items[0]
        entity_type = items[1]
        condition = items[2] if len(items) > 2 else None
        return (var, entity_type, condition)

    def statement(self, items):
        return items[0]

    def set_stmt(self, items):
        # items: [path, expression]
        target = items[0]
        value = items[1]
        return SetStatement(target=target, value=value)

    def trigger_stmt(self, items):
        # items: [entity_action, CNAME, object?]
        entity_action = items[0]
        target = items[1]
        params = items[2] if len(items) > 2 else None

        entity_type, action_name = entity_action
        return TriggerStatement(
            entity_type=entity_type,
            action_name=action_name,
            target=target,
            params=params,
        )

    def path(self, items):
        return ".".join(items)

    def object(self, items):
        return dict(items) if items else {}

    def member(self, items):
        return (items[0], items[1])

    def value_list(self, items):
        return items

    def function_call(self, items):
        name = items[0]
        args = items[1] if len(items) > 1 else []
        return ("call", name, args)

    def expression(self, items):
        return items[0]

    def or_expr(self, items):
        # Filter out the "OR" terminals and keep only the expressions
        expressions = [item for item in items if item != "OR"]
        if len(expressions) == 1:
            return expressions[0]
        # Build left-associative OR chain
        result = expressions[0]
        for i in range(1, len(expressions)):
            result = ("or", result, expressions[i])
        return result

    def and_expr(self, items):
        # Filter out the "AND" terminals and keep only the expressions
        expressions = [item for item in items if item != "AND"]
        if len(expressions) == 1:
            return expressions[0]
        # Build left-associative AND chain
        result = expressions[0]
        for i in range(1, len(expressions)):
            result = ("and", result, expressions[i])
        return result

    def not_expr(self, items):
        # When NOT is optional [NOT], Lark passes:
        # - 1 item if NOT is not present: [comparison]
        # - 2 items if NOT is present: ["NOT", comparison]
        # But it can also pass 2 items with None: [None, comparison]
        if len(items) == 1:
            return items[0]
        # Check if NOT is actually present (not None)
        if items[0] == "NOT":
            return ("not", items[1])
        # NOT is not present (items[0] is None)
        return items[1]

    def comparison(self, items):
        """Handle comparison expressions.

        The grammar has several forms:
        - term [comp_op term] - binary comparison with optional operator
        - term IN "[" [value_list] "]" - IN operator
        - term IS [NOT] NULL - IS NULL check
        - term MATCHES STRING - regex match
        - term CHANGED [FROM value TO value] - change detection
        - EXISTS "(" pattern ")" - existence check
        - term relationship term - relationship check

        When the comparison is just a single term (no operator), items has 1 element.
        When there's an IN/IS NULL/MATCHES/CHANGED/EXISTS/relationship, items has 2-4 elements.
        When there's a binary comparison (term op term), items has 3 elements.
        """
        if len(items) == 1:
            return items[0]

        # Filter out None values from optional parts
        # When comp_op is not present, it might appear as None
        non_none_items = [item for item in items if item is not None]

        if len(non_none_items) == 1:
            # Only a single term, no comparison operator
            return non_none_items[0]

        if len(items) == 2:
            # Check if this is an IS NULL or IS NOT NULL case
            # items could be: [term, None] for "term IS NULL" -> handled by ternary
            # or it could be the result of a special operator
            if items[1] is None:
                return items[0]  # Just a term, no operator
            return items[1]

        # Check if we have a valid comparison operator
        op = items[1]
        if op is None:
            # No operator, just return the term
            return items[0]

        if op == "IS":
            # IS NULL or IS NOT NULL
            # For "term IS NULL": items = [term, "IS", None, None] or [term, "IS", None]
            # For "term IS NOT NULL": items = [term, "IS", "NOT", None] or [term, "IS", "NOT"]
            # The last item is always None (the NULL token)
            is_not = (len(items) > 2 and items[2] == "NOT") or (
                len(items) > 3 and items[2] == "NOT"
            )
            return ("is_null", items[0], is_not)

        # Binary comparison: term op term
        return ("op", op, items[0], items[2])

    def comp_op(self, items):
        """Extract comparison operator from token."""
        # items[0] is a Token with type like '__ANON_0' or similar
        # We need to extract the string value
        if items:
            return str(items[0].value) if hasattr(items[0], "value") else str(items[0])
        return None

    def term(self, items):
        return items[0]

    def true_lit(self, items):
        return True

    def false_lit(self, items):
        return False

    def value(self, items):
        # items can be empty for boolean/NULL literals that are matched directly
        if not items:
            return None
        return items[0]

    def pattern(self, items):
        return items

    def relationship(self, items):
        return items

    def arg_list(self, items):
        return items


class RuleParser:
    """Parser for ACTION and RULE DSL."""

    def __init__(self):
        grammar_path = Path(__file__).parent / "grammar.lark"
        with open(grammar_path) as f:
            grammar = f.read()

        self.lark = Lark(
            grammar, parser="lalr", transformer=ASTTransformer(), start="start"
        )

    def parse(self, dsl_text: str) -> list[Union[ActionDef, RuleDef]]:
        """Parse DSL text into AST."""
        return self.lark.parse(dsl_text)

    def parse_file(self, file_path: str) -> list[Union[ActionDef, RuleDef]]:
        """Parse DSL file into AST."""
        with open(file_path) as f:
            return self.parse(f.read())
