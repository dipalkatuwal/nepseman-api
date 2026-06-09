"""
services/nepse.py
-----------------
All NEPSE data functions — fully async, with TTL caching.

Cache TTLs:
  Live data  (prices, depth, floorsheet) → 30s
  Index data (indices, subindices)        → 60s
  Stable data (company list, security)   → 600s (10 min)
"""

import logging
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from app.core.cache import cache
from app.core.config import settings
from app.core.endpoints import GET_ENDPOINTS, POST_ENDPOINTS
from app.core.session import get_session

logger = logging.getLogger(__name__)

LIVE  = settings.CACHE_TTL_LIVE      # 30s
IDX   = 60                            # 60s
STABLE = settings.CACHE_TTL_DEFAULT  # 600s


# ── symbol → id resolution ─────────────────────────────────────────────────────

_symbol_map: Optional[Dict[str, int]] = None


async def _get_symbol_map() -> Dict[str, int]:
    global _symbol_map
    if _symbol_map is not None:
        return _symbol_map
    try:
        session = await get_session()
        data = await session.get(GET_ENDPOINTS["security_list"])
        if isinstance(data, list):
            _symbol_map = {item["symbol"]: item["id"] for item in data}
        elif isinstance(data, dict):
            items = data.get("content", [])
            _symbol_map = {item["symbol"]: item["id"] for item in items}
        else:
            _symbol_map = {}
        logger.info(f"Symbol map loaded: {len(_symbol_map)} securities")
    except Exception as e:
        logger.error(f"Failed to load symbol map: {e}")
        _symbol_map = {}
    return _symbol_map


async def _resolve(symbol: str) -> int:
    """Resolve a ticker symbol to its NEPSE security ID."""
    global _symbol_map
    sym = symbol.upper()
    smap = await _get_symbol_map()
    if sym not in smap:
        _symbol_map = None
        smap = await _get_symbol_map()
    if sym not in smap:
        raise ValueError(
            f"Symbol '{sym}' not found. "
            f"Hit /api/v1/securities/list for valid symbols."
        )
    return smap[sym]


# ── market status ──────────────────────────────────────────────────────────────

@cache.ttl(seconds=LIVE)
async def is_market_open() -> bool:
    session = await get_session()
    data = await session.get(GET_ENDPOINTS["market_open"])
    return bool(data) and data.get("isOpen", "CLOSE") == "OPEN"


@cache.ttl(seconds=LIVE)
async def get_market_status() -> Dict[str, Any]:
    session = await get_session()
    return await session.get(GET_ENDPOINTS["market_open"])


# ── market summary ─────────────────────────────────────────────────────────────

@cache.ttl(seconds=IDX)
async def get_market_summary() -> Any:
    session = await get_session()
    return await session.get(GET_ENDPOINTS["market_summary"])


@cache.ttl(seconds=LIVE)
async def get_supply_demand() -> Any:
    session = await get_session()
    return await session.get(GET_ENDPOINTS["supply_demand"])


# ── prices ─────────────────────────────────────────────────────────────────────

@cache.ttl(seconds=LIVE)
async def get_today_price(business_date: Optional[str] = None) -> List[Dict]:
    params = {"size": "500"}
    if business_date:
        params["businessDate"] = business_date
    session = await get_session()
    result = await session.post(
        POST_ENDPOINTS["today_price"],
        payload_type="floor",
        extra_params=params,
    )
    if isinstance(result, dict):
        return result.get("content", result)
    return result or []


@cache.ttl(seconds=LIVE)
async def get_price_volume() -> Any:
    session = await get_session()
    return await session.get(GET_ENDPOINTS["price_volume"])


@cache.ttl(seconds=LIVE)
async def get_live_market() -> Any:
    session = await get_session()
    return await session.get(GET_ENDPOINTS["live_market"])


@cache.ttl(seconds=LIVE)
async def get_supply_demand_prices() -> Any:
    session = await get_session()
    return await session.get(GET_ENDPOINTS["supply_demand"])


