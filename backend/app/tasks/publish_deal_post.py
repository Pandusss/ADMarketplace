from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from app.core.config import settings
from app.db.session import SessionLocal
from app.db.models.deal import Deal, DealStatus
from app.domain.deals.service import publish_deal_by_system


logger = logging.getLogger(__name__)

def _parse_iso_maybe_z(s: str) -> datetime:
    raw = (s or "").strip()
    if raw.endswith("Z"):
        raw = raw.replace("Z", "+00:00")
    dt = datetime.fromisoformat(raw)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def publish_deal_post(deal_id: str) -> dict:
    """
    RQ job: publish scheduled deal post to the channel.
    Wraps deal_service.publish_deal_by_system().
    """

    if not settings.telegram_bot_token:
        raise RuntimeError("Telegram bot not configured")

    db = SessionLocal()
    try:
        deal = db.query(Deal).filter(Deal.id == deal_id).one_or_none()
        if not deal:
            return {"ok": False, "detail": "Deal not found"}

        if deal.status in (DealStatus.posted.value, DealStatus.released.value):
            return {"ok": True, "detail": f"Already {deal.status}"}
        if deal.status in (DealStatus.cancelled.value, DealStatus.refunded.value):
            return {"ok": True, "detail": f"Deal is {deal.status}"}
        if deal.status != DealStatus.scheduled.value:
            return {"ok": False, "detail": f"Not scheduled (status={deal.status})"}

        # Scheduled time check
        if not (deal.scheduled_at or "").strip():
            return {"ok": False, "detail": "Missing scheduled_at"}

        scheduled_utc = _parse_iso_maybe_z(str(deal.scheduled_at))
        now_utc = datetime.now(tz=timezone.utc)
        if scheduled_utc > now_utc:
            return {"ok": True, "detail": "Not due yet"}

        # Use the service method to publish
        # asyncio.run is needed because RQ jobs are sync, but service is async
        try:
            asyncio.run(publish_deal_by_system(db, deal.id))
            return {"ok": True, "detail": "Published", "deal_id": deal_id}
        except Exception as e:
            logger.error(f"Failed to publish deal {deal_id}: {e}", exc_info=True)
            return {"ok": False, "detail": str(e)}

    finally:
        db.close()
