from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime

from app.core.config import settings
from app.db.session import SessionLocal
from app.db.models.deal import Deal, DealStatus
from app.domain.deals.service import release_funds_action, ACTOR_SYSTEM

logger = logging.getLogger(__name__)


def auto_release_task(deal_id: str) -> dict:
    if not settings.telegram_bot_token:
        return {"ok": False, "detail": "Telegram bot not configured"}

    return asyncio.run(_auto_release_async(deal_id))


async def _auto_release_async(deal_id: str) -> dict:
    db = SessionLocal()
    try:
        deal = db.query(Deal).filter(Deal.id == deal_id).one_or_none()
        if not deal:
            return {"ok": False, "detail": "Deal not found"}

        if deal.status == DealStatus.released.value:
            return {"ok": True, "detail": "Already released"}

        if deal.status != DealStatus.posted.value:
            return {"ok": False, "detail": f"Deal status is {deal.status}, expected posted"}

        if deal.post_not_found:
            return {"ok": False, "detail": "Post not found, awaiting advertiser decision"}

        if getattr(deal, "top_violated", False):
            return {"ok": False, "detail": "Top placement was violated, awaiting advertiser decision"}

        msg_ids = []
        if deal.published_message_ids:
            try:
                msg_ids = json.loads(deal.published_message_ids)
            except Exception:
                msg_ids = []

        can_verify = bool(deal.published_channel_id and msg_ids)

        if can_verify:
            try:
                post_ok, is_modified = await _check_post_exists(deal, msg_ids)
            except Exception as e:
                logger.error(f"Post check failed for {deal_id}: {e}", exc_info=True)
                post_ok, is_modified = False, False

            if not post_ok:
                logger.warning(f"Post not found for deal {deal_id}, flagging for manual release")
                deal.post_not_found = True
                deal.updated_at = datetime.utcnow()
                db.commit()
                return {"ok": False, "detail": "Post not found, awaiting advertiser decision"}
            
            if is_modified:
                logger.warning(f"Post modified for deal {deal_id}, flagging for manual release")
                deal.post_is_modified = True
                deal.updated_at = datetime.utcnow()
                db.commit()
                return {"ok": False, "detail": "Post has been modified, awaiting advertiser decision"}
        else:
            logger.warning(f"Deal {deal_id} missing verification data, flagging for manual release")
            deal.post_not_found = True
            deal.updated_at = datetime.utcnow()
            db.commit()
            return {"ok": False, "detail": "Cannot verify post, awaiting advertiser decision"}

        try:
            await release_funds_action(db, deal.id, ACTOR_SYSTEM)
            return {"ok": True, "detail": "Funds released", "deal_id": deal_id}
        except Exception as e:
            logger.error(f"Release failed for {deal_id}: {e}", exc_info=True)
            return {"ok": False, "detail": str(e)}

    finally:
        db.close()


async def _check_post_exists(deal: Deal, msg_ids: list) -> tuple[bool, bool]:
    from app.domain.channels.service import ChannelAnalyticsService

    check_id = int(msg_ids[0])
    channel_id = deal.published_channel_id

    svc = ChannelAnalyticsService()
    try:
        await svc.start()
        client = svc._ensure_client()
        msgs = await client.get_messages(int(channel_id), ids=check_id)
        msg = msgs if not isinstance(msgs, list) else (msgs[0] if msgs else None)
        if msg is None:
            logger.warning(f"Post {check_id} deleted in channel {channel_id} (deal {deal.id})")
            return False, False
        
        # Check if the message was edited
        is_modified = msg.edit_date is not None
        if is_modified:
            logger.warning(f"Post {check_id} was modified at {msg.edit_date} in channel {channel_id} (deal {deal.id})")
            
        return True, is_modified
    except Exception as e:
        logger.error(f"Post check error for {deal.id} (msg {check_id}): {e}", exc_info=True)
        return False, False
    finally:
        await svc.stop()
