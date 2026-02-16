from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal

from app.schemas.channel import ChannelOut


class CampaignApplyIn(BaseModel):
    channel_id: str = Field(min_length=1)
    offer_price_ton: float | None = None
    message: str | None = None


class CampaignOfferOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    campaign_id: str
    channel_id: str
    applicant_id: str
    offer_price_ton: float
    message: str
    status: str
    deal_id: str | None = None
    created_at: datetime | None = None


class CampaignOfferListOut(CampaignOfferOut):
    """
    Extended view for listing offers in the Mini App.
    Avoids technical IDs in UI by providing human-readable titles.
    """

    campaign_title: str = ""
    channel_name: str = ""
    template_id: str = ""
    template_preview_text: str = ""
    template_preview_has_media: bool = False
    template_preview_count: int = 0
    deal_status: str | None = None


class CampaignOfferDetailOut(BaseModel):
    """
    Full view for an offer details page.
    Shows channel info (important for advertiser) and campaign title (important context).
    """

    id: str
    status: str
    created_at: datetime | None = None
    offer_price_ton: float
    message: str = ""
    deal_id: str | None = None

    campaign_id: str
    campaign_title: str = ""

    channel: ChannelOut

    campaign_owner_id: str = ""
    campaign_owner_display_name: str = ""
    campaign_owner_username: str | None = None
    campaign_owner_rating_avg: float = 0.0
    campaign_owner_rating_count: int = 0
    # Explicit roles
    campaign_owner_rating_advertiser_avg: float = 0.0
    campaign_owner_rating_advertiser_count: int = 0

    applicant_id: str = ""
    applicant_rating_avg: float = 0.0
    applicant_rating_count: int = 0
    # Explicit roles
    applicant_rating_owner_avg: float = 0.0
    applicant_rating_owner_count: int = 0

    viewer_role: Literal["incoming", "my"]
    can_start_deal: bool = False
