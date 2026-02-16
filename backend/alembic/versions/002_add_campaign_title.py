"""add campaign_title to channel_offers and deals"""
from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001_add_reviews"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("channel_offers", sa.Column("campaign_title", sa.String(), nullable=False, server_default=""))
    op.add_column("deals", sa.Column("campaign_title", sa.String(), nullable=False, server_default=""))

def downgrade():
    op.drop_column("channel_offers", "campaign_title")
    op.drop_column("deals", "campaign_title")
