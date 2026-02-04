# KG Rule DSL Specification v2

A domain-specific language for expressing business rules and actions over knowledge graphs.

---

## Overview

The DSL consists of two core constructs:

| Construct | Purpose | Location |
|-----------|---------|----------|
| **ACTION** | Define operations on entity types with preconditions | Bound to entity classes |
| **RULE** | React to state changes, update properties, trigger actions | Global rule set |

### Design Principles
1. **Rules** only do two things: `SET` properties and `TRIGGER` actions
2. **Actions** define what operations are possible and under what conditions
3. **Preconditions** on Actions automatically block invalid operations
4. **Separation of concerns** - rules don't need to know blocking logic

---

## Part 1: ACTION Definition

Actions are methods bound to entity types that can be invoked by rules or external systems.

### 1.1 Syntax

```
ACTION <EntityType>.<actionName>(<parameters>?) {
    PRECONDITION [name]: <condition>
        ON_FAILURE: <error_message>
    [PRECONDITION ...]
    
    EFFECT {
        <statements>
    }?
}
```

### 1.2 Components

| Component | Required | Description |
|-----------|----------|-------------|
| `EntityType.actionName` | ✅ | Action identifier, bound to a class |
| `parameters` | ❌ | Optional input parameters |
| `PRECONDITION` | ✅ | Conditions that must be true to execute |
| `ON_FAILURE` | ✅ | Error message when precondition fails |
| `EFFECT` | ❌ | Side effects when action executes |

### 1.3 Precondition Syntax

```javascript
// Simple property check
PRECONDITION: this.status == "Open"

// Named precondition (for better error messages)
PRECONDITION statusCheck: this.status == "Open"
    ON_FAILURE: "Order must be in Open status"

// Graph pattern check
PRECONDITION supplierValid: 
    NOT EXISTS(this -[orderedFrom]-> s:Supplier WHERE s.status IN ["Suspended", "Blacklisted"])
    ON_FAILURE: "Cannot proceed: supplier is blocked"

// Multiple preconditions (ALL must pass)
PRECONDITION statusCheck: this.status == "Draft"
PRECONDITION amountCheck: this.amount > 0
PRECONDITION dateCheck: this.dueDate > NOW()
```

### 1.4 Effect Syntax

```javascript
EFFECT {
    // Property updates
    SET this.status = "Completed";
    SET this.completedAt = NOW();
    
    // Trigger other actions
    TRIGGER Notification.send ON this WITH { 
        template: "order_completed" 
    };
    
    // Create entities/relationships
    CREATE (log: AuditLog { 
        action: "completed", 
        target: this.id, 
        timestamp: NOW() 
    });
    LINK this -[hasLog]-> log;
}
```

### 1.5 Parameters

```javascript
ACTION PurchaseOrder.approve(approver: User, comment: String?) {
    PRECONDITION levelCheck: approver.level >= this.requiredApprovalLevel
        ON_FAILURE: "Approver level insufficient"
    
    EFFECT {
        SET this.status = "Approved";
        SET this.approvedBy = approver.id;
        SET this.approvalComment = comment;
    }
}
```

### 1.6 Complete Examples

