"""add bybit btc file field

Revision ID: add_bybit_btc_file
Revises: 6ea14ce19836
Create Date: 2025-01-27 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_bybit_btc_file'
down_revision: Union[str, Sequence[str], None] = '6ea14ce19836'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Добавляем поле для файла выгрузки Bybit BTC
    op.add_column('shift_report', sa.Column('bybit_btc_file', sa.String(length=255), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Удаляем поле для файла выгрузки Bybit BTC
    op.drop_column('shift_report', 'bybit_btc_file') 