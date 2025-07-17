"""Add department field to shift_report table

Revision ID: add_department_field
Revises: add_count_in_sales_purchases_fields
Create Date: 2025-01-27 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_department_field'
down_revision = '5d3cfa67f6cd'
branch_labels = None
depends_on = None


def upgrade():
    # Добавляем поле department для указания отдела
    op.add_column('shift_report', sa.Column('department', sa.String(20), nullable=False, default='first'))


def downgrade():
    # Удаляем поле department
    op.drop_column('shift_report', 'department') 