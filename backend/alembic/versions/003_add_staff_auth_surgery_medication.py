"""Add staff auth and surgery medication tables

Revision ID: 003
Revises: 002
Create Date: 2025-11-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add email and hashed_password columns to staff table
    op.add_column('staff', sa.Column('email', sa.String(), nullable=True))
    op.add_column('staff', sa.Column('hashed_password', sa.String(), nullable=True))
    op.create_index(op.f('ix_staff_email'), 'staff', ['email'], unique=True)
    
    # Create surgeries table
    op.create_table(
        'surgeries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('pet_id', sa.Integer(), nullable=False),
        sa.Column('staff_id', sa.Integer(), nullable=False),
        sa.Column('surgery_type', sa.String(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('start_time', sa.DateTime(), nullable=False),
        sa.Column('end_time', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['pet_id'], ['pets.id'], ),
        sa.ForeignKeyConstraint(['staff_id'], ['staff.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_surgeries_id'), 'surgeries', ['id'], unique=False)
    op.create_index(op.f('ix_surgeries_status'), 'surgeries', ['status'], unique=False)
    
    # Create medications table
    op.create_table(
        'medications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('stock_quantity', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('unit', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_medications_id'), 'medications', ['id'], unique=False)
    op.create_index(op.f('ix_medications_name'), 'medications', ['name'], unique=False)


def downgrade() -> None:
    # Drop medications table
    op.drop_index(op.f('ix_medications_name'), table_name='medications')
    op.drop_index(op.f('ix_medications_id'), table_name='medications')
    op.drop_table('medications')
    
    # Drop surgeries table
    op.drop_index(op.f('ix_surgeries_status'), table_name='surgeries')
    op.drop_index(op.f('ix_surgeries_id'), table_name='surgeries')
    op.drop_table('surgeries')
    
    # Remove email and hashed_password from staff table
    op.drop_index(op.f('ix_staff_email'), table_name='staff')
    op.drop_column('staff', 'hashed_password')
    op.drop_column('staff', 'email')