```javascript
// ===== 采购订单动作 =====

ACTION PurchaseOrder.submit {
    PRECONDITION statusCheck: this.status == "Draft"
        ON_FAILURE: "Only draft orders can be submitted"
    
    PRECONDITION materialCheck: 
        NOT EXISTS(this -[containsItem]-> item -[forMaterial]-> m:Material 
                   WHERE m.status IN ["Frozen", "Deactivated"])
        ON_FAILURE: "Order contains frozen or deactivated materials"
    
    PRECONDITION supplierCheck:
        NOT EXISTS(this -[orderedFrom]-> s:Supplier 
                   WHERE s.status IN ["Suspended", "Blacklisted", "Expired"])
        ON_FAILURE: "Cannot submit: supplier is blocked"
    
    EFFECT {
        SET this.status = "Submitted";
        SET this.submittedAt = NOW();
    }
}

ACTION PurchaseOrder.transfer {
    PRECONDITION: this.status == "Open"
        ON_FAILURE: "Cannot transfer: order is not open"
    
    // No EFFECT - transfer logic handled externally
}

ACTION PurchaseOrder.cancel {
    PRECONDITION: this.status IN ["Draft", "Open", "Submitted"]
        ON_FAILURE: "Cannot cancel: order is in final state"
    
    EFFECT {
        SET this.status = "Cancelled";
        SET this.cancelledAt = NOW();
    }
}

// ===== 付款动作 =====

ACTION Payment.revalidate {
    PRECONDITION: this.status == "Pending"
        ON_FAILURE: "Only pending payments can be revalidated"
    
    EFFECT {
        SET this.requiresRevalidation = true;
        SET this.revalidationRequestedAt = NOW();
        TRIGGER Workflow.start ON this WITH { 
            workflowType: "PaymentRevalidation" 
        };
    }
}

ACTION Payment.execute {
    PRECONDITION statusCheck: this.status == "Approved"
        ON_FAILURE: "Payment must be approved before execution"
    
    PRECONDITION bankCheck:
        EXISTS(this -[paidTo]-> org WHERE org.mainBankAccount IS NOT NULL)
        ON_FAILURE: "Target organization has no bank account configured"
    
    EFFECT {
        SET this.status = "Executed";
        SET this.executedAt = NOW();
    }
}

// ===== 采购申请动作 =====

ACTION PurchaseRequisition.submit {
    PRECONDITION statusCheck: this.status == "Draft"
        ON_FAILURE: "Only draft requisitions can be submitted"
    
    PRECONDITION materialCheck:
        NOT EXISTS(this -[forMaterial]-> m:Material 
                   WHERE m.status IN ["Frozen", "Deactivated"])
        ON_FAILURE: "Cannot submit PR for frozen/deactivated material"
    
    EFFECT {
        SET this.status = "Submitted";
    }
}
```

---

## Part 2: RULE Definition

Rules react to state changes and execute `SET` or `TRIGGER` operations.

### 2.1 Syntax

```
RULE <rule_name> [PRIORITY <number>] {
    <trigger_clause>
    <scope_clause>
}
```

### 2.2 Triggers

| Trigger | Syntax | Description |
|---------|--------|-------------|
| Property Update | `ON UPDATE(Type.property)` | Fires when property changes |
| Entity Create | `ON CREATE(Type)` | Fires when entity created |
| Entity Delete | `ON DELETE(Type)` | Fires when entity deleted |
| Relationship | `ON LINK(Type, Rel, Type)` | Fires when relationship created |
| Batch Scan | `ON SCAN` | Fires on scheduled scan |

### 2.3 Change Detection

```javascript
// Detect any change
ON UPDATE(Supplier.creditLevel)
FOR (s: Supplier WHERE s.creditLevel CHANGED) { ... }

// Detect specific transition
ON UPDATE(Supplier.creditLevel)
FOR (s: Supplier WHERE s.creditLevel CHANGED FROM "A" TO ["B", "C"]) { ... }

// Access old value
FOR (s: Supplier WHERE s.creditLevel CHANGED) {
    SET s.previousCreditLevel = OLD(s.creditLevel);
}
```

### 2.4 Scope Clause (FOR)

```javascript
// Basic
FOR (variable: EntityType WHERE condition) { ... }

// Graph traversal
FOR (po: PurchaseOrder WHERE po -[orderedFrom]-> supplier) { ... }

// Nested scopes
FOR (s: Supplier WHERE s.status == "Suspended") {
    FOR (po: PurchaseOrder WHERE po -[orderedFrom]-> s) {
        ...
    }
}
```

### 2.5 Condition Operators

| Operator | Example |
|----------|---------|
| Equality | `x.status == "Open"` |
| Inequality | `x.amount != 0` |
| Comparison | `x.amount > 1000`, `x.date < NOW()` |
| Membership | `x.status IN ["A", "B", "C"]` |
| Null Check | `x.field IS NULL` / `IS NOT NULL` |
| Pattern | `x.name MATCHES "PO_2024_*"` |
| Existence | `EXISTS(x -[rel]-> y)` / `NOT EXISTS(...)` |
| Change | `x.field CHANGED` / `CHANGED FROM a TO b` |

