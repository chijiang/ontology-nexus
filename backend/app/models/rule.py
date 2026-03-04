# backend/app/models/rule.py
from datetime import datetime, timezone
from sqlalchemy import Boolean, String, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class ActionDefinition(Base):
    """Represents an action that can be executed by the rule engine."""

    __tablename__ = "action_definitions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(
        String(255), nullable=False
    )  # e.g., "PurchaseOrder.submit"
    entity_type: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # e.g., "PurchaseOrder"
    dsl_content: Mapped[str] = mapped_column(Text, nullable=False)  # Full ACTION DSL
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    def __init__(self, **kwargs):
        if "is_active" not in kwargs:
            kwargs["is_active"] = True
        super().__init__(**kwargs)


class Rule(Base):
    """Represents a business rule that triggers on specific entity changes."""

    __tablename__ = "rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False
    )  # e.g., "SupplierStatusBlocking"
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    trigger_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # UPDATE/CREATE/DELETE
    trigger_entity: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # e.g., "Supplier"
    trigger_property: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # e.g., "status"
    dsl_content: Mapped[str] = mapped_column(Text, nullable=False)  # Full RULE DSL
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    def __init__(self, **kwargs):
        if "is_active" not in kwargs:
            kwargs["is_active"] = True
        if "priority" not in kwargs:
            kwargs["priority"] = 0
        super().__init__(**kwargs)


class ExecutionLog(Base):
    """Logs of rule and action executions."""

    __tablename__ = "execution_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc), index=True)
    type: Mapped[str] = mapped_column(String(20), nullable=False)  # RULE / ACTION
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    entity_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    actor_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    actor_type: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # AI / USER / MCP / SYSTEM
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    detail: Mapped[dict | None] = mapped_column(
        Text, nullable=True
    )  # Store as JSON string

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
