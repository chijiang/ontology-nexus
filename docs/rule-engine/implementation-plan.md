# Rule Engine Implementation Plan

Complete development roadmap for the ACTION + RULE engine system.

---

## Project Overview

| Aspect | Detail |
|--------|--------|
| **Goal** | Build a rule engine that supports ACTION definitions with PRECONDITIONs and RULE definitions for reactive state management |
| **Stack** | Python (Backend), Lark (Parser), Neo4j (Graph DB) |
| **Timeline** | 6 phases, ~4-6 weeks estimated |

---

## Phase 1: DSL Parser

**Duration**: 3-5 days

### 1.1 Objectives
- Parse ACTION and RULE definitions from DSL text
- Generate Abstract Syntax Tree (AST) for execution

### 1.2 Implementation Path

| Step | Task | File/Location |
|------|------|---------------|
| 1.1.1 | Install Lark parser | `pyproject.toml` |
| 1.1.2 | Define grammar | `backend/app/rule_engine/grammar.lark` |
| 1.1.3 | Create AST node classes | `backend/app/rule_engine/ast_nodes.py` |
| 1.1.4 | Implement Lark Transformer | `backend/app/rule_engine/parser.py` |
| 1.1.5 | Add error handling & validation | `backend/app/rule_engine/parser.py` |

### 1.3 Deliverables

```
backend/app/rule_engine/
├── __init__.py
├── grammar.lark          # Lark grammar file
├── ast_nodes.py          # Dataclasses for AST nodes
└── parser.py             # Parser class with parse() method
```

**API**:
```python
from app.rule_engine import RuleParser

parser = RuleParser()
ast = parser.parse(dsl_text)
# Returns: list[ActionDef | RuleDef]
```

### 1.4 Testing

| Test Type | Method | Location |
|-----------|--------|----------|
| Unit | Parse valid ACTION/RULE definitions | `tests/rule_engine/test_parser.py` |
| Unit | Verify AST structure correctness | `tests/rule_engine/test_parser.py` |
| Unit | Parse error handling (invalid syntax) | `tests/rule_engine/test_parser.py` |
| Fixture | Use 4 sample rules from DSL spec | `tests/fixtures/sample_rules.dsl` |

**Acceptance Criteria**:
- [ ] Parse all 4 example rules from DSL spec without error
- [ ] Parse all 6 example actions from DSL spec without error
- [ ] Invalid syntax returns clear error message with line number

---

## Phase 2: Expression Evaluator

**Duration**: 3-4 days

### 2.1 Objectives
- Evaluate condition expressions (WHERE, PRECONDITION)
- Support all operators: `==`, `IN`, `EXISTS`, `CHANGED`, etc.

### 2.2 Implementation Path

| Step | Task | File/Location |
|------|------|---------------|
| 2.1.1 | Create evaluation context class | `backend/app/rule_engine/context.py` |
| 2.1.2 | Implement expression evaluator | `backend/app/rule_engine/evaluator.py` |
| 2.1.3 | Add built-in functions | `backend/app/rule_engine/functions.py` |
| 2.1.4 | Handle graph pattern expressions | `backend/app/rule_engine/evaluator.py` |

### 2.3 Deliverables

```
backend/app/rule_engine/
├── context.py            # EvaluationContext class
├── evaluator.py          # ExpressionEvaluator class
└── functions.py          # NOW(), CONCAT(), OLD(), etc.
```

**API**:
```python
from app.rule_engine import ExpressionEvaluator, EvaluationContext

ctx = EvaluationContext(
    entity={"id": "PO_001", "status": "Open", "amount": 1000},
    old_values={"status": "Draft"},
    session=neo4j_session
)
evaluator = ExpressionEvaluator(ctx)
result = evaluator.evaluate(ast_expression)  # Returns: bool | value
```

### 2.4 Testing

| Test Type | Method | Location |
|-----------|--------|----------|
| Unit | Evaluate simple comparisons | `tests/rule_engine/test_evaluator.py` |
| Unit | Evaluate IN, IS NULL, MATCHES | `tests/rule_engine/test_evaluator.py` |
| Unit | Evaluate CHANGED FROM...TO | `tests/rule_engine/test_evaluator.py` |
| Integration | Evaluate EXISTS with Neo4j mock | `tests/rule_engine/test_evaluator.py` |
| Unit | Test all built-in functions | `tests/rule_engine/test_functions.py` |

**Acceptance Criteria**:
- [ ] All operators from DSL spec work correctly
- [ ] CHANGED detection works with old_values context
- [ ] EXISTS pattern evaluation returns correct boolean

---

## Phase 3: Action Registry & Executor

**Duration**: 4-5 days

### 3.1 Objectives
- Store ACTION definitions in registry
- Execute actions with PRECONDITION checking
- Run EFFECT statements

### 3.2 Implementation Path

