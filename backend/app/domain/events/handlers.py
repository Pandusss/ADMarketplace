"""
Event Handlers.
Implements internal system signals and asynchronous callbacks 
triggered by state changes in deals, payments, or channel registrations.
"""
from __future__ import annotations
import logging
from typing import Final, Optional

from app.infra.events.bus import deal_updated
from app.domain.events.types import DealEvent
from app.infra.telegram.bot_client import TelegramBotClient
from app.infra.websocket.manager import notify_deal_update
from app.core.config import settings
from app.db.models.deal import Deal
from app.db.models.user import User
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)

# Constants - Messages
MSG_NEW_DEAL_REQ: Final[str] = "📩 <b>New Deal Request</b>\nChannel: {channel}\n\n💬 Chat is open. Reply to this message to write to the advertiser."
MSG_DEAL_CREATED: Final[str] = "✅ <b>Deal Created</b>\nDeal {emoji} #{deal_id}\n\n💬 Chat is open. Reply to write to the channel owner."
MSG_TERMS_AGREED_ADV: Final[str] = "💳 <b>Terms Agreed!</b>\nDeal {emoji} #{deal_id} is ready for payment.\nPlease proceed to the wallet to pay."
MSG_TERMS_AGREED_OWNER: Final[str] = "⏳ <b>Terms Agreed!</b>\nDeal {emoji} #{deal_id} is now waiting for payment from the advertiser."
MSG_SLOT_REQUESTED: Final[str] = "📅 <b>Slot Requested</b>\nDeal {emoji} #{deal_id}\nThe advertiser has requested a publication slot. Please approve it in the app."
MSG_SLOT_APPROVED: Final[str] = "✅ <b>Slot Approved</b>\nDeal {emoji} #{deal_id}\nYour requested slot has been approved by the channel owner."
MSG_CREATIVE_SUBMITTED: Final[str] = "🎨 <b>Creative Submitted</b>\nDeal {emoji} #{deal_id}\nA creative draft has been submitted for your review."
MSG_CREATIVE_APPROVED: Final[str] = "⭐ <b>Creative Approved!</b>\nDeal {emoji} #{deal_id}\nYour creative has been approved. The post is ready to be published."
MSG_EDITS_REQUESTED: Final[str] = "✏️ <b>Edits Requested</b>\nDeal {emoji} #{deal_id}\nEdits have been requested for your creative draft. Please check the chat."
MSG_PUBLISHED_ADV: Final[str] = "🚀 <b>Deal Published!</b>\nDeal {emoji} #{deal_id}\nThe creative is now live on the channel. Check the post!"
MSG_PUBLISHED_OWNER: Final[str] = "✅ <b>Post Published</b>\nDeal {emoji} #{deal_id} has been successfully posted to your channel."
MSG_FUNDS_RELEASED_OWNER: Final[str] = "💰 <b>Funds Released!</b>\nDeal {emoji} #{deal_id}\nThe advertiser has released the funds. {amount} TON is on its way to your wallet!"
MSG_FUNDS_RELEASED_ADV: Final[str] = "🏁 <b>Deal Completed</b>\nDeal {emoji} #{deal_id}\nFunds released. Thank you for using our platform!"
MSG_DEAL_CANCELLED: Final[str] = "❌ <b>Deal Cancelled</b>\nDeal #{deal_id} was cancelled. The chat is now closed."
MSG_REFUND_CONFIRMED: Final[str] = "💰 <b>Refund Confirmed</b>\nDeal {emoji} #{deal_id}\n{amount} TON has been returned to your wallet."
MSG_DEAL_REFUNDED: Final[str] = "❌ <b>Deal Refunded</b>\nDeal #{deal_id} was cancelled and funds were returned to the advertiser."
MSG_DEAL_AWAITING: Final[str] = "📋 <b>Deal Ready for Confirmation</b>\nDeal {emoji} #{deal_id}\nPlease review the final terms and confirm in the app."
MSG_DEAL_BOTH_CONFIRMED: Final[str] = "✅ <b>Deal Confirmed!</b>\nDeal {emoji} #{deal_id}\nBoth parties confirmed. The post will be published as scheduled."
MSG_TOP_VIOLATED: Final[str] = "⚠️ <b>Top Placement Violated!</b>\nDeal {emoji} #{deal_id}\nA new post was published in the channel before the top duration expired. Automatic fund release is paused — please review and decide in the app."