# ── top lists ──────────────────────────────────────────────────────────────────

@cache.ttl(seconds=LIVE)
async def get_top_gainers() -> List[Dict]:
    session = await get_session()
    return await session.get(GET_ENDPOINTS["top_gainers"]) or []

@cache.ttl(seconds=LIVE)
async def get_top_losers() -> List[Dict]:
    session = await get_session()
    return await session.get(GET_ENDPOINTS["top_losers"]) or []

@cache.ttl(seconds=LIVE)
async def get_top_turnover() -> List[Dict]:
    session = await get_session()
    return await session.get(GET_ENDPOINTS["top_turnover"]) or []

@cache.ttl(seconds=LIVE)
async def get_top_trade() -> List[Dict]:
    session = await get_session()
    return await session.get(GET_ENDPOINTS["top_trade"]) or []

@cache.ttl(seconds=LIVE)
async def get_top_transaction() -> List[Dict]:
    session = await get_session()
    return await session.get(GET_ENDPOINTS["top_transaction"]) or []


# ── indices ────────────────────────────────────────────────────────────────────

@cache.ttl(seconds=IDX)
async def get_nepse_index() -> Any:
    session = await get_session()
    return await session.get(GET_ENDPOINTS["nepse_index"])

@cache.ttl(seconds=IDX)
async def get_nepse_subindices() -> Any:
    session = await get_session()
    return await session.get(GET_ENDPOINTS["nepse_subindices"])


_INDEX_GRAPH_MAP = {
    "nepse":              "nepse_index_graph",
    "sensitive":          "sensitive_index_graph",
    "float":              "float_index_graph",
    "sensitive_float":    "sensitive_float_index_graph",
    "banking":            "banking_subindex_graph",
    "dev_bank":           "dev_bank_subindex_graph",
    "finance":            "finance_subindex_graph",
    "hotel_tourism":      "hotel_tourism_subindex_graph",
    "hydro":              "hydro_subindex_graph",
    "investment":         "investment_subindex_graph",
    "life_insurance":     "life_insurance_subindex_graph",
    "manufacturing":      "manufacturing_subindex_graph",
    "microfinance":       "microfinance_subindex_graph",
    "mutual_fund":        "mutual_fund_subindex_graph",
    "non_life_insurance": "non_life_insurance_subindex_graph",
    "others":             "others_subindex_graph",
    "trading":            "trading_subindex_graph",
}


@cache.ttl(seconds=IDX)
async def get_index_graph(index_name: str = "nepse") -> Any:
    key = index_name.lower()
    if key not in _INDEX_GRAPH_MAP:
        raise ValueError(f"Unknown index '{index_name}'. Valid: {list(_INDEX_GRAPH_MAP)}")
    session = await get_session()
    return await session.post(POST_ENDPOINTS[_INDEX_GRAPH_MAP[key]], payload_type="general")


# ── securities / companies ─────────────────────────────────────────────────────

@cache.ttl(seconds=STABLE)
async def get_company_list() -> List[Dict]:
    session = await get_session()
    return await session.get(GET_ENDPOINTS["company_list"]) or []

@cache.ttl(seconds=STABLE)
async def get_security_list() -> List[Dict]:
    session = await get_session()
    result = await session.get(GET_ENDPOINTS["security_list"])
    if isinstance(result, list):
        return result
    if isinstance(result, dict):
        return result.get("content", [])
    return []


@cache.ttl(seconds=STABLE)
async def get_sector_scrips() -> Dict[str, List[str]]:
    from collections import defaultdict
    company_map = {c["symbol"]: c for c in await get_company_list()}
    result: Dict[str, List[str]] = defaultdict(list)
    for sec in await get_security_list():
        sym = sec["symbol"]
        if sym in company_map:
            sector = company_map[sym].get("sectorName", "Unknown")
            result[sector].append(sym)
        else:
            result["Promoter Share"].append(sym)
    return dict(result)


