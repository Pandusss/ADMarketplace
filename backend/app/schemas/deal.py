"""
Deal Schemas.
Pydantic models for advertising deals, defining data validation 
for API requests, responses, and internal state transfers.
"""
from __future__ import annotations
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, computed_field
import json


DealStatus = Literal[
    "negotiation",
    "pending_payment",
    "creative_draft",
    "creative_review",
    "approved",
    "scheduling",
    "scheduled",
    "awaiting_confirmation",
    "posted",
    "released",
    "cancelled",
    "refunded",
]


class DealCreateIn(BaseModel):
    channel_id: str
    campaign_brief: str = Field(min_length=1)
    creative_mode: str = "template"
    creative_instructions: str | None = None
    post_duration_hours: int | None = Field(default=None, ge=1)
    top_duration_hours: int = Field(default=0, ge=0)
    campaign_id: str | None = None


class DealOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    channel_id: str
    channel_name: str | None = None  # Channel title/name for display
    channel_handle: str | None = None
    channel_subscribers: int = 0
    channel_avg_views_24h: int = 0
    channel_category: str = ""
    channel_language: str = ""
    advertiser_id: str
    campaign_id: str | None = None
    emoji: str = ""
    status: DealStatus
    ad_format: Literal["post"]
    price_ton: float
    base_price_ton: float = 0.0
    created_at: datetime | None = None

    negotiation_confirmed_by_advertiser: bool = False
    negotiation_confirmed_by_channel: bool = False
    
    deal_confirmed_by_advertiser: bool = False
    deal_confirmed_by_channel: bool = False
    deal_confirmed_at: datetime | None = None
    auto_release_hours: int | None = None
    post_duration_hours: int | None = None
    top_duration_hours: int = 0

    campaign_brief: str
    creative_mode: str
    creative_instructions: str | None = None
    preferred_publish_at: str | None = None

    # Legacy field (not used in bot-first flow). Keep for backward compatibility.
    creative_text: str = ""
    scheduled_at: str | None = None

    cancelled_by: Literal["advertiser", "channel_owner", "system"] | None = None
    cancelled_at: datetime | None = None
    
    # Escrow fields (for frontend display)
    escrow_address: str | None = None
    escrow_network: str | None = None
    payment_confirmed_at: datetime | None = None
    payment_tx_hash: str | None = None
    release_tx_hash: str | None = None
    released_at: datetime | None = None
    refund_tx_hash: str | None = None
    refunded_at: datetime | None = None

    # Bot-first creative references (Telegram = editor)
    waiting_for_creative: bool = False
    creative_type: str | None = None
    creative_chat_id: str | None = None
    creative_message_ids: list[int] | None = None

    # Inline preview snapshot (COMPROMISE)
    creative_preview_text: str = ""
    # Removed creative_preview_has_media from regular fields to use @computed_field
    creative_preview_count: int = 0

    @computed_field
    @property
    def creative_preview_has_media(self) -> bool:
        return bool(self.creative_preview_file_id or self.creative_preview_file_ids)

    # These fields are required for the computed_field but can be hidden if needed.
    # We'll just ensure they are available from model_config(from_attributes=True)
    creative_preview_file_id: str = ""
    creative_preview_file_ids: str = ""

    # Publishing metadata
    published_channel_id: str | None = None
    published_at: datetime | None = None
    post_not_found: bool = False
    post_is_modified: bool = False
    top_violated: bool = False

    @field_validator("creative_message_ids", mode="before")
    @classmethod
    def decode_json_list(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return None
        return v

    @field_validator(
        "created_at", 
        "cancelled_at", 
        "payment_confirmed_at", 
        "released_at", 
        "refunded_at",
        "released_at", 
        "refunded_at",
        "published_at",
        "deal_confirmed_at",
        mode="before"
    )
    @classmethod
    def parse_datetime(cls, v):
        if isinstance(v, str):
            try:
                # Remove Z and use isoformat
                s = v.replace("Z", "+00:00")
                return datetime.fromisoformat(s)
            except Exception:
                return None
        return v


class DealPermissions(BaseModel):
    can_confirm_terms: bool
    can_confirm_deal: bool = False
    can_accept: bool
    can_pay: bool
    can_use_template: bool
    can_submit_creative: bool
    can_approve: bool
    can_approve_creative: bool
    can_request_edits: bool
    can_cancel: bool
    can_publish: bool
    can_release: bool
    can_request_slot: bool
    can_approve_slot: bool
    can_review: bool = False
    negotiation_confirmed_by_me: bool
    negotiation_confirmed_by_other: bool


class DealDetailOut(DealOut):
    permissions: DealPermissions
    channel_rating_avg: float = 0.0
    channel_rating_count: int = 0
    advertiser_rating_avg: float = 0.0
    advertiser_rating_count: int = 0
    channel_price_per_post_ton: float = 0.0
    channel_price_top_hour_ton: float = 0.0
    channel_top_price_step_pct: float = 0.0


class DealConfirmIn(BaseModel):
    pass


class DealAcceptOut(BaseModel):
    deal: DealOut


class DealRequestSlotIn(BaseModel):
    local_datetime: str  # YYYY-MM-DDTHH:MM


class DealSlot(BaseModel):
    key: str
    local: str
    utc: str
    busy: bool
    requested: bool
    scheduled: bool


class DealSlotsOut(BaseModel):
    timezone: str
    window_start: str
    window_end: str
    slot_minutes: int
    date: str
    slots: list[DealSlot]


class DealPayInstructionsOut(BaseModel):
    escrow_address: str
    amount_ton: float
    network: str
    instruction: str


class DealCreativeIn(BaseModel):
    # Deprecated: we do not accept creatives via Mini App.
    creative_text: str = Field(min_length=1)


class DealActionOut(BaseModel):
    deal: DealOut
