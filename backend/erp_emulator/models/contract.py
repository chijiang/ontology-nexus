"""Contract Model

Represents procurement contracts between suppliers and materials.
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    Index,
    CheckConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from erp_emulator.database import Base


class Contract(Base):
    """Procurement contract linking suppliers to materials"""

    __tablename__ = "contracts"

    id = Column(Integer, primary_key=True, autoincrement="auto")
    contract_number = Column(String(50), unique=True, nullable=False, index=True)
    supplier_id = Column(
        Integer,
        ForeignKey("suppliers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    material_id = Column(
        Integer,
        ForeignKey("materials.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime)
    agreed_price = Column(Float, nullable=False)
    min_quantity = Column(Float, default=1)
    max_quantity = Column(Float)
    status = Column(
        String(30), default="active", index=True
    )  # active, expired, cancelled
    terms = Column(String(500))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    supplier = relationship("Supplier", back_populates="contracts")
    # Relationships
    supplier = relationship("Supplier", back_populates="contracts")
    material = relationship("Material", back_populates="contracts")
    purchase_orders = relationship("PurchaseOrder", back_populates="contract")

    __table_args__ = (
        Index("idx_contracts_supplier", "supplier_id"),
        Index("idx_contracts_material", "material_id"),
        Index("idx_contracts_status", "status"),
        CheckConstraint("max_quantity IS NULL OR max_quantity >= min_quantity"),
    )
