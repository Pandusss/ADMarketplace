"""
Channel Schemas.
Pydantic models for Telegram channels, covering registration forms, 
analytics data structures, and ad slot availability.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


ChannelMemberRole = Literal["owner", "admin", "pr_manager"]


class ChannelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    # Keep backward compatible naming for existing clients:
    # expose `name` as the channel title.
    name: str = Field(validation_alias="title")
    handle: str
    description: str
    avatar_file_id: str | None = None

    subscribers_count: int
    avg_views: int
    
    # Analytics
    avg_views_24h: int = 0
    avg_views_7d: int = 0
    premium_share: float = 0.0
    growth_7d: float = 0.0
    
    # Advanced / Strict Analytics
    avg_views_per_post: int = 0
    median_views: int = 0
    engagement_rate: float = 0.0
    median_er: float = 0.0
    posts_per_day: float = 0.0
    ad_reach_estimate: int = 0
    followers_trend_percent: float = 0.0
    stability_score: float = 0.0
    
    # --- New High-Fidelity Metrics ---
    subs_today: int = 0
    subs_week: int = 0
    subs_month: int = 0
    joins_24h: int = 0
    leaves_24h: int = 0
    
    reach_12h: int = 0
    reach_24h: int = 0
    reach_48h: int = 0
    err_24h_percent: float = 0.0
    
    posts_total: int = 0
    posts_yesterday: int = 0
    posts_week: int = 0
    posts_month: int = 0
    channel_created_at: datetime | None = None
    
    avg_forwards: float = 0.0
    avg_replies: float = 0.0
    avg_reactions: float = 0.0
    
    premium_subscribers_count: int = 0
    region_stats: dict[str, float] | None = None
    
    last_stats_update: datetime | None = None

    verified_stats: bool

    category: str
    language: str
    price_per_post_ton: float = Field(ge=0)
    price_top_hour_ton: float = Field(default=0.0, ge=0)
    top_price_step_pct: float = Field(default=0.0, ge=0)

    is_verified: bool = False
    is_published: bool = False
    owner_id: str | None = None
    rating_avg: float = 0.0
    rating_count: int = 0

    # Posting availability settings (optional for backward compatibility).
    posting_timezone: str = "UTC"
    posting_window_start: str = "10:00"
    posting_window_end: str = "20:00"
    posting_slot_minutes: int = 30


class ChannelMemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    channel_id: str
    role: ChannelMemberRole


class ChannelAvailabilityIn(BaseModel):
    """
    Channel owner's posting availability settings.

    Times are stored as strings in HH:MM format (24h) in the channel's timezone.
    """

    posting_timezone: str = Field(default="UTC", min_length=1)
    posting_window_start: str = Field(default="10:00", min_length=1)
    posting_window_end: str = Field(default="20:00", min_length=1)
    posting_slot_minutes: int = Field(default=30, ge=5, le=240)


class ChannelUpdateIn(BaseModel):
    category: str | None = None
    language: str | None = None
    price_per_post_ton: float | None = Field(default=None, ge=0)
    price_top_hour_ton: float | None = Field(default=None, ge=0)
    top_price_step_pct: float | None = Field(default=None, ge=0)
    description: str | None = None
    posting_window_start: str | None = None
    posting_window_end: str | None = None
    posting_slot_minutes: int | None = Field(default=None, ge=5, le=240)
