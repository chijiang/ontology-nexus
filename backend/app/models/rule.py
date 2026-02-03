# backend/app/models/rule.py
from datetime import datetime
from sqlalchemy import Boolean, String, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class ActionDefinition(Base):
    """Represents an action that can be executed by the rule engine."""
    __tablename__ = "action_definitions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)  # e.g., "PurchaseOrder.submit"
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "PurchaseOrder"
    dsl_content: Mapped[str] = mapped_column(Text, nullable=False)  # Full ACTION DSL
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    def __init__(self, **kwargs):
        if 'is_active' not in kwargs:
            kwargs['is_active'] = True
        super().__init__(**kwargs)


class Rule(Base):
    """Represents a business rule that triggers on specific entity changes."""
    __tablename__ = "rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)  # e.g., "SupplierStatusBlocking"
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    trigger_type: Mapped[str] = mapped_column(String(20), nullable=False)  # UPDATE/CREATE/DELETE
    trigger_entity: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "Supplier"
    trigger_property: Mapped[str | None] = mapped_column(String(100), nullable=True)  # e.g., "status"
    dsl_content: Mapped[str] = mapped_column(Text, nullable=False)  # Full RULE DSL
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    def __init__(self, **kwargs):
        if 'is_active' not in kwargs:
            kwargs['is_active'] = True
        if 'priority' not in kwargs:
            kwargs['priority'] = 0
        super().__init__(**kwargs)
