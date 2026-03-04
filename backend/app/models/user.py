# backend/app/models/user.py
from datetime import datetime, timezone
from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Multi-role support fields
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    approval_status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    approval_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    approved_by: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Foreign key to User.id
    approved_at: Mapped[datetime | None] = mapped_column(nullable=True)
    is_password_changed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __init__(self, **kwargs):
        if 'is_active' not in kwargs:
            kwargs['is_active'] = True
        if 'is_admin' not in kwargs:
            kwargs['is_admin'] = False
        if 'approval_status' not in kwargs:
            kwargs['approval_status'] = 'pending'
        if 'is_password_changed' not in kwargs:
            kwargs['is_password_changed'] = False
        super().__init__(**kwargs)
