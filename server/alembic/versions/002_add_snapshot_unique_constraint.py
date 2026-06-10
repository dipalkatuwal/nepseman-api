"""add unique constraint on (symbol, business_date) to market_snapshots

Revision ID: 002
Revises: 001
Create Date: 2025-06-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE market_snapshots
            ADD CONSTRAINT uq_snapshot_symbol_date UNIQUE (symbol, business_date)
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE market_snapshots
            DROP CONSTRAINT uq_snapshot_symbol_date
        """
    )
