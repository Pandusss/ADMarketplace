from __future__ import annotations
from datetime import datetime
from enum import Enum
from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.models.base import Base

class ChatInputMode(str, Enum):
    CHAT = "chat"
    CREATIVE_SUBMISSION = "creative_submission"

class UserChatContext(Base):
    __tablename__ = "user_chat_contexts"
    user_id: Mapped[str] = mapped_column(String, primary_key=True)
    deal_id: Mapped[str] = mapped_column(String, nullable=False)
    input_mode: Mapped[str] = mapped_column(String, nullable=False, default=ChatInputMode.CHAT.value)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
