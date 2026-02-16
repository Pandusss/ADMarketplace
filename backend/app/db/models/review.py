from __future__ import annotations
from datetime import datetime
from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.models.base import Base


class Review(Base):
    __tablename__ = "reviews"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    deal_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    reviewer_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    target_user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    target_channel_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    target_campaign_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