| Step | Task | File/Location |
|------|------|---------------|
| 3.1.1 | Create ActionRegistry class | `backend/app/rule_engine/action_registry.py` |
| 3.1.2 | Implement precondition checker | `backend/app/rule_engine/action_executor.py` |
| 3.1.3 | Implement effect executor | `backend/app/rule_engine/action_executor.py` |
| 3.1.4 | Add SET/CREATE/LINK/TRIGGER handlers | `backend/app/rule_engine/effect_handlers.py` |
| 3.1.5 | Integrate with Neo4j for mutations | `backend/app/rule_engine/graph_mutator.py` |

### 3.3 Deliverables

```
backend/app/rule_engine/
├── action_registry.py    # ActionRegistry class
├── action_executor.py    # ActionExecutor class
├── effect_handlers.py    # SET, CREATE, LINK, TRIGGER handlers
└── graph_mutator.py      # Neo4j write operations
```

**API**:
```python
from app.rule_engine import ActionRegistry, ActionExecutor

# Register actions
registry = ActionRegistry()
registry.load_from_file("rules/actions.dsl")

# Execute action
executor = ActionExecutor(registry, neo4j_session)
result = await executor.execute(
    entity_type="PurchaseOrder",
    action_name="submit",
    entity_id="PO_001",
    params={}
)
# Returns: ActionResult(success=True) or ActionResult(success=False, error="...")
```

### 3.4 Testing

| Test Type | Method | Location |
|-----------|--------|----------|
| Unit | Register and lookup actions | `tests/rule_engine/test_action_registry.py` |
| Unit | PRECONDITION pass/fail cases | `tests/rule_engine/test_action_executor.py` |
| Unit | Multiple PRECONDITIONs (all must pass) | `tests/rule_engine/test_action_executor.py` |
| Integration | EFFECT executes SET correctly | `tests/rule_engine/test_action_executor.py` |
| Integration | Nested TRIGGER in EFFECT | `tests/rule_engine/test_action_executor.py` |

**Acceptance Criteria**:
- [ ] `PurchaseOrder.submit` action works with all 3 preconditions
- [ ] Failed precondition returns correct ON_FAILURE message
- [ ] EFFECT statements modify graph correctly

---

## Phase 4: Rule Engine Core

**Duration**: 5-6 days

### 4.1 Objectives
- Match events to rule triggers
- Execute FOR scopes via Cypher
- Run SET and TRIGGER statements

### 4.2 Implementation Path

| Step | Task | File/Location |
|------|------|---------------|
| 4.1.1 | Create RuleRegistry class | `backend/app/rule_engine/rule_registry.py` |
| 4.1.2 | Implement trigger matching | `backend/app/rule_engine/rule_engine.py` |
| 4.1.3 | Implement FOR→Cypher translator | `backend/app/rule_engine/cypher_translator.py` |
| 4.1.4 | Implement rule executor | `backend/app/rule_engine/rule_engine.py` |
| 4.1.5 | Add cascade detection & loop prevention | `backend/app/rule_engine/rule_engine.py` |

### 4.3 Deliverables

```
backend/app/rule_engine/
├── rule_registry.py      # RuleRegistry with trigger index
├── rule_engine.py        # RuleEngine core class
└── cypher_translator.py  # FOR clause to Cypher query
```

**API**:
```python
from app.rule_engine import RuleEngine

engine = RuleEngine(action_registry, neo4j_session)
engine.load_rules_from_file("rules/business_rules.dsl")

# Manual trigger (for testing)
await engine.on_event(UpdateEvent(
    entity_type="Supplier",
    entity_id="BP_10001",
    property="status",
    old_value="Active",
    new_value="Suspended"
))
```

### 4.4 Testing

| Test Type | Method | Location |
|-----------|--------|----------|
| Unit | Trigger matching by event type | `tests/rule_engine/test_rule_engine.py` |
| Unit | Priority ordering | `tests/rule_engine/test_rule_engine.py` |
| Unit | FOR clause Cypher generation | `tests/rule_engine/test_cypher_translator.py` |
| Integration | SupplierStatusBlocking rule | `tests/rule_engine/test_rules_integration.py` |
| Integration | CreditLevelDowngrade rule | `tests/rule_engine/test_rules_integration.py` |
| Integration | Cascade rule execution | `tests/rule_engine/test_rules_integration.py` |

**Acceptance Criteria**:
- [ ] All 4 sample rules execute correctly
- [ ] Cypher queries are valid and performant
- [ ] Cascade rules trigger correctly (max depth=10)

---

## Phase 5: Event Integration

**Duration**: 3-4 days

### 5.1 Objectives
- Hook rule engine into existing graph operations
- Capture property changes automatically

### 5.2 Implementation Path

| Step | Task | File/Location |
|------|------|---------------|
| 5.1.1 | Create GraphEventEmitter | `backend/app/rule_engine/event_emitter.py` |
| 5.1.2 | Wrap existing GraphTools mutations | `backend/app/services/graph_tools.py` |
| 5.1.3 | Connect emitter to RuleEngine | `backend/app/rule_engine/__init__.py` |
| 5.1.4 | Add transaction support | `backend/app/rule_engine/rule_engine.py` |

