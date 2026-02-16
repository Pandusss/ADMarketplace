from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

from app.core.config import settings
from app.db.session import SessionLocal
from app.db.models.deal import Deal, DealStatus

logger = logging.getLogger(__name__)


def check_top_task(deal_id: str) -> dict:
    """RQ job: check if top placement was violated for a deal."""
    if not settings.telegram_bot_token:
        return {"ok": False, "detail": "Telegram bot not configured"}
    return asyncio.run(_check_top_async(deal_id))


async def _check_top_async(deal_id: str) -> dict:
    db = SessionLocal()
    try:
        deal = db.query(Deal).filter(Deal.id == deal_id).one_or_none()
        if not deal:
            return {"ok": False, "detail": "Deal not found"}

        if deal.status not in (DealStatus.posted.value, DealStatus.released.value):
            return {"ok": False, "detail": f"Deal status is {deal.status}, skipping top check"}

        top_hours = deal.top_duration_hours or 0
        if top_hours <= 0:
            return {"ok": True, "detail": "No top duration set"}

        if not deal.published_channel_id or not deal.published_message_ids:
            return {"ok": False, "detail": "Missing publication data"}

        try:
            msg_ids = json.loads(deal.published_message_ids)
        except Exception:
            return {"ok": False, "detail": "Cannot parse published_message_ids"}

        if not msg_ids:
            return {"ok": False, "detail": "Empty published_message_ids"}

        # The max id is the last message of the media group
        max_published_id = max(int(mid) for mid in msg_ids)

        violated = await _check_newer_posts_exist(
            channel_id=deal.published_channel_id,
            after_msg_id=max_published_id,
        )

        if violated:
            logger.warning(
                f"Top violated for deal {deal_id}: "
                f"newer posts found after msg {max_published_id} "
                f"in channel {deal.published_channel_id}"
            )
            deal.top_violated = True
            deal.updated_at = datetime.utcnow()
            db.commit()

            # Emit signal so notifications can be sent
            try:
                from app.infra.events import bus as signals
                asyncio.get_event_loop().create_task(
                    signals.deal_updated.emit(
                        signals.DealEvent(
                            deal_id=deal.id,
                            actor_id="system",
                            event_type="top_violated",
                        )
                    )
                )
            except Exception as e:
                logger.error(f"Failed to emit top_violated signal: {e}")

            return {"ok": True, "detail": "Top placement was violated", "violated": True}
        else:
            logger.info(f"Top OK for deal {deal_id}: post is still last in channel")
            return {"ok": True, "detail": "Top placement intact", "violated": False}

    finally:
        db.close()


async def _check_newer_posts_exist(channel_id: str, after_msg_id: int) -> bool:
    """
    Check if any messages with id > after_msg_id exist in the channel.
    Uses Telethon (userbot) since the bot API can't list channel messages.
    """
    from app.domain.channels.service import ChannelAnalyticsService

    svc = ChannelAnalyticsService()
    try:
        await svc.start()
        client = svc._ensure_client()

        # Get the most recent message in the channel
        last_msgs = await client.get_messages(int(channel_id), limit=1)
        last_msg = last_msgs[0] if isinstance(last_msgs, list) and last_msgs else last_msgs

        if last_msg is None:
            # Channel is empty — post was deleted, but that's a different issue
            return False

        # If the latest message id is greater than our max published id,
        # something was posted after our ad
        return last_msg.id > after_msg_id

    except Exception as e:
        logger.error(f"Top check error for channel {channel_id}, msg {after_msg_id}: {e}", exc_info=True)
        # On error, don't flag as violated — fail safe
        return False
    finally:
        await svc.stop()
