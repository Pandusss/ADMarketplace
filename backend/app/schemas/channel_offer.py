from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.channel import ChannelOut


class ChannelOfferCreateIn(BaseModel):
    """Create a new channel offer (advertiser → channel owner)."""
    
    campaign_title: str = Field(default="", max_length=100, description="Short campaign title")
    campaign_brief: str = Field(..., min_length=1, description="Brief description of the campaign")
    creative_mode: str = Field(default="template", description="Creative mode: 'template' or 'custom_task'")
    creative_instructions: str | None = Field(default=None, description="Custom instructions for creative (if custom_task mode)")
    preferred_publish_at: str | None = Field(default=None, description="Preferred publish time in ISO format")
    template_id: str | None = Field(default=None, description="Selected template ID (if mode=template)")
    message: str = Field(default="", description="Optional message to channel owner")
    post_duration_hours: int = Field(default=24, ge=1, le=168, description="How long the post must stay (hours)")


class ChannelOfferOut(BaseModel):
    """Basic channel offer output."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    channel_id: str
    advertiser_id: str
    offer_price_ton: float
    message: str
    status: str
    deal_id: str | None
    created_at: datetime | None = None


class ChannelOfferListOut(ChannelOfferOut):
    """Channel offer in list view with channel name."""
    
    channel_name: str
    deal_status: str | None = None


class ChannelOfferDetailOut(ChannelOfferOut):
    """Detailed channel offer with full channel info and campaign details."""
    
    campaign_brief: str
    campaign_title: str = ""
    creative_mode: str
    creative_instructions: str | None
    preferred_publish_at: str | None
    channel: ChannelOut
    viewer_role: Literal["incoming", "my"]
    post_duration_hours: int = 24
    can_start_deal: bool
    advertiser_rating_avg: float = 0.0
    advertiser_rating_count: int = 0
    # Explicit roles
    advertiser_rating_advertiser_avg: float = 0.0
    advertiser_rating_advertiser_count: int = 0

    advertiser_display_name: str = ""
    advertiser_username: str | None = None
