"""
Channel Database Model.
ORM definition for Telegram channels, storing statistics, 
verification status, and ad slot availability.
"""
from __future__ import annotations
from datetime import datetime
from typing import Literal
from sqlalchemy import Boolean, DateTime, Float, Integer, String, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.models.base import Base

class Channel(Base):
    __tablename__ = "channels"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    owner_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    avatar_file_id: Mapped[str | None] = mapped_column(String, nullable=True)
    owner: Mapped["User"] = relationship("User", foreign_keys=[owner_id], primaryjoin="Channel.owner_id == User.id")
    telegram_channel_id: Mapped[str | None] = mapped_column(String, nullable=True, unique=True, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False, default="")
    handle: Mapped[str] = mapped_column(String, nullable=False, default="")
    description: Mapped[str] = mapped_column(String, nullable=False, default="")
    subscribers_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_views: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_views_per_post: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_views_24h: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_views_7d: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    premium_share: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    followers_trend_percent: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    growth_7d: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    last_stats_update: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    engagement_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    median_er: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    posts_per_day: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    ad_reach_estimate: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    median_views: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stability_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    last_scanned_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    premium_subscribers_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    region_stats: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    subs_today: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    subs_week: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    subs_month: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    joins_24h: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    leaves_24h: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reach_12h: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reach_24h: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reach_48h: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    err_24h_percent: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    posts_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    posts_yesterday: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    posts_week: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    posts_month: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    channel_created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    avg_forwards: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    avg_replies: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    avg_reactions: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    verified_stats: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    category: Mapped[str] = mapped_column(String, nullable=False, default="Crypto")
    language: Mapped[str] = mapped_column(String, nullable=False, default="EN")
    price_per_post_ton: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    price_top_hour_ton: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    top_price_step_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    wallet_address: Mapped[str] = mapped_column(String, nullable=False, default="")
    posting_timezone: Mapped[str] = mapped_column(String, nullable=False, default="UTC")
    posting_window_start: Mapped[str] = mapped_column(String, nullable=False, default="10:00")
    posting_window_end: Mapped[str] = mapped_column(String, nullable=False, default="20:00")
    posting_slot_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    rating_avg: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    rating_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

class ChannelMember(Base):
    __tablename__ = "channel_members"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    channel_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    role: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
