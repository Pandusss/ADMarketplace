from __future__ import annotations

import json
import logging
import asyncio
from datetime import timedelta
from typing import Any, Dict

from app.db.session import SessionLocal
from app.db.models.user import User
from app.db.models.channel import Channel
from app.db.models.channel_snapshot import ChannelSnapshot
from app.db.models.channel_post import ChannelPost
from app.domain.channels.service import ChannelAnalyticsService
from app.infra.telegram.bot_client import TelegramBotClient
from app.infra.queue.rq import get_queue
from app.core.config import settings
from app.utils.dt import utcnow_naive

logger = logging.getLogger(__name__)

# --- Helpers ---

async def _join_and_promote(
    channel_id_tg: str,
    invite_link: str | None,
    channel_handle: str | None,
    service: ChannelAnalyticsService,
    bot: TelegramBotClient,
) -> None:
    """Join the channel with the user-bot and promote it to admin."""
    logger.info("[_join_and_promote] Started for %s", channel_id_tg)

    # 1. Join
    try:
        if invite_link:
            logger.info("[_join_and_promote] Joining via link: %s", invite_link)
            await service.join_channel(invite_link)
        elif channel_handle:
            logger.info("[_join_and_promote] Joining via handle: @%s", channel_handle)
            await service.join_channel(channel_handle)
        else:
            logger.info("[_join_and_promote] No link/handle for %s — skipping join", channel_id_tg)
    except Exception as e:
        logger.warning("[_join_and_promote] Join failed: %s", e)

    # 2. Promote
    try:
        me = await service.get_me()
        logger.info("[_join_and_promote] User-bot %s — promoting...", me.id)

        await bot.promote_chat_member(
            chat_id=channel_id_tg,
            user_id=me.id,
            can_post_messages=True,
            can_edit_messages=False,
            can_delete_messages=False,
        )
        logger.info("[_join_and_promote] Promoted %s in %s", me.id, channel_id_tg)
    except Exception as e:
        logger.warning("[_join_and_promote] Auto-promotion skipped/failed: %s", e)


async def _refresh_channel_avatar(db, channel: Channel, bot: TelegramBotClient) -> None:
    """Fetch and save channel avatar if it is missing."""
    if channel.avatar_file_id:
        return

    try:
        logger.info("Fetching missing avatar for %s...", channel.id)
        chat_info = await bot.get_chat(str(channel.telegram_channel_id))
        photo = chat_info.get("photo")
        if photo:
            channel.avatar_file_id = photo.get("small_file_id") or photo.get("big_file_id")
            db.commit()
            logger.info("Avatar updated for %s: %s", channel.id, channel.avatar_file_id)
    except Exception as e:
        logger.warning("Failed to refresh avatar for %s: %s", channel.id, e)


async def _scan_and_save_posts(
    db,
    channel: Channel,
    service: ChannelAnalyticsService,
    handle: str,
) -> Dict[str, Any]:
    """Scan recent posts, upsert them into DB, and return calculated metrics."""
    try:
        logger.info("Scanning posts for %s...", handle)
        posts_data = await service.scan_channel(handle, limit=200)

        # Calculate engagement metrics
        stats_result = service.calculate_stats(posts_data, subscribers=channel.subscribers_count)
        manual_metrics = stats_result.get("calculated_metrics", {})
        logger.info("Manual metrics for %s: %s", handle, manual_metrics)

        # Upsert posts
        post_ids = [p["post_id"] for p in posts_data]
        existing_posts = (
            db.query(ChannelPost)
            .filter(ChannelPost.channel_id == channel.id, ChannelPost.post_id.in_(post_ids))
            .all()
        )
        existing_by_id = {p.post_id: p for p in existing_posts}

        for p_dict in posts_data:
            existing = existing_by_id.get(p_dict["post_id"])

            if existing:
                existing.views = p_dict["views"]
                existing.forwards = p_dict["forwards"]
                existing.replies = p_dict["replies"]
                existing.reactions = json.dumps(p_dict["reactions"], ensure_ascii=False)
                existing.grouped_id = p_dict.get("grouped_id")
                existing.updated_at = utcnow_naive()
            else:
                db_data = {
                    **p_dict,
                    "reactions": json.dumps(p_dict["reactions"], ensure_ascii=False),
                    "date": (
                        p_dict["date"].replace(tzinfo=None)
                        if p_dict["date"].tzinfo
                        else p_dict["date"]
                    ),
                }
                db.add(ChannelPost(channel_id=channel.id, **db_data))

        channel.last_scanned_at = utcnow_naive()
        return manual_metrics

    except Exception as e:
        logger.error("Post scan failed for %s: %s", channel.id, e)
        db.rollback()
        return {}


