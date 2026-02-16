from __future__ import annotations
from datetime import datetime
from sqlalchemy import DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.models.base import Base

class CampaignOfferStatus:
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"

class CampaignOffer(Base):
    __tablename__ = "campaign_offers"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    campaign_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    channel_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    applicant_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    offer_price_ton: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    message: Mapped[str] = mapped_column(String, nullable=False, default="")
    status: Mapped[str] = mapped_column(String, nullable=False, default=CampaignOfferStatus.pending)
    creative_mode: Mapped[str | None] = mapped_column(String, nullable=True)
    creative_instructions: Mapped[str | None] = mapped_column(String, nullable=True)
    deal_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
