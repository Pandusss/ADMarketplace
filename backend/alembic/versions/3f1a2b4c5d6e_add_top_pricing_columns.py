"""add_top_pricing_columns

Revision ID: 3f1a2b4c5d6e
Revises: 2ebdccc3ebf8
Create Date: 2026-02-13 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3f1a2b4c5d6e'
down_revision: Union[str, None] = '0c7b2eb09204'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('channels', sa.Column('price_top_hour_ton', sa.Float(), nullable=False, server_default='0.0'))
    op.add_column('deals', sa.Column('top_duration_hours', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    op.drop_column('deals', 'top_duration_hours')
    op.drop_column('channels', 'price_top_hour_ton')