async def _update_detailed_stats(
    channel: Channel,
    service: ChannelAnalyticsService,
    handle: str,
) -> None:
    """Fetch premium / region breakdown and write it to the channel model."""
    try:
        logger.info("Fetching detailed stats for %s...", handle)
        detailed = await service.get_detailed_stats(handle)
        logger.debug("Detailed stats for %s: %s", handle, detailed)

        channel.premium_subscribers_count = detailed.get("premium_count", 0)
        channel.premium_share = detailed.get("premium_percentage", 0.0)

        raw_regions = detailed.get("region_stats", {})
        total_processed = detailed.get("total_processed", 0)

        if total_processed > 0:
            channel.region_stats = {
                code.upper(): round((count / total_processed) * 100, 1)
                for code, count in raw_regions.items()
            }
        else:
            channel.region_stats = {}

    except Exception as e:
        logger.error("Detailed stats fetch failed for %s: %s", channel.id, e)


def _calculate_subscriber_deltas(db, channel: Channel, has_official_deltas: bool) -> None:
    """Fallback: calculate sub deltas from snapshots when Telegram stats are unavailable."""

    def _get_snapshot_delta(days: int) -> int:
        target_date = utcnow_naive() - timedelta(days=days)
        snap = (
            db.query(ChannelSnapshot)
            .filter(
                ChannelSnapshot.channel_id == channel.id,
                ChannelSnapshot.fetched_at <= target_date,
            )
            .order_by(ChannelSnapshot.fetched_at.desc())
            .first()
        )
        if not snap:
            snap = (
                db.query(ChannelSnapshot)
                .filter(ChannelSnapshot.channel_id == channel.id)
                .order_by(ChannelSnapshot.fetched_at.asc())
                .first()
            )
        return (channel.subscribers_count - snap.subscribers) if snap else 0

    try:
        if not has_official_deltas:
            channel.subs_today = _get_snapshot_delta(1)
            channel.subs_week = _get_snapshot_delta(7)
            channel.subs_month = _get_snapshot_delta(30)
    except Exception as e:
        logger.warning("Failed to calculate manual deltas for %s: %s", channel.id, e)


def _apply_telegram_metrics(channel: Channel, tg_metrics: dict) -> None:
    """Map official Telegram metrics onto the Channel ORM model."""
    channel.subscribers_count = tg_metrics.get("followers") or channel.subscribers_count

    channel.subs_today = tg_metrics.get("subs_today", 0)
    channel.subs_week = tg_metrics.get("subs_week", 0)
    channel.subs_month = tg_metrics.get("subs_month", 0)
    channel.avg_views_per_post = tg_metrics.get("avg_views_per_post", 0)
    channel.followers_trend_percent = tg_metrics.get("followers_trend_percent", 0.0)
    channel.joins_24h = tg_metrics.get("joins_24h", 0)
    channel.leaves_24h = tg_metrics.get("leaves_24h", 0)

    if tg_metrics.get("channel_created_at"):
        channel.channel_created_at = tg_metrics["channel_created_at"]

    if tg_metrics.get("official_languages"):
        channel.region_stats = tg_metrics["official_languages"]


def _apply_manual_metrics(channel: Channel, manual_metrics: dict) -> None:
    """Map calculated post-level metrics onto the Channel ORM model."""
    if not manual_metrics:
        return

    channel.avg_views_24h = manual_metrics.get("avg_views_24h", 0)
    channel.avg_views_7d = manual_metrics.get("avg_views_7d", 0)
    channel.median_views = manual_metrics.get("median_views", 0)
    channel.ad_reach_estimate = manual_metrics.get("ad_reach_estimate", 0)
    channel.stability_score = manual_metrics.get("stability_score", 0.0)
    channel.engagement_rate = manual_metrics.get("engagement_rate", 0.0)
    channel.median_er = manual_metrics.get("median_er", 0.0)
    channel.err_24h_percent = manual_metrics.get("err_24h_percent", 0.0)
    channel.avg_reactions = manual_metrics.get("avg_reactions", 0.0)
    channel.avg_forwards = manual_metrics.get("avg_forwards", 0.0)
    channel.avg_replies = manual_metrics.get("avg_replies", 0.0)
    channel.posts_per_day = manual_metrics.get("posts_per_day", 0.0)
    channel.posts_total = manual_metrics.get("posts_total", 0)
    channel.posts_yesterday = manual_metrics.get("posts_yesterday", 0)
    channel.posts_week = manual_metrics.get("posts_week", 0)
    channel.posts_month = manual_metrics.get("posts_month", 0)


def _apply_derived_fields(channel: Channel) -> None:
    """Fill in secondary / fallback fields."""
    if not channel.reach_24h:
        channel.reach_24h = channel.avg_views_24h

    channel.avg_views = (
        channel.avg_views_7d if channel.avg_views_7d > 0 else channel.avg_views_per_post
    )

    channel.last_stats_update = utcnow_naive()
    channel.verified_stats = True


def _apply_metrics_to_channel(
    channel: Channel,
    stats: dict,
    manual_metrics: dict,
) -> None:
    """Orchestrate all metric-application helpers."""
    tg_metrics = stats.get("telegram_metrics", {})
    _apply_telegram_metrics(channel, tg_metrics)
    _apply_manual_metrics(channel, manual_metrics)
    _apply_derived_fields(channel)


