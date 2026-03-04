# backend/app/models/conversation.py
from datetime import datetime, timezone
from sqlalchemy import String, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), default="新对话")
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.id",
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # 'user' or 'assistant'
    content: Mapped[str] = mapped_column(Text, nullable=False)
    extra_metadata: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )  # For graph_data, thinking, etc.
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

    conversation: Mapped["Conversation"] = relationship(
        "Conversation", back_populates="messages"
    )
