"""Add scam and internal transfer fields to ShiftReport

Revision ID: add_scam_and_internal_transfer_fields
Revises: update_salary_settings_profit_based
Create Date: 2024-01-XX XX:XX:XX.XXXXXX

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_scam_and_internal_transfer_fields'
down_revision = 'update_salary_settings_profit_based'
branch_labels = None
depends_on = None


def upgrade():
    # Добавляем новые поля для скама
    op.add_column('shift_report', sa.Column('scam_amount_rub', sa.Numeric(precision=15, scale=2), nullable=True, default=0))
    op.add_column('shift_report', sa.Column('scam_platform', sa.String(length=20), nullable=True, default='bybit'))
    op.add_column('shift_report', sa.Column('scam_account', sa.String(length=100), nullable=True, default=''))
    
    # Добавляем новые поля для внутреннего перевода
    op.add_column('shift_report', sa.Column('internal_transfer_amount_rub', sa.Numeric(precision=15, scale=2), nullable=True, default=0))
    op.add_column('shift_report', sa.Column('internal_transfer_platform', sa.String(length=20), nullable=True, default='bybit'))
    op.add_column('shift_report', sa.Column('internal_transfer_account', sa.String(length=100), nullable=True, default=''))


def downgrade():
    # Удаляем поля для скама
    op.drop_column('shift_report', 'scam_amount_rub')
    op.drop_column('shift_report', 'scam_platform')
    op.drop_column('shift_report', 'scam_account')
    
    # Удаляем поля для внутреннего перевода
    op.drop_column('shift_report', 'internal_transfer_amount_rub')
    op.drop_column('shift_report', 'internal_transfer_platform')
    op.drop_column('shift_report', 'internal_transfer_account') 