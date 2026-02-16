"""add reviews table and rating fields

Revision ID: 001_add_reviews
Revises:
Create Date: 2026-02-12
"""
from alembic import op
import sqlalchemy as sa

revision = "001_add_reviews"
down_revision = "000_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reviews",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("deal_id", sa.String(), nullable=False, index=True),
        sa.Column("reviewer_id", sa.String(), nullable=False, index=True),
        sa.Column("target_user_id", sa.String(), nullable=False, index=True),
        sa.Column("target_channel_id", sa.String(), nullable=True, index=True),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.add_column("users", sa.Column("rating_avg", sa.Float(), nullable=False, server_default="0"))
    op.add_column("users", sa.Column("rating_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("channels", sa.Column("rating_avg", sa.Float(), nullable=False, server_default="0"))
    op.add_column("channels", sa.Column("rating_count", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("channels", "rating_count")
    op.drop_column("channels", "rating_avg")
    op.drop_column("users", "rating_count")
    op.drop_column("users", "rating_avg")
    op.drop_table("reviews")
