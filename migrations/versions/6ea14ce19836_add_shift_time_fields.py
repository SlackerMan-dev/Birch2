"""add shift time fields

Revision ID: 6ea14ce19836
Revises: daae5e05aa18
Create Date: 2025-07-10 03:02:29.090374

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6ea14ce19836'
down_revision: Union[str, Sequence[str], None] = 'daae5e05aa18'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('account_balance_history', sa.Column('balance_type', sa.String(length=10), nullable=False))
    op.alter_column('employee', 'telegram',
               existing_type=sa.VARCHAR(length=100),
               nullable=True)
    op.alter_column('employee', 'salary_percent',
               existing_type=sa.NUMERIC(precision=5, scale=2),
               type_=sa.Float(),
               nullable=True)
    op.drop_index(op.f('ix_order_employee_id'), table_name='order')
    op.drop_index(op.f('ix_order_executed_at'), table_name='order')
    op.drop_index(op.f('ix_order_platform'), table_name='order')
    op.drop_index(op.f('ix_order_status'), table_name='order')
    op.add_column('shift_report', sa.Column('appeal_amount', sa.Numeric(precision=15, scale=2), nullable=True))
    op.add_column('shift_report', sa.Column('appeal_comment', sa.Text(), nullable=True))
    op.add_column('shift_report', sa.Column('shift_start_time', sa.DateTime(), nullable=True))
    op.add_column('shift_report', sa.Column('shift_end_time', sa.DateTime(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('shift_report', 'shift_end_time')
    op.drop_column('shift_report', 'shift_start_time')
    op.drop_column('shift_report', 'appeal_comment')
    op.drop_column('shift_report', 'appeal_amount')
    op.create_index(op.f('ix_order_status'), 'order', ['status'], unique=False)
    op.create_index(op.f('ix_order_platform'), 'order', ['platform'], unique=False)
    op.create_index(op.f('ix_order_executed_at'), 'order', ['executed_at'], unique=False)
    op.create_index(op.f('ix_order_employee_id'), 'order', ['employee_id'], unique=False)
    op.alter_column('employee', 'salary_percent',
               existing_type=sa.Float(),
               type_=sa.NUMERIC(precision=5, scale=2),
               nullable=False)
    op.alter_column('employee', 'telegram',
               existing_type=sa.VARCHAR(length=100),
               nullable=False)
    op.drop_column('account_balance_history', 'balance_type')
    # ### end Alembic commands ###
