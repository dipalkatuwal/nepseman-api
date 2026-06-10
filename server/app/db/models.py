"""
db/models.py
------------
SQLAlchemy ORM models for PostgreSQL persistence.

Tables:
  - market_snapshots  : daily price snapshots for each stock
  - market_summaries  : daily NEPSE index summary
"""

from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class MarketSnapshot(Base):
    """
    One row per (symbol, scraped_at) — captures the state of a stock
    each time /prices/today is fetched and persisted.
    """

    __tablename__ = "market_snapshots"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Stock identity
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    security_name: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Price fields
    open_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    high_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    low_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    closing_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    previous_closing: Mapped[float | None] = mapped_column(Float, nullable=True)
    percentage_change: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Volume / value
    total_traded_quantity: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_traded_value: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Business date from NEPSE (e.g. "2025-06-09")
    business_date: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)

    # When we scraped it
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_now,
        index=True,
    )

    # Composite index for fast symbol + date queries
    __table_args__ = (
        Index("ix_snapshots_symbol_date", "symbol", "business_date"),
    )

    def __repr__(self) -> str:
        return f"<MarketSnapshot {self.symbol} @ {self.business_date} close={self.closing_price}>"


class MarketSummary(Base):
    """
    One row per scrape of the daily NEPSE market summary.
    """

    __tablename__ = "market_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    nepse_index: Mapped[float | None] = mapped_column(Float, nullable=True)
    nepse_change: Mapped[float | None] = mapped_column(Float, nullable=True)
    sensitive_index: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_turnover: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_traded_shares: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_transactions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_scrips: Mapped[int | None] = mapped_column(Integer, nullable=True)
    market_cap: Mapped[float | None] = mapped_column(Float, nullable=True)

    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_now,
        index=True,
    )

    def __repr__(self) -> str:
        return f"<MarketSummary nepse={self.nepse_index} @ {self.scraped_at}>"
