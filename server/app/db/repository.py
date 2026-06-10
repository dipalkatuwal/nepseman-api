"""
db/repository.py
----------------
Database access layer — all raw DB queries live here, not in routes.

Functions:
  - save_price_snapshot(db, prices)               → upsert today's prices (idempotent)
  - save_market_summary(db, summary)              → insert a summary row
  - get_snapshots(db, symbol, date, limit, offset) → paginated ORM query
  - get_latest_snapshot(db, symbol)               → most recent row for a symbol
  - get_snapshot_summary(db)                      → per-symbol stats via raw SQL
"""

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import desc, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import MarketSnapshot, MarketSummary

logger = logging.getLogger(__name__)


async def save_price_snapshot(
    db: AsyncSession,
    prices: list[dict[str, Any]],
    business_date: str | None = None,
) -> int:
    """
    Upsert a list of price dicts keyed on (symbol, business_date).
    Duplicate calls for the same trading day are silently ignored.
    Returns the number of rows processed.
    """
    if not prices:
        return 0

    now = datetime.now(timezone.utc)
    rows = []

    for p in prices:
        rows.append({
            "symbol":                p.get("symbol") or "",
            "security_name":         p.get("securityName"),
            "open_price":            p.get("openPrice"),
            "high_price":            p.get("highPrice"),
            "low_price":             p.get("lowPrice"),
            "closing_price":         p.get("closingPrice"),
            "previous_closing":      p.get("previousClosing"),
            "percentage_change":     p.get("percentageChange"),
            "total_traded_quantity": p.get("totalTradedQuantity"),
            "total_traded_value":    p.get("totalTradedValue"),
            "business_date":         business_date,
            "scraped_at":            now,
        })

    stmt = (
        pg_insert(MarketSnapshot)
        .values(rows)
        .on_conflict_do_nothing(constraint="uq_snapshot_symbol_date")
    )
    await db.execute(stmt)
    logger.info(f"💾  Upserted {len(rows)} price snapshots (date={business_date})")
    return len(rows)


async def save_market_summary(
    db: AsyncSession,
    summary: dict[str, Any],
) -> MarketSummary:
    """Insert one market summary row."""
    row = MarketSummary(
        nepse_index=summary.get("nepseIndex"),
        nepse_change=summary.get("nepseChange"),
        sensitive_index=summary.get("sensitiveIndex"),
        total_turnover=summary.get("totalTurnover"),
        total_traded_shares=summary.get("totalTradedShares"),
        total_transactions=summary.get("totalTransactions"),
        total_scrips=summary.get("totalScrips"),
        market_cap=summary.get("marketCap"),
        scraped_at=datetime.now(timezone.utc),
    )
    db.add(row)
    logger.info("💾  Persisted market summary")
    return row


async def get_snapshots(
    db: AsyncSession,
    symbol: str | None = None,
    business_date: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[MarketSnapshot]:
    """
    Query snapshots with optional filters.
    Supports pagination via limit/offset.
    """
    stmt = select(MarketSnapshot).order_by(desc(MarketSnapshot.scraped_at))

    if symbol:
        stmt = stmt.where(MarketSnapshot.symbol == symbol.upper())
    if business_date:
        stmt = stmt.where(MarketSnapshot.business_date == business_date)

    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_latest_snapshot(
    db: AsyncSession,
    symbol: str,
) -> MarketSnapshot | None:
    """Get the most recently scraped snapshot for a symbol."""
    stmt = (
        select(MarketSnapshot)
        .where(MarketSnapshot.symbol == symbol.upper())
        .order_by(desc(MarketSnapshot.scraped_at))
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_snapshot_summary(db: AsyncSession) -> list[dict]:
    """
    Return per-symbol stats using raw SQL:
    symbol, total_snapshots, latest_close, latest_date
    Ordered by latest_date DESC, then symbol ASC.
    """
    sql = text("""
        SELECT
            symbol,
            COUNT(*)                                          AS total_snapshots,
            closing_price FILTER (
                WHERE scraped_at = MAX(scraped_at) OVER (PARTITION BY symbol)
            )                                                 AS latest_close,
            MAX(business_date)                                AS latest_date
        FROM market_snapshots
        GROUP BY symbol, closing_price, scraped_at
        ORDER BY latest_date DESC NULLS LAST, symbol ASC
    """)
    # Simpler equivalent that avoids the window-function-in-aggregate issue:
    sql = text("""
        SELECT
            s.symbol,
            s.total_snapshots,
            ms.closing_price  AS latest_close,
            s.latest_date
        FROM (
            SELECT
                symbol,
                COUNT(*)           AS total_snapshots,
                MAX(business_date) AS latest_date,
                MAX(scraped_at)    AS latest_scraped_at
            FROM market_snapshots
            GROUP BY symbol
        ) s
        JOIN market_snapshots ms
          ON ms.symbol     = s.symbol
         AND ms.scraped_at = s.latest_scraped_at
        ORDER BY s.latest_date DESC NULLS LAST, s.symbol ASC
    """)
    result = await db.execute(sql)
    rows = result.mappings().all()
    return [dict(r) for r in rows]
