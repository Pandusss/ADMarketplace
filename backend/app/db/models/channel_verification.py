from __future__ import annotations
from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.models.base import Base

class ChannelVerification(Base):
    __tablename__ = "channel_verifications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    token: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    telegram_channel_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    channel_username: Mapped[str | None] = mapped_column(String, nullable=True)
    channel_title: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
