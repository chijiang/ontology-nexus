"""Purchase Order Models

Represents purchase orders and their line items.
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Text,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from erp_emulator.database import Base


class PurchaseOrder(Base):
    """Purchase order header"""

    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True, autoincrement="auto")
    order_number = Column(String(50), unique=True, nullable=False, index=True)
    supplier_id = Column(
        Integer,
        ForeignKey("suppliers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status = Column(
        String(30),
        default="draft",
        index=True,
    )  # draft, pending, confirmed, partial, delivered, cancelled
    order_date = Column(DateTime, server_default=func.now(), index=True)
    delivery_date = Column(DateTime)
    total_amount = Column(Float, default=0.0)
    payment_terms = Column(String(100), default="NET 30")
    shipping_address = Column(Text)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_orders_supplier", "supplier_id"),
        Index("idx_orders_status", "status"),
        Index("idx_orders_date", "order_date"),
        Index("idx_orders_number", "order_number"),
        Index("idx_orders_contract", "contract_id"),
        Index("idx_orders_material", "material_id"),
    )

    contract_id = Column(
        Integer, ForeignKey("contracts.id", ondelete="SET NULL"), nullable=True
    )
    material_id = Column(
        Integer, ForeignKey("materials.id", ondelete="RESTRICT"), nullable=True
    )

    # Relationships
    supplier = relationship("Supplier", back_populates="purchase_orders")
    contract = relationship("Contract", back_populates="purchase_orders")
    material = relationship("Material", back_populates="purchase_orders")
    order_items = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
    )
    payments = relationship(
        "Payment",
        back_populates="order",
        cascade="all, delete-orphan",
    )


class OrderItem(Base):
    """Purchase order line item"""

    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, autoincrement="auto")
    order_id = Column(
        Integer,
        ForeignKey("purchase_orders.id", ondelete="CASCADE"),
        nullable=False,
    )
    material_id = Column(
        Integer, ForeignKey("materials.id", ondelete="RESTRICT"), nullable=False
    )
    quantity = Column(Float, nullable=False)
    unit_price = Column(Float, nullable=False)
    subtotal = Column(Float, nullable=False)
    discount_percent = Column(Float, default=0.0)
    delivery_status = Column(
        String(30), default="pending"
    )  # pending, partial, complete

    # Relationships
    order = relationship("PurchaseOrder", back_populates="order_items")
    material = relationship("Material", back_populates="order_items")

    __table_args__ = (
        Index("idx_order_items_order", "order_id"),
        Index("idx_order_items_material", "material_id"),
    )
