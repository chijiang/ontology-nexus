# backend/app/models/role.py
"""
Role and Permission Models

RBAC (Role-Based Access Control) implementation for multi-role user support.
Defines roles and their associated permissions for pages, actions, and entity types.
"""

from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class Role(Base):
    """Role table

    Defines user roles with basic structure.
    """

    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    role_type: Mapped[str] = mapped_column(
        String(20), default="system", nullable=False
    )  # "system" or "business"
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False
    )


class UserRole(Base):
    """User-Role association table

    Many-to-many relationship between users and roles.
    """

    __tablename__ = "user_roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role_id: Mapped[int] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"), nullable=False
    )
    assigned_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    __table_args__ = (UniqueConstraint("user_id", "role_id", name="uq_user_role"),)


class RolePagePermission(Base):
    """Page permission table

    Defines which pages/views a role can access.
    """

    __tablename__ = "role_page_permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    role_id: Mapped[int] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"), nullable=False
    )
    page_id: Mapped[str] = mapped_column(String(50), nullable=False)

    __table_args__ = (UniqueConstraint("role_id", "page_id", name="uq_role_page"),)


class RoleActionPermission(Base):
    """Action permission table

    Defines which specific actions a role can perform.
    """

    __tablename__ = "role_action_permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    role_id: Mapped[int] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"), nullable=False
    )
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    action_name: Mapped[str] = mapped_column(String(100), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "role_id", "entity_type", "action_name", name="uq_role_action"
        ),
    )


class RoleEntityPermission(Base):
    """Entity type permission table

    Defines access permissions for different entity types in the knowledge graph.
    """

    __tablename__ = "role_entity_permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    role_id: Mapped[int] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"), nullable=False
    )
    entity_class_name: Mapped[str] = mapped_column(String(100), nullable=False)

    __table_args__ = (
        UniqueConstraint("role_id", "entity_class_name", name="uq_role_entity"),
    )
