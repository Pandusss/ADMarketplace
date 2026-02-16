from __future__ import annotations
from datetime import datetime
from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.models.base import Base

class ChannelOffer(Base):
    __tablename__ = "channel_offers"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    channel_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    advertiser_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    applicant_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    offer_price_ton: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    message: Mapped[str] = mapped_column(String, nullable=False, default="")
    campaign_brief: Mapped[str] = mapped_column(String, nullable=False, default="")
    campaign_title: Mapped[str] = mapped_column(String, nullable=False, default="")
    creative_mode: Mapped[str] = mapped_column(String, nullable=False, default="template")
    creative_instructions: Mapped[str | None] = mapped_column(String, nullable=True)
    template_id: Mapped[str | None] = mapped_column(String, nullable=True)
    preferred_publish_at: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    post_duration_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=24)
    deal_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
