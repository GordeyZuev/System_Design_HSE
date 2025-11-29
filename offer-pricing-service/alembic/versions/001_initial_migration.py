"""Initial migration - create offers and offer_audit tables

Revision ID: 001
Revises: 
Create Date: 2024-11-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum type for offer status
    # op.execute("CREATE TYPE offer_status AS ENUM ('ACTIVE', 'USED', 'EXPIRED', 'CANCELLED')")
    
    # Create offers table
    op.create_table(
        'offers',
        sa.Column('offer_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('station_id', sa.String(length=255), nullable=False),
        sa.Column('tariff_snapshot', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('status', sa.Enum('ACTIVE', 'USED', 'EXPIRED', 'CANCELLED', name='offer_status'), nullable=False),
        sa.Column('tariff_version', sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint('offer_id')
    )
    
    # Create indexes for offers table
    op.create_index('idx_offers_user_status', 'offers', ['user_id', 'status'])
    op.create_index('idx_offers_status_expires', 'offers', ['status', 'expires_at'])
    op.create_index(op.f('ix_offers_created_at'), 'offers', ['created_at'])
    op.create_index(op.f('ix_offers_expires_at'), 'offers', ['expires_at'])
    op.create_index(op.f('ix_offers_station_id'), 'offers', ['station_id'])
    op.create_index(op.f('ix_offers_status'), 'offers', ['status'])
    op.create_index(op.f('ix_offers_user_id'), 'offers', ['user_id'])
    
    # Create offer_audit table
    op.create_table(
        'offer_audit',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('offer_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('ts', sa.DateTime(), nullable=False),
        sa.Column('payload_json', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for offer_audit table
    op.create_index('idx_audit_offer_ts', 'offer_audit', ['offer_id', 'ts'])
    op.create_index(op.f('ix_offer_audit_offer_id'), 'offer_audit', ['offer_id'])
    op.create_index(op.f('ix_offer_audit_ts'), 'offer_audit', ['ts'])


def downgrade() -> None:
    # Drop offer_audit table
    op.drop_index(op.f('ix_offer_audit_ts'), table_name='offer_audit')
    op.drop_index(op.f('ix_offer_audit_offer_id'), table_name='offer_audit')
    op.drop_index('idx_audit_offer_ts', table_name='offer_audit')
    op.drop_table('offer_audit')
    
    # Drop offers table
    op.drop_index(op.f('ix_offers_user_id'), table_name='offers')
    op.drop_index(op.f('ix_offers_status'), table_name='offers')
    op.drop_index(op.f('ix_offers_station_id'), table_name='offers')
    op.drop_index(op.f('ix_offers_expires_at'), table_name='offers')
    op.drop_index(op.f('ix_offers_created_at'), table_name='offers')
    op.drop_index('idx_offers_status_expires', table_name='offers')
    op.drop_index('idx_offers_user_status', table_name='offers')
    op.drop_table('offers')
    
    # Drop enum type
    op.execute("DROP TYPE offer_status")

