"""add_top_price_step_pct

Revision ID: 4a2b3c4d5e6f
Revises: 3f1a2b4c5d6e
Create Date: 2026-02-13 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4a2b3c4d5e6f'
down_revision: Union[str, None] = '3f1a2b4c5d6e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('channels', sa.Column('top_price_step_pct', sa.Float(), nullable=False, server_default='0.0'))


def downgrade() -> None:
    op.drop_column('channels', 'top_price_step_pct')