def _create_snapshot(db, channel: Channel, languages: dict | None) -> None:
    """Persist a historical snapshot of the channel's current state."""
    snapshot = ChannelSnapshot(
        channel_id=channel.id,
        subscribers=channel.subscribers_count,
        avg_views_24h=channel.avg_views_24h,
        avg_views_7d=channel.avg_views_7d,
        languages=languages,
        premium_share=channel.premium_share,
        growth_7d=channel.followers_trend_percent,
        stability_score=channel.stability_score,
        premium_subscribers_count=channel.premium_subscribers_count,
        region_stats=channel.region_stats,
    )
    db.add(snapshot)
    logger.info("Snapshot created for %s", channel.id)


# --- Main Task Logic ---

async def _update_channel_analytics_async(
    channel_id: str,
    invite_link: str | None = None,
) -> None:
    """Core async pipeline: join → fetch stats → scan → persist."""
    logger.info("[Analytics] Triggered for %s", channel_id)
    db = SessionLocal()

    try:
        channel = db.query(Channel).filter(Channel.id == channel_id).one_or_none()
        if not channel:
            logger.error("Channel %s not found", channel_id)
            return

        service = ChannelAnalyticsService()
        await service.start()

        try:
            bot = TelegramBotClient(settings.telegram_bot_token)
            await bot.start()
            try:
                # 1. Avatar
                await _refresh_channel_avatar(db, channel, bot)

                # 2. Join & promote
                await _join_and_promote(
                    channel_id_tg=str(channel.telegram_channel_id),
                    invite_link=invite_link,
                    channel_handle=channel.handle,
                    service=service,
                    bot=bot,
                )

                handle = channel.handle or channel.telegram_channel_id
                if not handle:
                    logger.error("Channel %s has no handle or telegram_id", channel_id)
                    return

                # 3. Official Telegram stats
                stats = await service.fetch_channel_stats(handle)

                # 3.5  Update subscribers_count BEFORE calculating ER
                tg_subs = stats.get("telegram_metrics", {}).get("followers")
                if tg_subs:
                    channel.subscribers_count = tg_subs

                # 4. Post scan & calculated metrics
                manual_metrics = await _scan_and_save_posts(db, channel, service, handle)

                # 5. Detailed stats (premium, regions)
                await _update_detailed_stats(channel, service, handle)

                # 6. Apply all metrics to ORM model
                _apply_metrics_to_channel(channel, stats, manual_metrics)

                # 7. Subscriber deltas (fallback from snapshots)
                tg_metrics = stats.get("telegram_metrics", {})
                has_official_deltas = bool(
                    tg_metrics.get("subs_today") or tg_metrics.get("subs_week")
                )
                _calculate_subscriber_deltas(db, channel, has_official_deltas)

                logger.info("Final region_stats for %s: %s", channel.id, channel.region_stats)

                # 8. Snapshot + commit
                _create_snapshot(
                    db, channel,
                    stats.get("telegram_metrics", {}).get("official_languages"),
                )
                db.commit()

                logger.info(
                    "Successfully updated analytics for %s (@%s)",
                    channel.id,
                    channel.handle,
                )

            finally:
                await bot.stop()

        except Exception as e:
            logger.exception("Failed to update analytics for %s: %s", channel_id, e)
        finally:
            await service.stop()

    except Exception as e:
        logger.exception("Fatal error initializing analytics for %s: %s", channel_id, e)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# RQ entry-points
# ---------------------------------------------------------------------------

def update_channel_analytics(channel_id: str, invite_link: str | None = None) -> None:
    """Synchronous RQ job wrapper — runs the async pipeline."""
    logger.info("[RQ Job] update_channel_analytics for %s", channel_id)
    asyncio.run(_update_channel_analytics_async(channel_id, invite_link))


def dispatch_analytics_updates(batch_size: int = 50) -> None:
    """Periodic dispatcher: enqueue stale channels for analytics refresh."""
    logger.info("[Dispatcher] Starting analytics dispatch (batch_size=%d)", batch_size)
    db = SessionLocal()

    try:
        cutoff = utcnow_naive() - timedelta(hours=12)

        candidates = (
            db.query(Channel)
            .filter(
                (Channel.last_scanned_at.is_(None)) | (Channel.last_scanned_at < cutoff)
            )
            .limit(batch_size)
            .all()
        )

        if not candidates:
            logger.info("[Dispatcher] No stale channels found.")
            return

        q = get_queue()
        logger.info("[Dispatcher] Found %d channels to update. Enqueuing...", len(candidates))

        for ch in candidates:
            job = q.enqueue(
                "app.tasks.analytics_tasks.update_channel_analytics",
                args=(ch.id,),
                job_timeout="10m",
                result_ttl=86400,
                description=f"Update analytics for {ch.title or ch.id}",
            )
            logger.info("[Dispatcher] Enqueued %s → Job %s", ch.id, job.id)

    except Exception as e:
        logger.exception("[Dispatcher] Failed to dispatch updates: %s", e)
    finally:
        db.close()
