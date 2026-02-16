from __future__ import annotations

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
    created_at: str | None = None


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
    created_at: str | None = None
    offer_price_ton: float
    message: str = ""
    deal_id: str | None = None

    campaign_id: str
    campaign_title: str = ""

    channel: ChannelOut

    viewer_role: Literal["incoming", "my"]
    can_start_deal: bool = False

