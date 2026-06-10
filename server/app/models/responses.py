"""
models/responses.py
-------------------
Pydantic models for API responses AND the unified response envelope helpers.

All routes return:
  {"success": true,  "data": <payload>, "error": null}
  {"success": false, "data": null,       "error": "message"}
"""

from typing import Any, Optional

from fastapi.responses import JSONResponse
from pydantic import BaseModel

# ── Envelope helpers ──────────────────────────────────────────────────────────

def ok(data: Any) -> JSONResponse:
    """Wrap a successful payload in the standard envelope."""
    return JSONResponse({"success": True, "data": data, "error": None})


def err(msg: str, status: int = 400) -> JSONResponse:
    """Wrap an error message in the standard envelope."""
    return JSONResponse({"success": False, "data": None, "error": msg}, status_code=status)


# ── Pydantic models (unchanged) ───────────────────────────────────────────────

class MarketStatus(BaseModel):
    is_open: bool


class MarketSummary(BaseModel):
    totalTurnover:     Optional[float] = None
    totalTradedShares: Optional[float] = None
    totalTransactions: Optional[int]   = None
    totalScrips:       Optional[int]   = None
    marketCap:         Optional[float] = None
    sensitiveIndex:    Optional[float] = None
    nepseIndex:        Optional[float] = None
    nepseChange:       Optional[float] = None

    class Config:
        extra = "allow"


class StockPrice(BaseModel):
    symbol:           Optional[str]   = None
    securityName:     Optional[str]   = None
    openPrice:        Optional[float] = None
    highPrice:        Optional[float] = None
    lowPrice:         Optional[float] = None
    closingPrice:     Optional[float] = None
    totalTradedQuantity: Optional[float] = None
    totalTradedValue:    Optional[float] = None
    previousClosing:     Optional[float] = None
    percentageChange:    Optional[float] = None

    class Config:
        extra = "allow"


class TickerInfo(BaseModel):
    symbol:       Optional[str]   = None
    securityName: Optional[str]   = None
    lastTradedPrice: Optional[float] = None
    percentageChange: Optional[float] = None
    openPrice:    Optional[float] = None
    highPrice:    Optional[float] = None
    lowPrice:     Optional[float] = None
    volume:       Optional[float] = None
    previousClose: Optional[float] = None

    class Config:
        extra = "allow"


class NepseIndex(BaseModel):
    index:        Optional[str]   = None
    currentValue: Optional[float] = None
    change:       Optional[float] = None
    percentChange: Optional[float] = None

    class Config:
        extra = "allow"


class GenericResponse(BaseModel):
    data: Any