### 2.6 Actions in Rules

Rules can only use two action types:

```javascript
// 1. SET - Update properties
SET entity.property = value;
SET entity.property = expression;  // e.g., entity.count + 1

// 2. TRIGGER - Invoke an ACTION
TRIGGER EntityType.actionName ON target;
TRIGGER EntityType.actionName ON target WITH { param1: value1 };
```

### 2.7 Complete Examples

```javascript
// ===== Rule 1: 供应商状态阻断 =====
RULE SupplierStatusBlocking PRIORITY 100 {
    ON UPDATE(Supplier.status)
    FOR (s: Supplier WHERE s.status IN ["Expired", "Blacklisted", "Suspended"]) {
        // Lock related POs
        FOR (po: PurchaseOrder WHERE po -[orderedFrom]-> s AND po.status == "Open") {
            SET po.status = "RiskLocked";
        }
        // Lock related PRs
        FOR (pr: PurchaseRequisition 
             WHERE EXISTS(po: PurchaseOrder 
                         WHERE po -[createdFrom]-> pr AND po -[orderedFrom]-> s)
             AND pr.status == "Open") {
            SET pr.status = "RiskLocked";
        }
    }
}

// ===== Rule 2: 信用等级联动 =====
RULE CreditLevelDowngrade PRIORITY 90 {
    ON UPDATE(Supplier.creditLevel)
    FOR (s: Supplier WHERE s.creditLevel CHANGED FROM "A" TO ["B", "C"]) {
        // Upgrade approval level for recent POs
        FOR (po: PurchaseOrder 
             WHERE po -[orderedFrom]-> s 
             AND po.createdAt > NOW() - DAYS(1)
             AND po.approvalLevel IN ["L1", "L2"]) {
            SET po.approvalLevel = "L4";
        }
    }
}

// ===== Rule 3: 物料状态阻断 =====
RULE MaterialStatusBlocking PRIORITY 110 {
    ON UPDATE(Material.status)
    FOR (m: Material WHERE m.status IN ["Frozen", "Deactivated"]) {
        // Return unapproved PRs
        FOR (pr: PurchaseRequisition 
             WHERE pr -[forMaterial]-> m 
             AND pr.status IN ["Open", "Submitted"]) {
            SET pr.status = "Returned";
            SET pr.returnReason = CONCAT("Material status changed to ", m.status);
        }
    }
}

// ===== Rule 4: 组织银行账户变更 =====
RULE OrgBankAccountAudit PRIORITY 80 {
    ON UPDATE(LegalEntity.mainBankAccount)
    FOR (org: LegalEntity WHERE org.mainBankAccount CHANGED) {
        FOR (pmt: Payment 
             WHERE pmt -[paidTo]-> org 
             AND pmt.status == "Pending") {
            // Trigger revalidation action
            TRIGGER Payment.revalidate ON pmt;
        }
    }
}

RULE OrgUnitBankAccountAudit PRIORITY 80 {
    ON UPDATE(OrgUnit.mainBankAccount)
    FOR (ou: OrgUnit WHERE ou.mainBankAccount CHANGED) {
        FOR (pmt: Payment 
             WHERE pmt -[paidTo]-> ou 
             AND pmt.status == "Pending") {
            TRIGGER Payment.revalidate ON pmt;
        }
    }
}
```

---

## Part 3: Built-in Functions

| Category | Functions |
|----------|-----------|
| **Time** | `NOW()`, `DATE(string)`, `DAYS(n)`, `HOURS(n)` |
| **Math** | `ABS(n)`, `ROUND(n)`, `MIN(a,b)`, `MAX(a,b)` |
| **String** | `CONCAT(a, b, ...)`, `UPPER(s)`, `LOWER(s)`, `LENGTH(s)` |
| **Aggregate** | `COUNT(pattern)`, `SUM(expr)`, `AVG(expr)` |
| **Change** | `OLD(property)` - previous value before update |
| **Lookup** | `LOOKUP(Type, field, value)` |

---

## Part 4: Implementation Guide

