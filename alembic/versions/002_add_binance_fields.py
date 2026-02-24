"""Add Binance fields to Position table

Revision ID: 002_add_binance_fields
Revises: 001_initial_schema
Create Date: 2025-01-XX

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_add_binance_fields'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add Binance-specific fields to positions table"""
    # Add new columns to positions table
    op.add_column('positions', sa.Column('leverage', sa.Integer(), server_default='1', nullable=False))
    op.add_column('positions', sa.Column('margin_type', sa.String(10), server_default='CROSSED', nullable=False))
    op.add_column('positions', sa.Column('liquidation_price', sa.Float(), nullable=True))


def downgrade() -> None:
    """Remove Binance-specific fields from positions table"""
    op.drop_column('positions', 'liquidation_price')
    op.drop_column('positions', 'margin_type')
    op.drop_column('positions', 'leverage')
