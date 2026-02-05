// Supplier-related rules for the knowledge graph rule engine.
// This file contains reactive rules that respond to supplier state changes.

// ACTION: Submit a purchase order for approval
// Precondition: Order must be in Draft status with positive amount
// Effect: Changes status to Submitted and records submission time
ACTION PurchaseOrder.submit {
    PRECONDITION statusCheck: this.status == "Draft"
        ON_FAILURE: "Only draft orders can be submitted"
    PRECONDITION: this.amount > 0
        ON_FAILURE: "Amount must be positive"
    EFFECT {
        SET this.status = "Submitted";
        SET this.submittedAt = NOW();
    }
}

// ACTION: Approve a purchase order
// Precondition: Order must be submitted and within budget
// Effect: Changes status to Approved
ACTION PurchaseOrder.approve {
    PRECONDITION: this.status == "Submitted"
        ON_FAILURE: "Only submitted orders can be approved"
    PRECONDITION: this.amount <= this.budgetLimit
        ON_FAILURE: "Order exceeds budget limit"
    EFFECT {
        SET this.status = "Approved";
        SET this.approvedAt = NOW();
    }
}

// ACTION: Reject a purchase order
// Precondition: Order must be in Submitted status
// Effect: Changes status to Rejected
ACTION PurchaseOrder.reject {
    PRECONDITION: this.status IN ["Submitted", "Draft"]
        ON_FAILURE: "Cannot reject order in current status"
    EFFECT {
        SET this.status = "Rejected";
        SET this.rejectedAt = NOW();
    }
}

// ACTION: Cancel a purchase order
// Precondition: Order must be open and cancellable
// Effect: Changes status to Cancelled
ACTION PurchaseOrder.cancel {
    PRECONDITION: this.status == "Open"
        ON_FAILURE: "Cannot cancel non-open order"
    PRECONDITION: this.canCancel == true
        ON_FAILURE: "Order cannot be cancelled"
    EFFECT {
        SET this.status = "Cancelled";
        SET this.cancelledAt = NOW();
    }
}

// ACTION: Transfer payment for a purchase order
// Precondition: Order must be in Open/Approved status and not yet transferred
// Effect: Marks order as transferred and records transfer details
ACTION PurchaseOrder.transfer {
    PRECONDITION: this.status IN ["Open", "Approved"]
        ON_FAILURE: "Only open or approved orders can be transferred"
    PRECONDITION: this.isTransferred == false
        ON_FAILURE: "This order has already been transferred"
    EFFECT {
        SET this.isTransferred = true;
        SET this.transferred = true;
        SET this.lastTransfer = NOW();
        SET this.transferAmount = this.amount;
    }
}

// RULE: Supplier Status Blocking
// Triggered when a Supplier's status changes
// Effect: Locks all open purchase orders from expired/blacklisted/suspended suppliers
RULE SupplierStatusBlocking PRIORITY 100 {
    ON UPDATE(Supplier.status)
    FOR (s: Supplier WHERE s.status IN ["Expired", "Blacklisted", "Suspended"]) {
        FOR (po: PurchaseOrder WHERE po -[orderedFrom]-> s AND po.status == "Open") {
            SET po.status = "RiskLocked";
            SET po.riskReason = "Supplier status: " + s.status;
        }
    }
}

// RULE: Supplier Risk Update
// Triggered when a Supplier's risk score changes
// Effect: Updates risk level on related purchase orders
RULE SupplierRiskUpdate PRIORITY 90 {
    ON UPDATE(Supplier.riskScore)
    FOR (s: Supplier WHERE s.riskScore > 50) {
        FOR (po: PurchaseOrder WHERE po -[orderedFrom]-> s AND po.status IN ["Open", "Submitted"]) {
            SET po.riskLevel = "High";
        }
    }
}

// RULE: Purchase Order Amount Validation
// Triggered when a Purchase Order amount is updated
// Effect: Validates the amount and updates validation status
RULE PurchaseOrderAmountValidation PRIORITY 80 {
    ON UPDATE(PurchaseOrder.amount)
    FOR (po: PurchaseOrder WHERE po.amount > po.maxAmount) {
        SET po.validationStatus = "Failed";
        SET po.validationError = "Amount exceeds maximum allowed";
    }
}

// RULE: Auto-approve low-value orders
// Triggered when a low-value Purchase Order is submitted
// Effect: Automatically approves orders below a threshold
RULE AutoApproveLowValueOrders PRIORITY 70 {
    ON UPDATE(PurchaseOrder.status)
    FOR (po: PurchaseOrder WHERE po.status == "Submitted" AND po.amount < 1000) {
        SET po.status = "Approved";
        SET po.autoApproved = true;
        SET po.approvedAt = NOW();
    }
}
