"""
models/responses.py
-------------------
Pydantic models for API responses.
All fields are Optional so partial NEPSE responses don't crash deserialization.
"""

from typing import Any, Optional

from pydantic import BaseModel


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