async def _send_tg(uid: str, text: str, reply_markup: dict | None = None):
    if not settings.telegram_bot_token or not uid: return
    try:
        bot = TelegramBotClient(settings.telegram_bot_token)
        await bot.send_message(uid, text, reply_markup=reply_markup, parse_mode="HTML")
    except Exception as e:
        logger.warning(f"Failed to send TG to {uid}: {e}")

async def on_deal_updated_ws(event: DealEvent):
    notify_deal_update(event.deal_id, event_type=event.event_type or "updated")

_TG_NOTIFICATIONS: dict[str, list[tuple[str, str]]] = {
    "created":            [("owner", MSG_NEW_DEAL_REQ), ("adv", MSG_DEAL_CREATED)],
    "pending_payment":    [("adv", MSG_TERMS_AGREED_ADV), ("owner", MSG_TERMS_AGREED_OWNER)],
    "slot_requested":     [("owner", MSG_SLOT_REQUESTED)],
    "slot_approved":      [("adv", MSG_DEAL_AWAITING), ("owner", MSG_DEAL_AWAITING)],
    "published":          [("adv", MSG_PUBLISHED_ADV), ("owner", MSG_PUBLISHED_OWNER)],
    "released":           [("owner", MSG_FUNDS_RELEASED_OWNER), ("adv", MSG_FUNDS_RELEASED_ADV)],
    "cancelled":          [("adv", MSG_DEAL_CANCELLED), ("owner", MSG_DEAL_CANCELLED)],
    "refunded":           [("adv", MSG_REFUND_CONFIRMED), ("owner", MSG_DEAL_REFUNDED)],
    "deal_confirmed":     [("adv", MSG_DEAL_BOTH_CONFIRMED), ("owner", MSG_DEAL_BOTH_CONFIRMED)],
    "creative_submitted": [("creative_reviewer", MSG_CREATIVE_SUBMITTED)],
    "creative_approved":  [("creative_submitter", MSG_CREATIVE_APPROVED)],
    "edits_requested":    [("creative_submitter", MSG_EDITS_REQUESTED)],
    "top_violated":       [("adv", MSG_TOP_VIOLATED)],
}


def _resolve_recipient(role: str, deal: Deal, owner: Optional[User], adv: Optional[User]) -> Optional[User]:
    if role == "owner":
        return owner
    if role == "adv":
        return adv
    is_custom = getattr(deal, "creative_mode", "template") == "custom_task"
    if role == "creative_reviewer":
        return adv if is_custom else owner
    if role == "creative_submitter":
        return owner if is_custom else adv
    return None


def _build_format_kwargs(deal: Deal, event: DealEvent) -> dict:
    base = {"emoji": deal.emoji, "deal_id": deal.id}
    if event.event_type == "created":
        base["channel"] = (event.metadata or {}).get("channel_title") or "the channel"
    if event.event_type == "released":
        base["amount"] = deal.price_ton
    if event.event_type == "refunded":
        base["amount"] = deal.expected_amount_ton
    return base


async def on_deal_updated_tg(event: DealEvent):
    db = SessionLocal()
    try:
        deal = db.query(Deal).get(event.deal_id)
        if not deal:
            return

        owner = db.query(User).get(deal.channel.owner_id) if deal.channel and deal.channel.owner_id else None
        adv = db.query(User).get(deal.advertiser_id)

        if event.event_type == "deal_confirmed":
            if not (deal.deal_confirmed_by_advertiser and deal.deal_confirmed_by_channel):
                return

        entries = _TG_NOTIFICATIONS.get(event.event_type)
        if not entries:
            return

        fmt = _build_format_kwargs(deal, event)

        for role, template in entries:
            recipient = _resolve_recipient(role, deal, owner, adv)
            if recipient:
                await _send_tg(recipient.telegram_user_id, template.format(**fmt))
    finally:
        db.close()

def register_signal_handlers():
    deal_updated.connect(on_deal_updated_ws)
    deal_updated.connect(on_deal_updated_tg)
    logger.info("Internal signal handlers registered.")
