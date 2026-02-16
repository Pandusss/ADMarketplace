from __future__ import annotations
from datetime import datetime
from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.models.base import Base

class CampaignStatus:
    open = "open"
    closed = "closed"

class Campaign(Base):
    __tablename__ = "campaigns"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    owner_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False, default="")
    brief: Mapped[str] = mapped_column(String, nullable=False, default="")
    category: Mapped[str] = mapped_column(String, nullable=False, default="")
    language: Mapped[str] = mapped_column(String, nullable=False, default="")
    budget_ton: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    desired_views_24h: Mapped[int | None] = mapped_column(Integer, nullable=True)
    template_id: Mapped[str] = mapped_column(String, nullable=False, default="")
    creative_mode: Mapped[str] = mapped_column(String, nullable=False, default="template")
    creative_instructions: Mapped[str | None] = mapped_column(String, nullable=True)
    post_duration_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=24)
    status: Mapped[str] = mapped_column(String, nullable=False, default=CampaignStatus.open)
    
    # Rating metrics
    rating_avg: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    rating_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
