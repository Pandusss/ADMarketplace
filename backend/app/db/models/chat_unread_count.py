from __future__ import annotations
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.models.base import Base

class ChatUnreadCount(Base):
    __tablename__ = "chat_unread_counts"
    user_id: Mapped[str] = mapped_column(String, primary_key=True)
    deal_id: Mapped[str] = mapped_column(String, primary_key=True)
    unread_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cross_chat_notified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_read_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
