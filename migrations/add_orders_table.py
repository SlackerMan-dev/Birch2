"""Миграция для добавления таблицы ордеров"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = 'add_orders_table'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Создаем таблицу orders
    op.create_table('order',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.String(length=100), nullable=False),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('platform', sa.String(length=20), nullable=False),
        sa.Column('account_name', sa.String(length=100), nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('side', sa.String(length=10), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=15, scale=8), nullable=False),
        sa.Column('price', sa.Numeric(precision=15, scale=8), nullable=False),
        sa.Column('total_usdt', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('fees_usdt', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('executed_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['employee_id'], ['employee.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('order_id')
    )
    
    # Создаем индексы для оптимизации
    op.create_index(op.f('ix_order_employee_id'), 'order', ['employee_id'], unique=False)
    op.create_index(op.f('ix_order_platform'), 'order', ['platform'], unique=False)
    op.create_index(op.f('ix_order_status'), 'order', ['status'], unique=False)
    op.create_index(op.f('ix_order_executed_at'), 'order', ['executed_at'], unique=False)

def downgrade():
    # Удаляем индексы
    op.drop_index(op.f('ix_order_executed_at'), table_name='order')
    op.drop_index(op.f('ix_order_status'), table_name='order')
    op.drop_index(op.f('ix_order_platform'), table_name='order')
    op.drop_index(op.f('ix_order_employee_id'), table_name='order')
    
    # Удаляем таблицу
    op.drop_table('order') 