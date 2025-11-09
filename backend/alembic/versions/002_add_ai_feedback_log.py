"""Add AI Feedback Log table

Revision ID: 002
Revises: 001
Create Date: 2025-11-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create ai_feedback_logs table
    op.create_table('ai_feedback_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('booking_id', sa.Integer(), nullable=True),
        sa.Column('staff_id', sa.Integer(), nullable=True),
        sa.Column('client_complaint_vector', Vector(384), nullable=True),
        sa.Column('staff_skills_vector', Vector(384), nullable=True),
        sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], ),
        sa.ForeignKeyConstraint(['staff_id'], ['staff.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_feedback_logs_id'), 'ai_feedback_logs', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_ai_feedback_logs_id'), table_name='ai_feedback_logs')
    op.drop_table('ai_feedback_logs')
