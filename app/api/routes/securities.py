import csv
import io
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.core import symbols as sym
from app.services import nepse as svc

router = APIRouter(prefix="/securities", tags=["Securities"])


def _to_csv(data: list, filename: str) -> StreamingResponse:
    if not data or not isinstance(data[0], dict):
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


# ── static routes first ───────────────────────────────────────────────────────

@router.get("/companies")
async def company_list():
    try:
        return await svc.get_company_list()
    except Exception as e:
        raise HTTPException(502, str(e))


@router.get("/list")
async def security_list(fmt: Optional[str] = None):
    try:
        data = await svc.get_security_list()
        if fmt == "csv":
            return _to_csv(data, "securities.csv")
        return data
    except Exception as e:
        raise HTTPException(502, str(e))


@router.get("/sectors")
async def sector_scrips():
    try:
        return await svc.get_sector_scrips()
    except Exception as e:
        raise HTTPException(502, str(e))


# ── symbol validation ─────────────────────────────────────────────────────────

@router.get("/validate/{symbol}")
async def validate_symbol(symbol: str):
    valid = await sym.is_valid_symbol(symbol)
    suggestions = [] if valid else await sym.get_suggestions(symbol)
    return {
        "symbol":      symbol.upper(),
        "is_valid":    valid,
        "suggestions": suggestions,
    }


# ── symbol sub-routes ─────────────────────────────────────────────────────────

@router.get("/{symbol}/graph")
async def daily_scrip_graph(symbol: str):
    try:
        return await svc.get_daily_scrip_graph(symbol)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(502, str(e))


@router.get("/{symbol}/history")
async def price_history(
    symbol: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    size: int = 500,
    fmt: Optional[str] = None,
):
    try:
        data = await svc.get_price_history(symbol, start_date, end_date, size)
        if fmt == "csv":
            return _to_csv(data if isinstance(data, list) else [], f"{symbol}_history.csv")
        return data
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(502, str(e))


@router.get("/{symbol}/depth")
async def market_depth(symbol: str):
    try:
        return await svc.get_market_depth(symbol)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(502, str(e))


# ── catch-all ─────────────────────────────────────────────────────────────────

@router.get("/{symbol}")
async def company_details(symbol: str):
    try:
        return await svc.get_company_details(symbol)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(502, str(e))


# ── bulk history ──────────────────────────────────────────────────────────────

@router.get("/history/bulk")
async def bulk_price_history(
    symbols: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    size: int = 500,
    fmt: Optional[str] = None,
    concurrency: int = 5,
):
    """
    Fetch OHLCV history for multiple tickers in one call.

    **symbols**: comma-separated tickers e.g. `NABIL,NICA,SCB,SHIFL`
    **fmt**: `json` (default) or `csv` (long-format, all tickers in one file)

    Returns parallel-fetched results — much faster than sequential calls.
    Failed tickers include an `"error"` key instead of records.

    Example: `/api/v1/securities/history/bulk?symbols=NABIL,NICA,SCB&start_date=2024-01-01`
    """
    import csv
    import io

    symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    if not symbol_list:
        raise HTTPException(400, "Provide at least one symbol.")
    if len(symbol_list) > 50:
        raise HTTPException(400, "Maximum 50 symbols per request.")

    try:
        data = await svc.get_bulk_price_history(
            symbol_list,
            start_date=start_date,
            end_date=end_date,
            size=size,
            concurrency=min(concurrency, 10),
        )
    except Exception as e:
        raise HTTPException(502, str(e))

    if fmt != "csv":
        return data

    # ── CSV: long format — symbol column prepended ────────────────────────────
    rows = []
    for ticker, records in data.items():
        if isinstance(records, list):
            for r in records:
                rows.append({"symbol": ticker, **r})

    if not rows:
        raise HTTPException(404, "No data returned for any symbol.")

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
    output.seek(0)

    filename = f"bulk_history_{'_'.join(symbol_list[:5])}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
