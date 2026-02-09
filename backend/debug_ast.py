from app.rule_engine.parser import RuleParser
import json

parser = RuleParser()
dsl = """
ACTION PurchaseOrder.openPO {
    PRECONDITION checkSupplier: NOT EXISTS(this -[orderedFrom]-> s:Supplier WHERE s.status != "Active")
        ON_FAILURE: "Fail"
    EFFECT { SET this.status = "Open"; }
}
"""
actions = parser.parse(dsl)
action = actions[0]
condition = action.preconditions[0].condition


def dump_ast(node):
    if isinstance(node, tuple):
        return [dump_ast(n) for n in node]
    elif isinstance(node, list):
        return [dump_ast(n) for n in node]
    elif hasattr(node, "__dict__"):
        return {k: dump_ast(v) for k, v in node.__dict__.items()}
    else:
        return node


print(json.dumps(dump_ast(condition), indent=2))
