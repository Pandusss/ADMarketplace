import sqlite3
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

def ensure_sqlite_schema() -> None:
    """
    Minimal sqlite schema migrations (non-destructive).

    We use Base.metadata.create_all(), but it doesn't ALTER existing tables.
    So we patch missing columns in-place for local dev.
    """

    url = (settings.database_url or "").strip()
    if not url.startswith("sqlite"):
        return

    # Expected formats:
    # - sqlite+pysqlite:////abs/path/to/app.db
    # - sqlite:///abs/path/to/app.db
    if "///" not in url:
        return
    db_path = url.split("///", 1)[1].split("?", 1)[0]
    if not db_path:
        return

    try:
        con = sqlite3.connect(db_path)
        cur = con.cursor()

        # campaigns.title (added after initial table creation)
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='campaigns'")
        if cur.fetchone():
            cur.execute("PRAGMA table_info(campaigns)")
            cols = [row[1] for row in cur.fetchall()]
            if "title" not in cols:
                logger.info("[DB] Migrating: adding campaigns.title")
                cur.execute("ALTER TABLE campaigns ADD COLUMN title TEXT NOT NULL DEFAULT ''")
                con.commit()
                con.commit()
            if "desired_views_24h" not in cols:
                logger.info("[DB] Migrating: adding campaigns.desired_views_24h")
                cur.execute("ALTER TABLE campaigns ADD COLUMN desired_views_24h INTEGER")
                con.commit()
            if "post_duration_hours" not in cols:
                logger.info("[DB] Migrating: adding campaigns.post_duration_hours")
                # Default 24h for existing campaigns to be safe
                cur.execute("ALTER TABLE campaigns ADD COLUMN post_duration_hours INTEGER NOT NULL DEFAULT 24")
                con.commit()

        # campaign_offers.deal_id (added for buy-ads -> deal conversion)
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='campaign_offers'")
        if cur.fetchone():
            cur.execute("PRAGMA table_info(campaign_offers)")
            cols = [row[1] for row in cur.fetchall()]
            if "deal_id" not in cols:
                logger.info("[DB] Migrating: adding campaign_offers.deal_id")
                cur.execute("ALTER TABLE campaign_offers ADD COLUMN deal_id TEXT")
                con.commit()

        # channel_offers.post_duration_hours
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='channel_offers'")
        if cur.fetchone():
            cur.execute("PRAGMA table_info(channel_offers)")
            cols = [row[1] for row in cur.fetchall()]
            if "post_duration_hours" not in cols:
                logger.info("[DB] Migrating: adding channel_offers.post_duration_hours")
                cur.execute("ALTER TABLE channel_offers ADD COLUMN post_duration_hours INTEGER NOT NULL DEFAULT 24")
                con.commit()

        # deals.negotiation_confirmed_* (two-sided negotiation confirmation)
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='deals'")
        if cur.fetchone():
            cur.execute("PRAGMA table_info(deals)")
            cols = [row[1] for row in cur.fetchall()]
            if "negotiation_confirmed_by_advertiser" not in cols:
                logger.info("[DB] Migrating: adding deals.negotiation_confirmed_by_advertiser")
                cur.execute("ALTER TABLE deals ADD COLUMN negotiation_confirmed_by_advertiser INTEGER NOT NULL DEFAULT 0")
                con.commit()
            if "negotiation_confirmed_by_channel" not in cols:
                logger.info("[DB] Migrating: adding deals.negotiation_confirmed_by_channel")
                cur.execute("ALTER TABLE deals ADD COLUMN negotiation_confirmed_by_channel INTEGER NOT NULL DEFAULT 0")
                con.commit()
            if "refund_tx_hash" not in cols:
                logger.info("[DB] Migrating: adding deals.refund_tx_hash")
                cur.execute("ALTER TABLE deals ADD COLUMN refund_tx_hash TEXT")
                con.commit()
            if "refunded_at" not in cols:
                logger.info("[DB] Migrating: adding deals.refunded_at")
                cur.execute("ALTER TABLE deals ADD COLUMN refunded_at TEXT")
                con.commit()
            if "deal_confirmed_by_advertiser" not in cols:
                logger.info("[DB] Migrating: adding deals.deal_confirmed_by_advertiser")
                cur.execute("ALTER TABLE deals ADD COLUMN deal_confirmed_by_advertiser INTEGER NOT NULL DEFAULT 0")
                con.commit()
            if "deal_confirmed_by_channel" not in cols:
                logger.info("[DB] Migrating: adding deals.deal_confirmed_by_channel")
                cur.execute("ALTER TABLE deals ADD COLUMN deal_confirmed_by_channel INTEGER NOT NULL DEFAULT 0")
                con.commit()
            if "deal_confirmed_at" not in cols:
                logger.info("[DB] Migrating: adding deals.deal_confirmed_at")
                cur.execute("ALTER TABLE deals ADD COLUMN deal_confirmed_at TEXT")
                con.commit()
            if "auto_release_hours" not in cols:
                logger.info("[DB] Migrating: adding deals.auto_release_hours")
                cur.execute("ALTER TABLE deals ADD COLUMN auto_release_hours INTEGER")
                con.commit()
            if "post_duration_hours" not in cols:
                logger.info("[DB] Migrating: adding deals.post_duration_hours")
                cur.execute("ALTER TABLE deals ADD COLUMN post_duration_hours INTEGER")
                con.commit()

        # channels posting availability settings
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='channels'")
        if cur.fetchone():
            cur.execute("PRAGMA table_info(channels)")
            cols = [row[1] for row in cur.fetchall()]
            if "avatar_file_id" not in cols:
                logger.info("[DB] Migrating: adding channels.avatar_file_id")
                cur.execute("ALTER TABLE channels ADD COLUMN avatar_file_id TEXT")
                con.commit()
            if "posting_timezone" not in cols:
                logger.info("[DB] Migrating: adding channels.posting_timezone")
                cur.execute("ALTER TABLE channels ADD COLUMN posting_timezone TEXT NOT NULL DEFAULT 'UTC'")
                con.commit()
            if "posting_window_start" not in cols:
                logger.info("[DB] Migrating: adding channels.posting_window_start")
                cur.execute("ALTER TABLE channels ADD COLUMN posting_window_start TEXT NOT NULL DEFAULT '10:00'")
                con.commit()
            if "posting_window_end" not in cols:
                logger.info("[DB] Migrating: adding channels.posting_window_end")
                cur.execute("ALTER TABLE channels ADD COLUMN posting_window_end TEXT NOT NULL DEFAULT '20:00'")
                con.commit()
            if "posting_slot_minutes" not in cols:
                logger.info("[DB] Migrating: adding channels.posting_slot_minutes")
                cur.execute("ALTER TABLE channels ADD COLUMN posting_slot_minutes INTEGER NOT NULL DEFAULT 30")
                con.commit()
            
            # Analytics columns
            if "avg_views_24h" not in cols:
                logger.info("[DB] Migrating: adding channels.avg_views_24h")
                cur.execute("ALTER TABLE channels ADD COLUMN avg_views_24h INTEGER NOT NULL DEFAULT 0")
                con.commit()
            if "avg_views_7d" not in cols:
                logger.info("[DB] Migrating: adding channels.avg_views_7d")
                cur.execute("ALTER TABLE channels ADD COLUMN avg_views_7d INTEGER NOT NULL DEFAULT 0")
                con.commit()
            if "premium_share" not in cols:
                logger.info("[DB] Migrating: adding channels.premium_share")
                cur.execute("ALTER TABLE channels ADD COLUMN premium_share FLOAT NOT NULL DEFAULT 0.0")
                con.commit()
            if "growth_7d" not in cols:
                logger.info("[DB] Migrating: adding channels.growth_7d")
                cur.execute("ALTER TABLE channels ADD COLUMN growth_7d FLOAT NOT NULL DEFAULT 0.0")
                con.commit()
            if "last_stats_update" not in cols:
                logger.info("[DB] Migrating: adding channels.last_stats_update")
                cur.execute("ALTER TABLE channels ADD COLUMN last_stats_update DATETIME")
                con.commit()
            
            # Manual Scraper columns
            if "engagement_rate" not in cols:
                logger.info("[DB] Migrating: adding channels.engagement_rate")
                cur.execute("ALTER TABLE channels ADD COLUMN engagement_rate FLOAT NOT NULL DEFAULT 0.0")
                con.commit()
            if "posts_per_day" not in cols:
                logger.info("[DB] Migrating: adding channels.posts_per_day")
                cur.execute("ALTER TABLE channels ADD COLUMN posts_per_day FLOAT NOT NULL DEFAULT 0.0")
                con.commit()
            if "ad_reach_estimate" not in cols:
                logger.info("[DB] Migrating: adding channels.ad_reach_estimate")
                cur.execute("ALTER TABLE channels ADD COLUMN ad_reach_estimate INTEGER NOT NULL DEFAULT 0")
                con.commit()
            if "last_scanned_at" not in cols:
                logger.info("[DB] Migrating: adding channels.last_scanned_at")
                cur.execute("ALTER TABLE channels ADD COLUMN last_scanned_at DATETIME")
                con.commit()
            
            # --- Auto-Release Fix ---
            if "published_message_ids" not in cols:
                logger.info("[DB] Migrating: adding deals.published_message_ids")
                cur.execute("ALTER TABLE deals ADD COLUMN published_message_ids TEXT")
                con.commit()
            
            # --- REFANTORING v2 ---
            if "avg_views_per_post" not in cols:
                 logger.info("[DB] Migrating: adding channels.avg_views_per_post")
                 cur.execute("ALTER TABLE channels ADD COLUMN avg_views_per_post INTEGER NOT NULL DEFAULT 0")
                 con.commit()
            if "median_views" not in cols:
                 logger.info("[DB] Migrating: adding channels.median_views")
                 cur.execute("ALTER TABLE channels ADD COLUMN median_views INTEGER NOT NULL DEFAULT 0")
                 con.commit()
            if "median_er" not in cols:
                 logger.info("[DB] Migrating: adding channels.median_er")
                 cur.execute("ALTER TABLE channels ADD COLUMN median_er FLOAT NOT NULL DEFAULT 0.0")
                 con.commit()
            if "followers_trend_percent" not in cols:
                 logger.info("[DB] Migrating: adding channels.followers_trend_percent")
                 cur.execute("ALTER TABLE channels ADD COLUMN followers_trend_percent FLOAT NOT NULL DEFAULT 0.0")
                 con.commit()

            # --- Rich Analytics (Numerical) ---
            rich_cols = {
                "subs_today": "INTEGER NOT NULL DEFAULT 0",
                "subs_week": "INTEGER NOT NULL DEFAULT 0",
                "subs_month": "INTEGER NOT NULL DEFAULT 0",
                "joins_24h": "INTEGER NOT NULL DEFAULT 0",
                "leaves_24h": "INTEGER NOT NULL DEFAULT 0",
                "reach_12h": "INTEGER NOT NULL DEFAULT 0",
                "reach_24h": "INTEGER NOT NULL DEFAULT 0",
                "reach_48h": "INTEGER NOT NULL DEFAULT 0",
                "err_24h_percent": "FLOAT NOT NULL DEFAULT 0.0",
                "posts_total": "INTEGER NOT NULL DEFAULT 0",
                "posts_yesterday": "INTEGER NOT NULL DEFAULT 0",
                "posts_week": "INTEGER NOT NULL DEFAULT 0",
                "posts_month": "INTEGER NOT NULL DEFAULT 0",
                "channel_created_at": "DATETIME",
                "avg_forwards": "FLOAT NOT NULL DEFAULT 0.0",
                "avg_replies": "FLOAT NOT NULL DEFAULT 0.0",
                "avg_reactions": "FLOAT NOT NULL DEFAULT 0.0"
            }
            for col_name, col_def in rich_cols.items():
                if col_name not in cols:
                    logger.info(f"[DB] Migrating: adding channels.{col_name}")
                    cur.execute(f"ALTER TABLE channels ADD COLUMN {col_name} {col_def}")
                    con.commit()

        # channel_snapshots table
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='channel_snapshots'")
        if not cur.fetchone():
            logger.info("[DB] Migrating: creating channel_snapshots table")
            cur.execute("""
                CREATE TABLE channel_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id TEXT NOT NULL,
                    subscribers INTEGER NOT NULL,
                    avg_views_24h INTEGER NOT NULL,
                    avg_views_7d INTEGER NOT NULL,
                    languages TEXT,
                    premium_share FLOAT NOT NULL DEFAULT 0.0,
                    growth_7d FLOAT NOT NULL DEFAULT 0.0,
                    fetched_at DATETIME NOT NULL
                )
            """)
            cur.execute("CREATE INDEX idx_channel_snapshots_channel_id ON channel_snapshots(channel_id)")
            con.commit()
    except Exception as e:
        # Best-effort: don't block app startup in dev
        logger.error(f"[DB] Schema migration skipped: {type(e).__name__}: {e}")
    finally:
        try:
            con.close()
        except Exception:
            pass
