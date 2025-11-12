"""add surgery inventory link

Revision ID: 004
Revises: 003
Create Date: 2025-11-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create surgery_inventory_links table
    op.create_table(
        'surgery_inventory_links',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('surgery_type', sa.String(), nullable=True),
        sa.Column('medication_id', sa.Integer(), nullable=True),
        sa.Column('required_quantity', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['medication_id'], ['medications.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_surgery_inventory_links_id'), 'surgery_inventory_links', ['id'], unique=False)
    op.create_index(op.f('ix_surgery_inventory_links_surgery_type'), 'surgery_inventory_links', ['surgery_type'], unique=False)


def downgrade() -> None:
    # Drop surgery_inventory_links table
    op.drop_index(op.f('ix_surgery_inventory_links_surgery_type'), table_name='surgery_inventory_links')
    op.drop_index(op.f('ix_surgery_inventory_links_id'), table_name='surgery_inventory_links')
    op.drop_table('surgery_inventory_links')
