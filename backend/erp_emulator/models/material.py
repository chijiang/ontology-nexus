"""Material Model

Represents a material/SKU in the ERP system.
"""

from sqlalchemy import Column, Integer, String, Float, Text, DateTime, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from erp_emulator.database import Base


class Material(Base):
    """Material entity representing products/SKUs in the system"""

    __tablename__ = "materials"

    id = Column(Integer, primary_key=True, autoincrement="auto")
    name = Column(String(255), nullable=False, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    category = Column(String(100), index=True)
    unit = Column(String(20), default="pcs")  # pcs, kg, m, l, etc.
    standard_price = Column(Float, default=0.0)
    lead_time_days = Column(Integer, default=7)
    min_order_quantity = Column(Integer, default=1)
    description = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    order_items = relationship(
        "OrderItem",
        back_populates="material",
    )
    contracts = relationship(
        "Contract",
        back_populates="material",
    )
    purchase_orders = relationship(
        "PurchaseOrder",
        back_populates="material",
    )

    __table_args__ = (
        Index("idx_materials_code", "code"),
        Index("idx_materials_category", "category"),
    )
