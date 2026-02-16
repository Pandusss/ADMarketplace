from __future__ import annotations
from datetime import datetime
from sqlalchemy import DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.db.models.base import Base

class TelegramUpdateState(Base):
    __tablename__ = "telegram_update_state"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    last_update_id: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
