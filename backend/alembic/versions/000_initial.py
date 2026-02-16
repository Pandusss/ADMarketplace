"""initial schema — create all base tables

Revision ID: 000_initial
Revises: (none)
Create Date: 2026-02-11
"""
from alembic import op
import sqlalchemy as sa

revision = "000_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── users ─────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=True, unique=True),
        sa.Column("telegram_username", sa.String(), nullable=True),
        sa.Column("wallet_address", sa.String(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # ── channels ──────────────────────────────────────────────
    op.create_table(
        "channels",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("owner_id", sa.String(), nullable=True),
        sa.Column("avatar_file_id", sa.String(), nullable=True),
        sa.Column("telegram_channel_id", sa.String(), nullable=True, unique=True),
        sa.Column("title", sa.String(), nullable=False, server_default=""),
        sa.Column("handle", sa.String(), nullable=False, server_default=""),
        sa.Column("description", sa.String(), nullable=False, server_default=""),
        sa.Column("subscribers_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_views", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_views_per_post", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_views_24h", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_views_7d", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("premium_share", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("followers_trend_percent", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("growth_7d", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("last_stats_update", sa.DateTime(), nullable=True),
        sa.Column("engagement_rate", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("median_er", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("posts_per_day", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("ad_reach_estimate", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("median_views", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("stability_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("last_scanned_at", sa.DateTime(), nullable=True),
        sa.Column("premium_subscribers_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("region_stats", sa.JSON(), nullable=True),
        sa.Column("subs_today", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("subs_week", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("subs_month", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("joins_24h", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("leaves_24h", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reach_12h", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reach_24h", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reach_48h", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("err_24h_percent", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("posts_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("posts_yesterday", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("posts_week", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("posts_month", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("channel_created_at", sa.DateTime(), nullable=True),
        sa.Column("avg_forwards", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("avg_replies", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("avg_reactions", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("verified_stats", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("category", sa.String(), nullable=False, server_default="Crypto"),
        sa.Column("language", sa.String(), nullable=False, server_default="EN"),
        sa.Column("price_per_post_ton", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("wallet_address", sa.String(), nullable=False, server_default=""),
        sa.Column("posting_timezone", sa.String(), nullable=False, server_default="UTC"),
        sa.Column("posting_window_start", sa.String(), nullable=False, server_default="10:00"),
        sa.Column("posting_window_end", sa.String(), nullable=False, server_default="20:00"),
        sa.Column("posting_slot_minutes", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("verified_at", sa.DateTime(), nullable=True),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_channels_owner_id", "channels", ["owner_id"])
    op.create_index("ix_channels_telegram_channel_id", "channels", ["telegram_channel_id"])

    # ── channel_members ───────────────────────────────────────
    op.create_table(
        "channel_members",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("channel_id", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_channel_members_user_id", "channel_members", ["user_id"])
    op.create_index("ix_channel_members_channel_id", "channel_members", ["channel_id"])

    # ── channel_offers ────────────────────────────────────────
    op.create_table(
        "channel_offers",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("channel_id", sa.String(), nullable=False),
        sa.Column("advertiser_id", sa.String(), nullable=False),
        sa.Column("applicant_id", sa.String(), nullable=False),
        sa.Column("offer_price_ton", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("message", sa.String(), nullable=False, server_default=""),
        sa.Column("campaign_brief", sa.String(), nullable=False, server_default=""),
        sa.Column("creative_mode", sa.String(), nullable=False, server_default="template"),
        sa.Column("creative_instructions", sa.String(), nullable=True),
        sa.Column("template_id", sa.String(), nullable=True),
        sa.Column("preferred_publish_at", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("post_duration_hours", sa.Integer(), nullable=False, server_default="24"),
        sa.Column("deal_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_channel_offers_channel_id", "channel_offers", ["channel_id"])
    op.create_index("ix_channel_offers_advertiser_id", "channel_offers", ["advertiser_id"])
    op.create_index("ix_channel_offers_applicant_id", "channel_offers", ["applicant_id"])
    op.create_index("ix_channel_offers_deal_id", "channel_offers", ["deal_id"])

    # ── channel_posts ─────────────────────────────────────────
    op.create_table(
        "channel_posts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("channel_id", sa.String(), sa.ForeignKey("channels.id"), nullable=False),
        sa.Column("post_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.DateTime(), nullable=False),
        sa.Column("views", sa.Integer(), server_default="0"),
        sa.Column("forwards", sa.Integer(), server_default="0"),
        sa.Column("replies", sa.Integer(), server_default="0"),
        sa.Column("reactions", sa.Text(), server_default="{}"),
        sa.Column("content_type", sa.String(), server_default="other"),
        sa.Column("has_links", sa.Boolean(), server_default="false"),
        sa.Column("grouped_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_channel_posts_id", "channel_posts", ["id"])
    op.create_index("ix_channel_posts_channel_id", "channel_posts", ["channel_id"])
    op.create_index("ix_channel_posts_date", "channel_posts", ["date"])
    op.create_index("ix_channel_posts_grouped_id", "channel_posts", ["grouped_id"])

    # ── channel_snapshots ─────────────────────────────────────
    op.create_table(
        "channel_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("channel_id", sa.String(), nullable=False),
        sa.Column("subscribers", sa.Integer(), nullable=False),
        sa.Column("avg_views_24h", sa.Integer(), nullable=False),
        sa.Column("avg_views_7d", sa.Integer(), nullable=False),
        sa.Column("languages", sa.JSON(), nullable=True),
        sa.Column("premium_share", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("growth_7d", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("stability_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("premium_subscribers_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("region_stats", sa.JSON(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_channel_snapshots_channel_id", "channel_snapshots", ["channel_id"])

    # ── channel_verifications ─────────────────────────────────
    op.create_table(
        "channel_verifications",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("token", sa.String(), nullable=False, unique=True),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("telegram_channel_id", sa.String(), nullable=True),
        sa.Column("channel_username", sa.String(), nullable=True),
        sa.Column("channel_title", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("verified_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_channel_verifications_user_id", "channel_verifications", ["user_id"])
    op.create_index("ix_channel_verifications_telegram_user_id", "channel_verifications", ["telegram_user_id"])
    op.create_index("ix_channel_verifications_token", "channel_verifications", ["token"])
    op.create_index("ix_channel_verifications_telegram_channel_id", "channel_verifications", ["telegram_channel_id"])

    # ── campaigns ─────────────────────────────────────────────
    op.create_table(
        "campaigns",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("owner_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False, server_default=""),
        sa.Column("brief", sa.String(), nullable=False, server_default=""),
        sa.Column("category", sa.String(), nullable=False, server_default=""),
        sa.Column("language", sa.String(), nullable=False, server_default=""),
        sa.Column("budget_ton", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("desired_views_24h", sa.Integer(), nullable=True),
        sa.Column("template_id", sa.String(), nullable=False, server_default=""),
        sa.Column("creative_mode", sa.String(), nullable=False, server_default="template"),
        sa.Column("creative_instructions", sa.String(), nullable=True),
        sa.Column("post_duration_hours", sa.Integer(), nullable=False, server_default="24"),
        sa.Column("status", sa.String(), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_campaigns_owner_id", "campaigns", ["owner_id"])

    # ── campaign_offers ───────────────────────────────────────
    op.create_table(
        "campaign_offers",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("campaign_id", sa.String(), nullable=False),
        sa.Column("channel_id", sa.String(), nullable=False),
        sa.Column("applicant_id", sa.String(), nullable=False),
        sa.Column("offer_price_ton", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("message", sa.String(), nullable=False, server_default=""),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("creative_mode", sa.String(), nullable=True),
        sa.Column("creative_instructions", sa.String(), nullable=True),
        sa.Column("deal_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_campaign_offers_campaign_id", "campaign_offers", ["campaign_id"])
    op.create_index("ix_campaign_offers_channel_id", "campaign_offers", ["channel_id"])
    op.create_index("ix_campaign_offers_applicant_id", "campaign_offers", ["applicant_id"])

    # ── deals ─────────────────────────────────────────────────
    op.create_table(
        "deals",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("channel_id", sa.String(), nullable=False),
        sa.Column("advertiser_id", sa.String(), nullable=False),
        sa.Column("emoji", sa.String(), nullable=False, server_default=""),
        sa.Column("status", sa.String(), nullable=False, server_default="negotiation"),
        sa.Column("ad_format", sa.String(), nullable=False, server_default="post"),
        sa.Column("price_ton", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("negotiation_confirmed_by_advertiser", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("negotiation_confirmed_by_channel", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("deal_confirmed_by_advertiser", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("deal_confirmed_by_channel", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("deal_confirmed_at", sa.String(), nullable=True),
        sa.Column("auto_release_hours", sa.Integer(), nullable=True),
        sa.Column("post_duration_hours", sa.Integer(), nullable=True),
        sa.Column("campaign_brief", sa.String(), nullable=False, server_default=""),
        sa.Column("creative_mode", sa.String(), nullable=False, server_default="template"),
        sa.Column("creative_instructions", sa.String(), nullable=True),
        sa.Column("preferred_publish_at", sa.String(), nullable=True),
        sa.Column("creative_text", sa.String(), nullable=False, server_default=""),
        sa.Column("scheduled_at", sa.String(), nullable=True),
        sa.Column("creative_chat_id", sa.String(), nullable=True),
        sa.Column("creative_message_ids", sa.String(), nullable=True),
        sa.Column("creative_type", sa.String(), nullable=True),
        sa.Column("waiting_for_creative", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("creative_preview_text", sa.String(), nullable=True),
        sa.Column("creative_preview_file_id", sa.String(), nullable=True),
        sa.Column("creative_preview_file_ids", sa.String(), nullable=True),
        sa.Column("creative_preview_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("published_channel_id", sa.String(), nullable=True),
        sa.Column("published_message_ids", sa.String(), nullable=True),
        sa.Column("published_at", sa.String(), nullable=True),
        sa.Column("escrow_wallet_id", sa.String(), nullable=True),
        sa.Column("escrow_address", sa.String(), nullable=True),
        sa.Column("escrow_network", sa.String(), nullable=True),
        sa.Column("expected_amount_ton", sa.String(), nullable=True),
        sa.Column("payment_confirmed_at", sa.String(), nullable=True),
        sa.Column("payment_tx_hash", sa.String(), nullable=True),
        sa.Column("release_tx_hash", sa.String(), nullable=True),
        sa.Column("released_at", sa.String(), nullable=True),
        sa.Column("refund_tx_hash", sa.String(), nullable=True),
        sa.Column("refunded_at", sa.String(), nullable=True),
        sa.Column("seller_wallet", sa.String(), nullable=True),
        sa.Column("cancelled_by", sa.String(), nullable=True),
        sa.Column("cancelled_at", sa.String(), nullable=True),
        sa.Column("post_not_found", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_deals_channel_id", "deals", ["channel_id"])
    op.create_index("ix_deals_advertiser_id", "deals", ["advertiser_id"])

    # ── payments ──────────────────────────────────────────────
    op.create_table(
        "payments",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("deal_id", sa.String(), nullable=False),
        sa.Column("amount_usdt", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(), nullable=False, server_default="unpaid"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("paid_at", sa.String(), nullable=True),
    )
    op.create_index("ix_payments_deal_id", "payments", ["deal_id"])

    # ── chat_messages ─────────────────────────────────────────
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("deal_id", sa.String(), nullable=False),
        sa.Column("sender_id", sa.String(), nullable=False),
        sa.Column("message_id", sa.Integer(), nullable=False),
        sa.Column("content_text", sa.Text(), nullable=True),
        sa.Column("content_type", sa.String(), nullable=False, server_default="text"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_chat_messages_id", "chat_messages", ["id"])
    op.create_index("ix_chat_messages_deal_id", "chat_messages", ["deal_id"])

    # ── chat_unread_counts ────────────────────────────────────
    op.create_table(
        "chat_unread_counts",
        sa.Column("user_id", sa.String(), primary_key=True),
        sa.Column("deal_id", sa.String(), primary_key=True),
        sa.Column("unread_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cross_chat_notified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("last_read_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # ── post_templates ────────────────────────────────────────
    op.create_table(
        "post_templates",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("owner_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False, server_default=""),
        sa.Column("creative_chat_id", sa.String(), nullable=True),
        sa.Column("creative_message_ids", sa.String(), nullable=True),
        sa.Column("creative_type", sa.String(), nullable=True),
        sa.Column("preview_text", sa.String(), nullable=False, server_default=""),
        sa.Column("preview_file_id", sa.String(), nullable=False, server_default=""),
        sa.Column("preview_file_ids", sa.String(), nullable=False, server_default=""),
        sa.Column("preview_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("waiting_for_content", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_post_templates_owner_id", "post_templates", ["owner_id"])

    # ── telegram_update_state ─────────────────────────────────
    op.create_table(
        "telegram_update_state",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("last_update_id", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # ── user_chat_contexts ────────────────────────────────────
    op.create_table(
        "user_chat_contexts",
        sa.Column("user_id", sa.String(), primary_key=True),
        sa.Column("deal_id", sa.String(), nullable=False),
        sa.Column("input_mode", sa.String(), nullable=False, server_default="chat"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("user_chat_contexts")
    op.drop_table("telegram_update_state")
    op.drop_table("post_templates")
    op.drop_table("chat_unread_counts")
    op.drop_table("chat_messages")
    op.drop_table("payments")
    op.drop_table("deals")
    op.drop_table("campaign_offers")
    op.drop_table("campaigns")
    op.drop_table("channel_verifications")
    op.drop_table("channel_snapshots")
    op.drop_table("channel_posts")
    op.drop_table("channel_offers")
    op.drop_table("channel_members")
    op.drop_table("channels")
    op.drop_table("users")