### 4.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     DSL Parser                               │
│  ┌─────────────┐    ┌─────────────┐                         │
│  │ ACTION Defs │    │  RULE Defs  │                         │
│  └──────┬──────┘    └──────┬──────┘                         │
└─────────┼──────────────────┼────────────────────────────────┘
          │                  │
          ▼                  ▼
┌─────────────────┐  ┌─────────────────┐
│ Action Registry │  │  Rule Engine    │
│  (Dict/Map)     │  │   (Event Loop)  │
└────────┬────────┘  └────────┬────────┘
         │                    │
         │    ┌───────────────┘
         │    │
         ▼    ▼
┌─────────────────────────────────────────────────────────────┐
│                   Execution Engine                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ Condition   │  │   Cypher    │  │   Effect    │         │
│  │ Evaluator   │  │ Translator  │  │  Executor   │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │   Neo4j     │
                    └─────────────┘
```

### 4.2 Component Responsibilities

| Component | Responsibility |
|-----------|----------------|
| **DSL Parser** | Parse ACTION and RULE definitions into AST |
| **Action Registry** | Store ACTION definitions, lookup by `Type.action` |
| **Rule Engine** | Subscribe to graph events, match triggers, execute rules |
| **Condition Evaluator** | Evaluate PRECONDITION and WHERE expressions |
| **Cypher Translator** | Convert FOR clauses to Cypher queries |
| **Effect Executor** | Execute SET, CREATE, LINK, TRIGGER statements |

### 4.3 Execution Flow

#### Action Invocation
```
External Request: "Execute PurchaseOrder.submit on PO_001"
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               │
            1. Lookup ACTION definition             │
                    │                               │
                    ▼                               │
            2. Load entity PO_001 from graph        │
                    │                               │
                    ▼                               │
            3. Evaluate each PRECONDITION           │
                    │                               │
        ┌───────────┴───────────┐                   │
        │                       │                   │
    [PASS]                  [FAIL]                  │
        │                       │                   │
        ▼                       ▼                   │
4. Execute EFFECT       Return ON_FAILURE message  │
        │                                           │
        ▼                                           │
5. Commit graph changes                             │
        │                                           │
        ▼                                           │
6. Emit property change events ─────────────────────┘
        │                          (triggers rules)
        ▼
    Return success
```

#### Rule Execution
```
Graph Event: "Supplier.status updated on BP_10001"
                    │
                    ▼
    1. Match rules by trigger: ON UPDATE(Supplier.status)
                    │
                    ▼
    2. Sort matched rules by PRIORITY (desc)
                    │
                    ▼
    3. For each rule:
        ├── Translate FOR clause to Cypher
        ├── Execute query to get matching entities
        └── For each entity:
            ├── Execute SET statements
            └── Execute TRIGGER statements
                    │
                    ▼
    4. Commit all changes
                    │
                    ▼
    5. Cascade: check if changes trigger more rules
```

### 4.4 Cypher Translation Examples

```javascript
// DSL FOR clause
FOR (po: PurchaseOrder WHERE po -[orderedFrom]-> s AND po.status == "Open")

// Cypher (s is bound from outer scope)
MATCH (po:PurchaseOrder)-[:orderedFrom]->(s:Supplier {id: $supplierId})
WHERE po.status = "Open"
RETURN po
```

```javascript
// DSL FOR with EXISTS
FOR (pr: PurchaseRequisition 
     WHERE EXISTS(po: PurchaseOrder WHERE po -[createdFrom]-> pr AND po -[orderedFrom]-> s))

// Cypher
MATCH (pr:PurchaseRequisition)
WHERE EXISTS {
    MATCH (po:PurchaseOrder)-[:createdFrom]->(pr)
    MATCH (po)-[:orderedFrom]->(s:Supplier {id: $supplierId})
}
RETURN pr
```

### 4.5 Data Structures

```python
# Python pseudo-code for runtime data structures

@dataclass
class Precondition:
    name: str | None
    condition: Expression  # AST node
    on_failure: str

@dataclass
class ActionDef:
    entity_type: str
    action_name: str
    parameters: list[Parameter]
    preconditions: list[Precondition]
    effect: EffectBlock | None

@dataclass
class RuleDef:
    name: str
    priority: int
    trigger: Trigger
    body: ForClause

