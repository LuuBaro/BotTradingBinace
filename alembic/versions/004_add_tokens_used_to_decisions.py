"""Add tokens_used field to Decision table

Revision ID: 004_add_tokens_used_to_decisions
Revises: 003_add_cascade_delete
Create Date: 2026-03-04

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '004_add_tokens_used_to_decisions'
down_revision: Union[str, None] = '003_add_cascade_delete'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add tokens_used column to decisions table for actual LLM token tracking"""
    op.add_column('decisions', sa.Column('tokens_used', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Remove tokens_used column from decisions table"""
    op.drop_column('decisions', 'tokens_used')
