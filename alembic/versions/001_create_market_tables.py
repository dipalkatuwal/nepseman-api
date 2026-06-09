"""create market_snapshots and market_summaries tables

Revision ID: 001
Revises: 
Create Date: 2025-06-09 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── market_snapshots ────────────────────────────────────────────────────
    op.create_table(
        "market_snapshots",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("security_name", sa.Text(), nullable=True),
        sa.Column("open_price", sa.Float(), nullable=True),
        sa.Column("high_price", sa.Float(), nullable=True),
        sa.Column("low_price", sa.Float(), nullable=True),
        sa.Column("closing_price", sa.Float(), nullable=True),
        sa.Column("previous_closing", sa.Float(), nullable=True),
        sa.Column("percentage_change", sa.Float(), nullable=True),
        sa.Column("total_traded_quantity", sa.Float(), nullable=True),
        sa.Column("total_traded_value", sa.Float(), nullable=True),
        sa.Column("business_date", sa.String(20), nullable=True),
        sa.Column("scraped_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_snapshots_symbol", "market_snapshots", ["symbol"])
    op.create_index("ix_snapshots_business_date", "market_snapshots", ["business_date"])
    op.create_index("ix_snapshots_scraped_at", "market_snapshots", ["scraped_at"])
    op.create_index(
        "ix_snapshots_symbol_date",
        "market_snapshots",
        ["symbol", "business_date"],
    )

    # ── market_summaries ────────────────────────────────────────────────────
    op.create_table(
        "market_summaries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("nepse_index", sa.Float(), nullable=True),
        sa.Column("nepse_change", sa.Float(), nullable=True),
        sa.Column("sensitive_index", sa.Float(), nullable=True),
        sa.Column("total_turnover", sa.Float(), nullable=True),
        sa.Column("total_traded_shares", sa.Float(), nullable=True),
        sa.Column("total_transactions", sa.Integer(), nullable=True),
        sa.Column("total_scrips", sa.Integer(), nullable=True),
        sa.Column("market_cap", sa.Float(), nullable=True),
        sa.Column("scraped_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_summaries_scraped_at", "market_summaries", ["scraped_at"])


def downgrade() -> None:
    op.drop_table("market_snapshots")
    op.drop_table("market_summaries")
