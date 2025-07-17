"""Add dokidka fields to shift_report table

Revision ID: add_dokidka_fields
Revises: update_salary_settings_profit_based
Create Date: 2025-07-16 17:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_dokidka_fields'
down_revision = 'update_salary_settings_profit_based'
branch_labels = None
depends_on = None

def upgrade():
    # Добавляем новые поля для докидок
    op.add_column('shift_report', sa.Column('dokidka_amount_rub', sa.Numeric(15, 2), nullable=True, default=0))
    op.add_column('shift_report', sa.Column('dokidka_platform', sa.String(20), nullable=True, default='bybit'))
    op.add_column('shift_report', sa.Column('dokidka_account', sa.String(100), nullable=True, default=''))

def downgrade():
    # Удаляем добавленные поля
    op.drop_column('shift_report', 'dokidka_amount_rub')
    op.drop_column('shift_report', 'dokidka_platform')
    op.drop_column('shift_report', 'dokidka_account') 