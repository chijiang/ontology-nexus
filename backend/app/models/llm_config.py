# backend/app/models/llm_config.py
from datetime import datetime, timezone
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class LLMConfig(Base):
    __tablename__ = "llm_configs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    api_key_encrypted: Mapped[str] = mapped_column(String(500), nullable=False)
    base_url: Mapped[str] = mapped_column(String(500), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
