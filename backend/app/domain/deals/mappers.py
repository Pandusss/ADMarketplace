from __future__ import annotations

import json
from typing import Final

from app.db.models.deal import Deal, DealStatus
from app.schemas.deal import DealOut

ALLOWED_UPDATE_FIELDS: Final[set[str]] = {
    "status", "emoji", "creative_text", "creative_mode", "creative_instructions",
    "scheduled_at", "waiting_for_creative", "creative_chat_id", "creative_type",
    "creative_message_ids", "creative_preview_text", "creative_preview_file_id",
    "creative_preview_file_ids", "creative_preview_count", "published_channel_id", "published_message_ids",
    "published_at", "cancelled_by", "cancelled_at", "escrow_wallet_id",
    "escrow_address", "escrow_network", "expected_amount_ton",
    "payment_confirmed_at", "payment_tx_hash", "release_tx_hash",
    "released_at", "refund_tx_hash", "refunded_at", "seller_wallet", "preferred_publish_at",
    "negotiation_confirmed_by_advertiser", "negotiation_confirmed_by_channel",
    "deal_confirmed_by_advertiser", "deal_confirmed_by_channel", "deal_confirmed_at",
    "post_duration_hours",
    "top_duration_hours",
    "post_not_found",
}


def deal_to_dict(d: Deal) -> dict:
    return DealOut.model_validate(d).model_dump()


def apply_deal_dict(d: Deal, payload: dict) -> None:
    for k, v in payload.items():
        if k in ALLOWED_UPDATE_FIELDS:
            if k in ("creative_message_ids", "published_message_ids") and v is not None and not isinstance(v, str):
                setattr(d, k, json.dumps(v))
            else:
                setattr(d, k, v)
