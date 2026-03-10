"""Supplier Model

Represents a vendor/supplier in the ERP system.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class Supplier(Base):
    """Supplier entity representing vendors in the system"""

    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, autoincrement="auto")
    name = Column(String(255), nullable=False, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    contact_person = Column(String(255))
    email = Column(String(255))
    phone = Column(String(50))
    address = Column(Text)
    credit_rating = Column(String(20), default="B")  # A, B, C, D
    status = Column(String(20), default="active", index=True)  # active, inactive
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    purchase_orders = relationship(
        "PurchaseOrder",
        back_populates="supplier",
        cascade="all, delete-orphan",
    )
    contracts = relationship(
        "Contract",
        back_populates="supplier",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_suppliers_code", "code"),
        Index("idx_suppliers_status", "status"),
    )