@cache.ttl(seconds=LIVE)
async def get_company_details(symbol: str) -> Any:
    sid = await _resolve(symbol)
    session = await get_session()
    return await session.post(
        POST_ENDPOINTS["company_details"] + str(sid),
        payload_type="scrips",
    )


@cache.ttl(seconds=LIVE)
async def get_daily_scrip_graph(symbol: str) -> Any:
    sid = await _resolve(symbol)
    session = await get_session()
    return await session.post(
        POST_ENDPOINTS["company_daily_graph"] + str(sid),
        payload_type="scrips",
    )


@cache.ttl(seconds=STABLE)
async def get_price_history(
    symbol: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    size: int = 500,
) -> Any:
    sid = await _resolve(symbol)
    end   = end_date   or date.today().strftime("%Y-%m-%d")
    start = start_date or (date.today() - timedelta(days=365)).strftime("%Y-%m-%d")
    path  = GET_ENDPOINTS["price_volume_history"] + str(sid)
    session = await get_session()
    result = await session.get(path, params={
        "size": str(size),
        "startDate": start,
        "endDate": end,
    })
    if isinstance(result, dict):
        return result.get("content", result)
    return result or []


@cache.ttl(seconds=LIVE)
async def get_market_depth(symbol: str) -> Any:
    sid = await _resolve(symbol)
    path = GET_ENDPOINTS["market_depth"] + str(sid) + "/"
    session = await get_session()
    result = await session.get(path)
    if result is None:
        return {
            "message": "Market is closed. Market depth is only available during trading hours (Sun-Thu 11:00-15:00 NST)."
        }
    return result


# ── floorsheet ─────────────────────────────────────────────────────────────────

@cache.ttl(seconds=LIVE)
async def get_floor_sheet(page: int = 0, size: int = 500) -> Any:
    session = await get_session()
    result = await session.post(
        POST_ENDPOINTS["floor_sheet"],
        payload_type="floor",
        extra_params={"size": str(size), "sort": "contractId,desc", "page": str(page)},
    )
    if isinstance(result, dict) and "floorsheets" in result:
        return result["floorsheets"].get("content", result)
    return result or []


@cache.ttl(seconds=LIVE)
async def get_floor_sheet_of(symbol: str, business_date: Optional[str] = None, size: int = 500) -> Any:
    sid = await _resolve(symbol)
    bd  = business_date or date.today().strftime("%Y-%m-%d")
    path = POST_ENDPOINTS["company_floorsheet"] + str(sid)
    session = await get_session()
    result = await session.post(
        path,
        payload_type="floor",
        extra_params={"businessDate": bd, "size": str(size), "sort": "contractid,desc"},
    )
    if isinstance(result, dict) and "floorsheets" in result:
        return result["floorsheets"].get("content", result)
    return result or []


# ── bulk history ───────────────────────────────────────────────────────────────

async def get_bulk_price_history(
    symbols: list[str],
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    size: int = 500,
    concurrency: int = 5,
) -> dict[str, Any]:
    """
    Fetch OHLCV history for multiple tickers in parallel.

    Uses a semaphore to cap concurrent requests (default 5) so we
    don't hammer nepalstock.com. Failed tickers return {"error": "..."}.

    Returns:
        {
          "NABIL": [ {date, open, high, low, close, volume}, ... ],
          "NICA":  [ ... ],
          "SCB":   {"error": "Symbol 'SCB' not found."},
        }
    """
    import asyncio

    sem = asyncio.Semaphore(concurrency)

    async def _fetch_one(sym: str) -> tuple[str, Any]:
        async with sem:
            try:
                data = await get_price_history(sym, start_date, end_date, size)
                return sym.upper(), data
            except Exception as e:
                return sym.upper(), {"error": str(e)}

    results = await asyncio.gather(*[_fetch_one(s) for s in symbols])
    return dict(results)
