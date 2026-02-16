"""
Deal Database Model.
SQLAlchemy ORM representation of an advertising deal, 
including relations to users, channels, and associated metadata.
"""
from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Literal
from random import choice
from sqlalchemy import Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.models.base import Base

_EMOJI_POOL = ["🍏", "🍎", "🍐", "🍊", "🍋", "🍌", "🍉", "🍇", "🍓", "🫐", "🍈", "🍒", "🍑", "🥭", "🍍", "🥥", "🥝", "🍅", "🍆", "🥑"]

def get_random_deal_emoji() -> str:
    return choice(_EMOJI_POOL)

class DealStatus(str, Enum):
    negotiation = "negotiation"
    pending_payment = "pending_payment"
    creative_draft = "creative_draft"
    creative_review = "creative_review"
    approved = "approved"
    scheduling = "scheduling"
    scheduled = "scheduled"
    awaiting_confirmation = "awaiting_confirmation"
    posted = "posted"
    released = "released"
    cancelled = "cancelled"
    refunded = "refunded"

class Deal(Base):
    __tablename__ = "deals"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    channel_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    advertiser_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    campaign_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    channel: Mapped["Channel"] = relationship("Channel", foreign_keys=[channel_id], primaryjoin="Deal.channel_id == Channel.id")
    emoji: Mapped[str] = mapped_column(String, nullable=False, default="")
    status: Mapped[str] = mapped_column(String, nullable=False, default=DealStatus.negotiation.value)
    ad_format: Mapped[str] = mapped_column(String, nullable=False, default="post")
    price_ton: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    negotiation_confirmed_by_advertiser: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    negotiation_confirmed_by_channel: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deal_confirmed_by_advertiser: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deal_confirmed_by_channel: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deal_confirmed_at: Mapped[str | None] = mapped_column(String, nullable=True)
    auto_release_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    post_duration_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    top_duration_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    campaign_brief: Mapped[str] = mapped_column(String, nullable=False, default="")
    campaign_title: Mapped[str] = mapped_column(String, nullable=False, default="")
    creative_mode: Mapped[str] = mapped_column(String, nullable=False, default="template")
    creative_instructions: Mapped[str | None] = mapped_column(String, nullable=True)
    preferred_publish_at: Mapped[str | None] = mapped_column(String, nullable=True)
    creative_text: Mapped[str] = mapped_column(String, nullable=False, default="")
    scheduled_at: Mapped[str | None] = mapped_column(String, nullable=True)
    creative_chat_id: Mapped[str | None] = mapped_column(String, nullable=True)
    creative_message_ids: Mapped[str | None] = mapped_column(String, nullable=True)
    creative_type: Mapped[str | None] = mapped_column(String, nullable=True)
    waiting_for_creative: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    creative_preview_text: Mapped[str | None] = mapped_column(String, nullable=True)
    creative_preview_file_id: Mapped[str | None] = mapped_column(String, nullable=True)
    creative_preview_file_ids: Mapped[str | None] = mapped_column(String, nullable=True)
    creative_preview_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    published_channel_id: Mapped[str | None] = mapped_column(String, nullable=True)
    published_message_ids: Mapped[str | None] = mapped_column(String, nullable=True)
    published_at: Mapped[str | None] = mapped_column(String, nullable=True)
    escrow_wallet_id: Mapped[str | None] = mapped_column(String, nullable=True)
    escrow_address: Mapped[str | None] = mapped_column(String, nullable=True)
    escrow_network: Mapped[str | None] = mapped_column(String, nullable=True)
    expected_amount_ton: Mapped[str | None] = mapped_column(String, nullable=True)
    payment_confirmed_at: Mapped[str | None] = mapped_column(String, nullable=True)
    payment_tx_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    release_tx_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    released_at: Mapped[str | None] = mapped_column(String, nullable=True)
    refund_tx_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    refunded_at: Mapped[str | None] = mapped_column(String, nullable=True)
    seller_wallet: Mapped[str | None] = mapped_column(String, nullable=True)
    cancelled_by: Mapped[str | None] = mapped_column(String, nullable=True)
    cancelled_at: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    post_not_found: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    post_is_modified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    top_violated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
