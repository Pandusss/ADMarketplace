from __future__ import annotations
from datetime import datetime
from sqlalchemy import DateTime, Float, Integer, String, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.db.models.base import Base

class ChannelSnapshot(Base):
    __tablename__ = "channel_snapshots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    subscribers: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_views_24h: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_views_7d: Mapped[int] = mapped_column(Integer, nullable=False)
    languages: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    premium_share: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    growth_7d: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    stability_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    premium_subscribers_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    region_stats: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
