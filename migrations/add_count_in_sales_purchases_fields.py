"""Add count_in_sales and count_in_purchases fields for all blocks

Revision ID: add_count_in_sales_purchases_fields
Revises: add_scam_and_internal_transfer_fields
Create Date: 2024-01-XX XX:XX:XX.XXXXXX

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_count_in_sales_purchases_fields'
down_revision = 'add_scam_and_internal_transfer_fields'
branch_labels = None
depends_on = None


def upgrade():
    # Добавляем поля для скама
    op.add_column('shift_report', sa.Column('scam_count_in_sales', sa.Boolean(), nullable=True, default=False))
    op.add_column('shift_report', sa.Column('scam_count_in_purchases', sa.Boolean(), nullable=True, default=False))
    
    # Добавляем поля для докидки
    op.add_column('shift_report', sa.Column('dokidka_count_in_sales', sa.Boolean(), nullable=True, default=False))
    op.add_column('shift_report', sa.Column('dokidka_count_in_purchases', sa.Boolean(), nullable=True, default=False))
    
    # Добавляем поля для внутреннего перевода
    op.add_column('shift_report', sa.Column('internal_transfer_count_in_sales', sa.Boolean(), nullable=True, default=False))
    op.add_column('shift_report', sa.Column('internal_transfer_count_in_purchases', sa.Boolean(), nullable=True, default=False))
    
    # Добавляем поля для апелляций
    op.add_column('shift_report', sa.Column('appeal_amount_rub', sa.Numeric(precision=15, scale=2), nullable=True, default=0))
    op.add_column('shift_report', sa.Column('appeal_platform', sa.String(length=20), nullable=True, default='bybit'))
    op.add_column('shift_report', sa.Column('appeal_account', sa.String(length=100), nullable=True, default=''))
    op.add_column('shift_report', sa.Column('appeal_count_in_sales', sa.Boolean(), nullable=True, default=False))
    op.add_column('shift_report', sa.Column('appeal_count_in_purchases', sa.Boolean(), nullable=True, default=False))


def downgrade():
    # Удаляем поля для скама
    op.drop_column('shift_report', 'scam_count_in_sales')
    op.drop_column('shift_report', 'scam_count_in_purchases')
    
    # Удаляем поля для докидки
    op.drop_column('shift_report', 'dokidka_count_in_sales')
    op.drop_column('shift_report', 'dokidka_count_in_purchases')
    
    # Удаляем поля для внутреннего перевода
    op.drop_column('shift_report', 'internal_transfer_count_in_sales')
    op.drop_column('shift_report', 'internal_transfer_count_in_purchases')
    
    # Удаляем поля для апелляций
    op.drop_column('shift_report', 'appeal_amount_rub')
    op.drop_column('shift_report', 'appeal_platform')
    op.drop_column('shift_report', 'appeal_account')
    op.drop_column('shift_report', 'appeal_count_in_sales')
    op.drop_column('shift_report', 'appeal_count_in_purchases') 