"""Payment Model

Represents payment records for purchase orders.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class Payment(Base):
    """Payment record for purchase orders"""

    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, autoincrement="auto")
    order_id = Column(
        Integer,
        ForeignKey("purchase_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    payment_date = Column(DateTime, server_default=func.now(), index=True)
    amount = Column(Float, nullable=False)
    payment_method = Column(
        String(50), default="bank_transfer"
    )  # bank_transfer, check, credit_card, cash
    status = Column(
        String(30), default="pending", index=True
    )  # pending, processing, completed, failed, cancelled
    reference = Column(String(100))  # Check number, transaction ID, etc.
    notes = Column(String(500))
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    order = relationship("PurchaseOrder", back_populates="payments")

    __table_args__ = (
        Index("idx_payments_order", "order_id"),
        Index("idx_payments_status", "status"),
        Index("idx_payments_date", "payment_date"),
    )