@dataclass
class ForClause:
    variable: str
    entity_type: str
    condition: Expression | None
    statements: list[Statement]  # SET, TRIGGER, or nested FOR

class ActionRegistry:
    def __init__(self):
        self._actions: dict[str, ActionDef] = {}
    
    def register(self, action: ActionDef):
        key = f"{action.entity_type}.{action.action_name}"
        self._actions[key] = action
    
    def lookup(self, entity_type: str, action_name: str) -> ActionDef | None:
        return self._actions.get(f"{entity_type}.{action_name}")

class RuleEngine:
    def __init__(self):
        self._rules: list[RuleDef] = []
        self._trigger_index: dict[str, list[RuleDef]] = {}
    
    def register(self, rule: RuleDef):
        self._rules.append(rule)
        trigger_key = self._get_trigger_key(rule.trigger)
        self._trigger_index.setdefault(trigger_key, []).append(rule)
        self._trigger_index[trigger_key].sort(key=lambda r: -r.priority)
    
    def on_event(self, event: GraphEvent):
        trigger_key = self._event_to_trigger_key(event)
        for rule in self._trigger_index.get(trigger_key, []):
            self._execute_rule(rule, event)
```

### 4.6 Parser Recommendation

Use **Lark** (Python) for parsing:

```python
# grammar.lark
start: (action_def | rule_def)*

action_def: "ACTION" entity_action "{" precondition+ effect? "}"
entity_action: NAME "." NAME ("(" param_list? ")")?
precondition: "PRECONDITION" NAME? ":" expr "ON_FAILURE" ":" STRING
effect: "EFFECT" "{" statement* "}"

rule_def: "RULE" NAME priority? "{" trigger for_clause "}"
priority: "PRIORITY" NUMBER
trigger: "ON" trigger_type "(" trigger_target ")"
trigger_type: "UPDATE" | "CREATE" | "DELETE" | "LINK" | "SCAN"
trigger_target: NAME ("." NAME)?

for_clause: "FOR" "(" binding ")" "{" statement* "}"
binding: NAME ":" NAME ("WHERE" expr)?

statement: set_stmt | trigger_stmt | for_clause
set_stmt: "SET" path "=" expr ";"
trigger_stmt: "TRIGGER" entity_action "ON" NAME ("WITH" object)? ";"

// ... expressions, paths, etc.
```

### 4.7 Change Detection Strategy

| Approach | Description | Recommended For |
|----------|-------------|-----------------|
| **Application Hooks** | Wrap Neo4j writes in your app | Full control, most common |
| **APOC Triggers** | Neo4j stored procedures | Real-time, simple setup |
| **Kafka Connector** | Stream changes to message queue | High scale, decoupled |
| **Polling** | Periodic snapshot comparison | Simple, but has latency |

**Recommended: Application Hooks**
```python
class GraphService:
    async def update_entity(self, entity_id: str, updates: dict):
        old_values = await self.get_entity(entity_id)
        await self.neo4j.run("MATCH (n {id: $id}) SET n += $updates", ...)
        
        for key, new_value in updates.items():
            if old_values.get(key) != new_value:
                await self.rule_engine.on_event(UpdateEvent(
                    entity_type=old_values["__type__"],
                    entity_id=entity_id,
                    property=key,
                    old_value=old_values.get(key),
                    new_value=new_value
                ))
```

---

## Part 5: Grammar (EBNF)

```ebnf
(* Top-level *)
program         = { action_def | rule_def } ;

(* ACTION Definition *)
action_def      = "ACTION" entity_action "{" { precondition } [ effect ] "}" ;
entity_action   = type_name "." action_name [ "(" [ param_list ] ")" ] ;
param_list      = param { "," param } ;
param           = identifier ":" type_name [ "?" ] ;

precondition    = "PRECONDITION" [ identifier ] ":" expression 
                  "ON_FAILURE" ":" string_literal ;

effect          = "EFFECT" "{" { statement } "}" ;

(* RULE Definition *)
rule_def        = "RULE" identifier [ priority ] "{" trigger for_clause "}" ;
priority        = "PRIORITY" integer ;

