// Sample rule for testing: Supplier Status Blocking
RULE SupplierStatusBlocking PRIORITY 100 {
    ON UPDATE(Supplier.status)
    FOR (s: Supplier WHERE s.status IN ["Expired", "Blacklisted", "Suspended"]) {
        FOR (po: PurchaseOrder WHERE po -[orderedFrom]-> s AND po.status == "Open") {
            SET po.status = "RiskLocked";
        }
    }
}
