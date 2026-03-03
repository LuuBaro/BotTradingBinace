"""make positions unique per user

Revision ID: 003_multi_tenant_position_unique
Revises: 002_add_binance_fields
Create Date: 2026-03-03
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "003_multi_tenant_position_unique"
down_revision = "002_add_binance_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Use batch mode for SQLite compatibility
    with op.batch_alter_table("positions", schema=None) as batch_op:
        # Drop legacy global unique constraint/index on symbol if present
        try:
            batch_op.drop_constraint("ix_positions_symbol", type_="unique")
        except Exception:
            pass
        try:
            batch_op.drop_constraint("uq_positions_symbol", type_="unique")
        except Exception:
            pass
        try:
            batch_op.drop_index("ix_positions_symbol")
        except Exception:
            pass

        batch_op.create_index("ix_positions_symbol", ["symbol"], unique=False)
        batch_op.create_unique_constraint(
            "uq_positions_user_symbol", ["user_id", "symbol"]
        )


def downgrade() -> None:
    with op.batch_alter_table("positions", schema=None) as batch_op:
        try:
            batch_op.drop_constraint("uq_positions_user_symbol", type_="unique")
        except Exception:
            pass
        try:
            batch_op.drop_index("ix_positions_symbol")
        except Exception:
            pass
        batch_op.create_unique_constraint("uq_positions_symbol", ["symbol"])
        batch_op.create_index("ix_positions_symbol", ["symbol"], unique=True)
