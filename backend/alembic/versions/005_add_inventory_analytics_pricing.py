"""add inventory items, client analytics, and pricing

Revision ID: 005
Revises: 004
Create Date: 2025-12-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '005'
down_revision: Union[str, None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create inventory_items table
    op.create_table(
        'inventory_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('subcategory', sa.String(), nullable=True),
        sa.Column('stock_quantity', sa.Integer(), nullable=True, default=0),
        sa.Column('min_stock_level', sa.Integer(), nullable=True, default=5),
        sa.Column('unit', sa.String(), nullable=True),
        sa.Column('unit_cost', sa.Integer(), nullable=True),
        sa.Column('location', sa.String(), nullable=True),
        sa.Column('supplier', sa.String(), nullable=True),
        sa.Column('sku', sa.String(), nullable=True),
        sa.Column('expiration_date', sa.DateTime(), nullable=True),
        sa.Column('last_restocked', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_inventory_items_id'), 'inventory_items', ['id'], unique=False)
    op.create_index(op.f('ix_inventory_items_name'), 'inventory_items', ['name'], unique=False)
    op.create_index(op.f('ix_inventory_items_category'), 'inventory_items', ['category'], unique=False)
    op.create_index(op.f('ix_inventory_items_sku'), 'inventory_items', ['sku'], unique=False)

    # Create client_analytics table
    op.create_table(
        'client_analytics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=True),
        sa.Column('total_appointments', sa.Integer(), nullable=True, default=0),
        sa.Column('completed_appointments', sa.Integer(), nullable=True, default=0),
        sa.Column('cancelled_appointments', sa.Integer(), nullable=True, default=0),
        sa.Column('no_show_count', sa.Integer(), nullable=True, default=0),
        sa.Column('last_visit_date', sa.DateTime(), nullable=True),
        sa.Column('first_visit_date', sa.DateTime(), nullable=True),
        sa.Column('total_spent', sa.Integer(), nullable=True, default=0),
        sa.Column('preferred_staff_id', sa.Integer(), nullable=True),
        sa.Column('average_booking_lead_time', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
        sa.ForeignKeyConstraint(['preferred_staff_id'], ['staff.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('client_id')
    )
    op.create_index(op.f('ix_client_analytics_id'), 'client_analytics', ['id'], unique=False)

    # Create services table for pricing
    op.create_table(
        'services',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('duration_minutes', sa.Integer(), nullable=True, default=30),
        sa.Column('base_price', sa.Integer(), nullable=False),  # Price in cents
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_services_id'), 'services', ['id'], unique=False)
    op.create_index(op.f('ix_services_name'), 'services', ['name'], unique=False)
    op.create_index(op.f('ix_services_category'), 'services', ['category'], unique=False)

    # Create email_campaigns table for outreach
    op.create_table(
        'email_campaigns',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('subject', sa.String(), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('campaign_type', sa.String(), nullable=True),  # reminder, promotion, follow_up, etc.
        sa.Column('status', sa.String(), nullable=True, default='draft'),  # draft, scheduled, sent
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('scheduled_for', sa.DateTime(), nullable=True),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('recipient_count', sa.Integer(), nullable=True, default=0),
        sa.ForeignKeyConstraint(['created_by'], ['staff.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_email_campaigns_id'), 'email_campaigns', ['id'], unique=False)

    # Create email_sends table to track individual sends
    op.create_table(
        'email_sends',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('campaign_id', sa.Integer(), nullable=True),
        sa.Column('client_id', sa.Integer(), nullable=True),
        sa.Column('email_address', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=True, default='pending'),  # pending, sent, delivered, opened, clicked, bounced
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('opened_at', sa.DateTime(), nullable=True),
        sa.Column('clicked_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['campaign_id'], ['email_campaigns.id'], ),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_email_sends_id'), 'email_sends', ['id'], unique=False)

    # Add service_id and price to bookings for revenue tracking
    op.add_column('bookings', sa.Column('service_id', sa.Integer(), nullable=True))
    op.add_column('bookings', sa.Column('price', sa.Integer(), nullable=True))  # Price in cents
    op.create_foreign_key('fk_bookings_service', 'bookings', 'services', ['service_id'], ['id'])


def downgrade() -> None:
    # Remove columns from bookings
    op.drop_constraint('fk_bookings_service', 'bookings', type_='foreignkey')
    op.drop_column('bookings', 'price')
    op.drop_column('bookings', 'service_id')

    # Drop email_sends table
    op.drop_index(op.f('ix_email_sends_id'), table_name='email_sends')
    op.drop_table('email_sends')

    # Drop email_campaigns table
    op.drop_index(op.f('ix_email_campaigns_id'), table_name='email_campaigns')
    op.drop_table('email_campaigns')

    # Drop services table
    op.drop_index(op.f('ix_services_category'), table_name='services')
    op.drop_index(op.f('ix_services_name'), table_name='services')
    op.drop_index(op.f('ix_services_id'), table_name='services')
    op.drop_table('services')

    # Drop client_analytics table
    op.drop_index(op.f('ix_client_analytics_id'), table_name='client_analytics')
    op.drop_table('client_analytics')

    # Drop inventory_items table
    op.drop_index(op.f('ix_inventory_items_sku'), table_name='inventory_items')
    op.drop_index(op.f('ix_inventory_items_category'), table_name='inventory_items')
    op.drop_index(op.f('ix_inventory_items_name'), table_name='inventory_items')
    op.drop_index(op.f('ix_inventory_items_id'), table_name='inventory_items')
    op.drop_table('inventory_items')
