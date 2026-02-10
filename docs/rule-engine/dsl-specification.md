# KG Rule DSL Specification

This document provides a comprehensive guide to the Domain Specific Language (DSL) used for defining **Actions** and **Rules** in the Knowledge Graph Rule Engine.

---

## 1. Overview

The DSL allows users to define business logic that interacts with the Knowledge Graph.
- **Actions** define "what can be done" to an entity, including safety checks (preconditions).
- **Rules** define "when to react" to changes in the graph and "what to trigger".

---

## 2. ACTION Definition

Actions are idempotent operations defined on an entity type. They consist of one or more **Preconditions** and an optional **Effect**.

### Syntax
```javascript
ACTION <EntityType>.<actionName> {
    PRECONDITION [name]: <expression>
        ON_FAILURE: <error_message>
    
    EFFECT {
        <statement>*
    }?
}
```

### Components
- **ENTITY TYPE**: The class of node this action applies to (e.g., `PurchaseOrder`).
- **PRECONDITION**: A logical expression that must evaluate to `true` for the action to proceed.
- **ON_FAILURE**: The message returned to the user/system if the precondition is not met.
- **EFFECT**: A block containing property updates (`SET`), cascading triggers (`TRIGGER`), or external service calls (`CALL`).

### Statements

- **SET**: Update a property of the current entity.
  ```javascript
  SET this.prop = value;
  ```
- **CALL**: Invoke an external gRPC method from a registered Data Product.
  ```javascript
  CALL ServiceName.MethodName({ field: expression, ... }) [INTO variable];
  ```
  - `ServiceName`: The `service_name` of a registered `DataProduct`.
  - `arguments`: A dictionary of fields and expressions to build the gRPC request.
  - `INTO variable`: (Optional) Capture the gRPC response into a temporary variable for use in subsequent statements.

### Typical Use Case: Submitting an Order with External Update
```javascript
ACTION PurchaseOrder.submit {
    // 1. Local property check
    PRECONDITION statusCheck: this.status == "Draft"
        ON_FAILURE: "Only draft orders can be submitted."

    // 2. Graph existence check (Checking if all related suppliers are active)
    PRECONDITION supplierCheck: NOT EXISTS(this -[orderedFrom]-> s:Supplier WHERE s.status != "Active")
        ON_FAILURE: "At least one supplier of this order is not active."

    EFFECT {
        // Call external ERP system via gRPC
        CALL ErpService.UpdateOrder({
            id: this.id,
            status: "Submitted"
        }) INTO erpResult;

        // Update local graph with ERP response if needed
        SET this.status = "Submitted";
        SET this.erp_ref = erpResult.external_id;
        SET this.submittedAt = NOW();
    }
}
```

---

## 3. RULE Definition

Rules are event-driven scripts that monitor graph updates and take automated actions.

### Syntax
```javascript
RULE <RuleName> [PRIORITY <number>] {
    ON <TriggerType>(<TriggerTarget>)
    FOR (<variable> : <EntityType> [WHERE <expression>]) {
        <statement>*
    }
}
```

### Triggers
- `ON UPDATE(Type.property)`: Fires when a specific property is changed.
- `ON CREATE(Type)`: Fires when a new node of a specific type is created.

### Scope and Context
- **FOR Clause**: Defines the set of entities the rule will act upon.
- **Relationship Match**: Within a `FOR` clause, you can match relationships between the current entity and a parent scope entity.

### Typical Use Case: Supplier Risk Blocking
```javascript
RULE SupplierStatusBlocking PRIORITY 100 {
    // Trigger when a Supplier's status changes
    ON UPDATE(Supplier.status)
    
    // Filter for Suppliers that have been blacklisted or suspended
    FOR (s: Supplier WHERE s.status IN ["Blacklisted", "Suspended", "Expired"]) {
        
        // Find all related PurchaseOrders that are currently Open
        FOR (po: PurchaseOrder WHERE po -[orderedFrom]-> s AND po.status == "Open") {
            
            // Lock the order due to supplier risk
            SET po.status = "RiskLocked";
            
            // Log the reason
            SET po.riskReason = CONCAT("Associated supplier ", s.name, " became ", s.status);
        }
    }
}
```

---

## 4. Expressions & Operators

### Comparison Operators
- `==`, `!=`, `<`, `>`, `<=`, `>=`: Standard comparison.
- `IN [value1, ...]`: List membership check.
- `IS [NOT] NULL`: Existence check for a value.

### Graph Operators
- **EXISTS(pattern)**: Checks if a graph pattern exists starting from the current context.
- **Patterns**: `this -[relName]-> var:Type` or `var:Type <-[relName]- parentVar`.

### Logical Operators
- `AND`, `OR`, `NOT`: Standard boolean logic.

---

## 5. Built-in Functions

- `NOW()`: Returns the current UTC timestamp (ISO format).
- `CONCAT(str1, str2, ...)`: Concatenates multiple strings.
- `OLD(property)`: (Rules only) Accesses the previous value of a property before the update.

---

## 6. Advanced Patterns

### Multi-hop Relationships in Actions
You can check deep relationships in preconditions:
```javascript
PRECONDITION checkSecurity: 
    EXISTS(this -[ownedBy]-> u:User -[hasRole]-> r:Role WHERE r.name == "Admin")
    ON_FAILURE: "Only admin-owned resources can be modified."
```

### Cascading Triggers in Rules
Rules can trigger actions defined elsewhere:
```javascript
RULE PaymentAutoExecution {
    ON UPDATE(Invoice.status)
    FOR (inv: Invoice WHERE inv.status == "Approved") {
        FOR (pmt: Payment WHERE pmt -[paysInvoice]-> inv) {
            TRIGGER Payment.execute ON pmt;
        }
    }
}
```
