"""Add count_in_sales and count_in_purchases fields to order table

Revision ID: add_order_count_fields
Revises: add_count_in_sales_purchases_fields
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_order_count_fields'
down_revision = 'add_count_in_sales_purchases_fields'
branch_labels = None
depends_on = None


def upgrade():
    # Добавляем новые поля в таблицу order
    op.add_column('order', sa.Column('count_in_sales', sa.Boolean(), nullable=True, default=False))
    op.add_column('order', sa.Column('count_in_purchases', sa.Boolean(), nullable=True, default=False))


def downgrade():
    # Удаляем поля при откате
    op.drop_column('order', 'count_in_sales')
    op.drop_column('order', 'count_in_purchases') 