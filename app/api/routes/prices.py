"""
prices.py
---------
Price endpoints — fetches live data from NEPSE and persists to PostgreSQL.
"""

import csv
import io
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.db import repository as repo
from app.db.database import get_db
from app.services import nepse as svc

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/prices", tags=["Prices"])


def _to_csv(data: list, filename: str) -> StreamingResponse:
    if not data:
        raise HTTPException(404, "No data available.")
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=data[0].keys())
    writer.writeheader()
    writer.writerows(data)
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/today")
async def today_price(
    business_date: Optional[str] = None,
    fmt: Optional[str] = None,
    persist: bool = Query(True, description="Save snapshot to PostgreSQL"),
):
    """
    Fetch today's prices from NEPSE.
    Pass persist=true (default) to save a snapshot to PostgreSQL.
    """
    try:
        data = await svc.get_today_price(business_date=business_date)

        if persist and data:
            try:
                async with get_db() as db:
                    await repo.save_price_snapshot(db, data, business_date=business_date)
            except Exception as db_err:
                # DB failure must never break the API response
                logger.warning(f"⚠️  DB persist failed (non-fatal): {db_err}")

        if fmt == "csv":
            return _to_csv(data, "today_price.csv")
        return data

    except Exception as e:
        raise HTTPException(502, str(e))


@router.get("/live")
async def live_market():
    try:
        return await svc.get_live_market()
    except Exception as e:
        raise HTTPException(502, str(e))


@router.get("/volume")
async def price_volume():
    try:
        return await svc.get_price_volume()
    except Exception as e:
        raise HTTPException(502, str(e))


@router.get("/top/gainers")
async def top_gainers():
    try:
        return await svc.get_top_gainers()
    except Exception as e:
        raise HTTPException(502, str(e))


@router.get("/top/losers")
async def top_losers():
    try:
        return await svc.get_top_losers()
    except Exception as e:
        raise HTTPException(502, str(e))


@router.get("/top/turnover")
async def top_turnover():
    try:
        return await svc.get_top_turnover()
    except Exception as e:
        raise HTTPException(502, str(e))


@router.get("/top/trade")
async def top_trade():
    try:
        return await svc.get_top_trade()
    except Exception as e:
        raise HTTPException(502, str(e))


@router.get("/top/transaction")
async def top_transaction():
    try:
        return await svc.get_top_transaction()
    except Exception as e:
        raise HTTPException(502, str(e))


# ── PostgreSQL query endpoints ────────────────────────────────────────────────

@router.get("/snapshots")
async def get_snapshots(
    symbol: Optional[str] = Query(None, description="Filter by stock symbol e.g. NABIL"),
    business_date: Optional[str] = Query(None, description="Filter by date e.g. 2025-06-09"),
    limit: int = Query(50, ge=1, le=500, description="Number of results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
):
    """
    Query persisted price snapshots from PostgreSQL.
    Supports filtering by symbol and/or date, with pagination.
    """
    try:
        async with get_db() as db:
            rows = await repo.get_snapshots(
                db,
                symbol=symbol,
                business_date=business_date,
                limit=limit,
                offset=offset,
            )
        return {
            "count": len(rows),
            "limit": limit,
            "offset": offset,
            "data": [
                {
                    "id": r.id,
                    "symbol": r.symbol,
                    "security_name": r.security_name,
                    "open_price": r.open_price,
                    "high_price": r.high_price,
                    "low_price": r.low_price,
                    "closing_price": r.closing_price,
                    "previous_closing": r.previous_closing,
                    "percentage_change": r.percentage_change,
                    "total_traded_quantity": r.total_traded_quantity,
                    "total_traded_value": r.total_traded_value,
                    "business_date": r.business_date,
                    "scraped_at": r.scraped_at.isoformat(),
                }
                for r in rows
            ],
        }
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/snapshots/{symbol}/latest")
async def get_latest_snapshot(symbol: str):
    """Get the most recently persisted snapshot for a symbol."""
    try:
        async with get_db() as db:
            row = await repo.get_latest_snapshot(db, symbol)
        if not row:
            raise HTTPException(404, f"No snapshot found for symbol '{symbol.upper()}'.")
        return {
            "symbol": row.symbol,
            "security_name": row.security_name,
            "closing_price": row.closing_price,
            "percentage_change": row.percentage_change,
            "business_date": row.business_date,
            "scraped_at": row.scraped_at.isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))