trigger         = "ON" trigger_type "(" trigger_target ")" ;
trigger_type    = "UPDATE" | "CREATE" | "DELETE" | "LINK" | "SCAN" ;
trigger_target  = type_name [ "." property_name ] ;

(* Scope and Statements *)
for_clause      = "FOR" "(" binding ")" "{" { statement } "}" ;
binding         = identifier ":" type_name [ "WHERE" expression ] ;

statement       = set_stmt | trigger_stmt | create_stmt | link_stmt | for_clause ;
set_stmt        = "SET" path "=" expression ";" ;
trigger_stmt    = "TRIGGER" entity_action "ON" identifier [ "WITH" object ] ";" ;
create_stmt     = "CREATE" "(" binding object ")" ";" ;
link_stmt       = "LINK" identifier "-[" rel_name "]->" identifier ";" ;

(* Expressions *)
expression      = or_expr ;
or_expr         = and_expr { "OR" and_expr } ;
and_expr        = not_expr { "AND" not_expr } ;
not_expr        = [ "NOT" ] comparison ;
comparison      = term [ comp_op term ] 
                | term "IN" "[" value_list "]"
                | term "IS" [ "NOT" ] "NULL"
                | term "MATCHES" string_literal
                | term "CHANGED" [ "FROM" value "TO" value ]
                | "EXISTS" "(" pattern ")" ;
comp_op         = "==" | "!=" | "<" | ">" | "<=" | ">=" ;

term            = path | value | function_call | "(" expression ")" ;
path            = identifier { "." property_name } ;
value           = string_literal | number | boolean | "NULL" ;
value_list      = value { "," value } ;

(* Pattern Matching *)
pattern         = identifier { relationship identifier } [ "WHERE" expression ] ;
relationship    = "-[" rel_name? "]->" | "<-[" rel_name? "]-" | "-[" rel_name? "]-" ;

(* Functions *)
function_call   = function_name "(" [ arg_list ] ")" ;
function_name   = "NOW" | "DATE" | "DAYS" | "CONCAT" | "OLD" | "COUNT" | ... ;
arg_list        = expression { "," expression } ;

(* Objects *)
object          = "{" [ member { "," member } ] "}" ;
member          = identifier ":" expression ;

(* Terminals *)
identifier      = letter { letter | digit | "_" } ;
type_name       = identifier ;
property_name   = identifier ;
action_name     = identifier ;
rel_name        = identifier ;
string_literal  = '"' { character } '"' ;
integer         = digit { digit } ;
number          = integer [ "." digit { digit } ] ;
boolean         = "true" | "false" ;
```

---

## Appendix: Quick Reference Card

```
╔═══════════════════════════════════════════════════════════════╗
║                    KG RULE DSL QUICK REFERENCE                 ║
╠═══════════════════════════════════════════════════════════════╣
║ ACTION <Type>.<name> {                                         ║
║     PRECONDITION [id]: <condition>                             ║
║         ON_FAILURE: "message"                                  ║
║     EFFECT { SET ...; TRIGGER ...; CREATE ...; LINK ...; }    ║
║ }                                                              ║
╠═══════════════════════════════════════════════════════════════╣
║ RULE <name> PRIORITY <n> {                                     ║
║     ON UPDATE|CREATE|DELETE(<Type.prop>)                       ║
║     FOR (var: Type WHERE condition) {                          ║
║         SET var.prop = value;                                  ║
║         TRIGGER Type.action ON var;                            ║
║     }                                                          ║
║ }                                                              ║
╠═══════════════════════════════════════════════════════════════╣
║ OPERATORS:  == != < > <= >=  IN [...]  IS NULL  MATCHES "..."  ║
║             AND OR NOT  EXISTS(pattern)  CHANGED FROM x TO y   ║
╠═══════════════════════════════════════════════════════════════╣
║ PATTERNS:   a -[rel]-> b    a <-[rel]- b    a -[*1..3]-> b    ║
╠═══════════════════════════════════════════════════════════════╣
║ FUNCTIONS:  NOW() DATE() DAYS(n) OLD(prop) CONCAT() COUNT()   ║
╚═══════════════════════════════════════════════════════════════╝
```