### 5.3 Deliverables

```
backend/app/rule_engine/
└── event_emitter.py      # GraphEventEmitter class

# Modified files:
backend/app/services/graph_tools.py  # Add event emission
backend/app/core/dependencies.py     # Rule engine DI
```

**API**:
```python
# In graph_tools.py
class GraphTools:
    async def update_entity(self, entity_id: str, updates: dict):
        old = await self.get_entity(entity_id)
        await self._do_update(entity_id, updates)
        
        for key, new_val in updates.items():
            if old.get(key) != new_val:
                await self.event_emitter.emit(UpdateEvent(...))
```

### 5.4 Testing

| Test Type | Method | Location |
|-----------|--------|----------|
| Integration | Update triggers rule automatically | `tests/rule_engine/test_integration.py` |
| Integration | Create triggers ON CREATE rules | `tests/rule_engine/test_integration.py` |
| E2E | Full scenario: update supplier → PO locked | `tests/rule_engine/test_e2e.py` |

**Acceptance Criteria**:
- [ ] Updating Supplier.status via API triggers SupplierStatusBlocking rule
- [ ] All graph mutations automatically emit events
- [ ] Transaction rollback on rule execution failure

---

## Phase 6: API & Management

**Duration**: 3-4 days

### 6.1 Objectives
- REST API for action invocation
- API for rule/action management
- Admin UI components (optional)

### 6.2 Implementation Path

| Step | Task | File/Location |
|------|------|---------------|
| 6.1.1 | Create action invocation endpoint | `backend/app/api/actions.py` |
| 6.1.2 | Create rule management endpoints | `backend/app/api/rules.py` |
| 6.1.3 | Add rule file upload/storage | `backend/app/services/rule_storage.py` |
| 6.1.4 | (Optional) Frontend rule editor | `frontend/src/components/rule-editor.tsx` |

### 6.3 Deliverables

```
backend/app/api/
├── actions.py            # POST /actions/{type}/{action}
└── rules.py              # GET/POST/DELETE /rules

backend/app/services/
└── rule_storage.py       # Rule file persistence
```

**API Endpoints**:
```
POST /api/actions/{entity_type}/{action_name}
  Body: { "entity_id": "PO_001", "params": {...} }
  Response: { "success": true } or { "success": false, "error": "..." }

GET  /api/rules
POST /api/rules          # Upload DSL file
GET  /api/rules/{name}
DELETE /api/rules/{name}

GET  /api/actions        # List all registered actions
GET  /api/actions/{entity_type}
```

### 6.4 Testing

| Test Type | Method | Location |
|-----------|--------|----------|
| API | POST action with valid preconditions | `tests/api/test_actions.py` |
| API | POST action with failed preconditions | `tests/api/test_actions.py` |
| API | Rule CRUD operations | `tests/api/test_rules.py` |
| E2E | Full API flow | `tests/api/test_e2e.py` |

**Acceptance Criteria**:
- [ ] Action API returns clear success/failure messages
- [ ] Rules can be uploaded and activated at runtime
- [ ] API documentation generated (OpenAPI)

---

## File Structure Summary

```
backend/app/rule_engine/
├── __init__.py
├── grammar.lark
├── ast_nodes.py
├── parser.py
├── context.py
├── evaluator.py
├── functions.py
├── action_registry.py
├── action_executor.py
├── effect_handlers.py
├── graph_mutator.py
├── rule_registry.py
├── rule_engine.py
├── cypher_translator.py
└── event_emitter.py

backend/app/api/
├── actions.py
└── rules.py

backend/app/services/
└── rule_storage.py

docs/rule-engine/
├── dsl-specification.md
└── implementation-plan.md

tests/rule_engine/
├── test_parser.py
├── test_evaluator.py
├── test_functions.py
├── test_action_registry.py
├── test_action_executor.py
├── test_rule_engine.py
├── test_cypher_translator.py
├── test_integration.py
└── test_e2e.py

tests/fixtures/
├── sample_rules.dsl
└── sample_actions.dsl
```

---

## Milestone Checklist

| Phase | Milestone | Verification |
|-------|-----------|--------------|
| 1 | Parser complete | All sample DSL parses without error |
| 2 | Evaluator complete | All operator tests pass |
| 3 | Action system complete | `PurchaseOrder.submit` works end-to-end |
| 4 | Rule engine complete | All 4 sample rules trigger correctly |
| 5 | Integration complete | Graph updates auto-trigger rules |
| 6 | API complete | REST API fully functional |

---

## Dependencies to Add

```toml
# pyproject.toml
[project.dependencies]
lark = "^1.1"  # Parser generator
```

---

## Risk & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Cascade loops | High | Max cascade depth limit (10), visited set |
| Cypher injection | High | Parameterized queries only |
| Performance (large graphs) | Medium | Index FOR patterns, batch updates |
| Complex nested patterns | Medium | Limit pattern depth, clear error messages |
