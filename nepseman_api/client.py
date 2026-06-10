"""
client.py
---------
High-level async client for Nepal Stock Exchange (NEPSE).

Usage:
    from nepseman_api import NepseClient

    async with NepseClient() as nepse:
        status = await nepse.market_status()
        prices = await nepse.today_price()
        history = await nepse.price_history("NABIL")
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from nepseman_api.exceptions import NepseSymbolError
from nepseman_api.session import NepseSession, _GET, _POST

logger = logging.getLogger(__name__)

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


class NepseClient:
    """
    Async NEPSE client. Use as a context manager or call `await client.close()` when done.

    Args:
        base_url: Override the NEPSE base URL (default: https://www.nepalstock.com).

    Example:
        async with NepseClient() as nepse:
            print(await nepse.market_status())
    """

    def __init__(self, base_url: str = "https://www.nepalstock.com") -> None:
        self._session = NepseSession(base_url)
        self._symbol_map: Optional[Dict[str, int]] = None

    # ── context manager ────────────────────────────────────────────────────────

    async def __aenter__(self) -> "NepseClient":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    async def close(self) -> None:
        """Close the underlying HTTP session."""
        await self._session.aclose()

    # ── symbol resolution ──────────────────────────────────────────────────────

    async def _symbol_id(self, symbol: str) -> int:
        """Resolve ticker symbol → NEPSE security ID."""
        sym = symbol.upper()
        if self._symbol_map is None:
            await self._load_symbol_map()
        if sym not in self._symbol_map:
            self._symbol_map = None
            await self._load_symbol_map()
        if sym not in self._symbol_map:
            raise NepseSymbolError(
                f"Symbol '{sym}' not found. Call security_list() for valid symbols."
            )
        return self._symbol_map[sym]

    async def _load_symbol_map(self) -> None:
        data = await self._session.get(_GET["security_list"])
        items = data if isinstance(data, list) else (data or {}).get("content", [])
        self._symbol_map = {item["symbol"]: item["id"] for item in items}
        logger.info("Symbol map loaded: %d securities", len(self._symbol_map))

    # ── market status ──────────────────────────────────────────────────────────

    async def market_status(self) -> Dict[str, Any]:
        """Return raw market-open data (includes isOpen flag)."""
        return await self._session.get(_GET["market_open"])

    async def is_market_open(self) -> bool:
        """Return True if NEPSE is currently open."""
        data = await self.market_status()
        return bool(data) and data.get("isOpen", "CLOSE") == "OPEN"

    async def market_summary(self) -> Any:
        """Return today's market summary (turnover, transactions, index etc.)."""
        return await self._session.get(_GET["market_summary"])

    async def supply_demand(self) -> Any:
        """Return market-wide supply/demand data."""
        return await self._session.get(_GET["supply_demand"])

    # ── prices ─────────────────────────────────────────────────────────────────

    async def today_price(self, business_date: Optional[str] = None) -> List[Dict]:
        """
        Return today's OHLCV price list for all securities.

        Args:
            business_date: Optional date string "YYYY-MM-DD". Defaults to today.
        """
        params = {"size": "500"}
        if business_date:
            params["businessDate"] = business_date
        result = await self._session.post(
            _POST["today_price"], payload_type="floor", extra_params=params
        )
        if isinstance(result, dict):
            return result.get("content", result)
        return result or []

    async def live_market(self) -> Any:
        """Return live market ticker data (only available during trading hours)."""
        return await self._session.get(_GET["live_market"])

    async def price_volume(self) -> Any:
        """Return daily price/volume stats."""
        return await self._session.get(_GET["price_volume"])

    async def price_history(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        size: int = 500,
    ) -> List[Dict]:
        """
        Return OHLCV history for a single ticker.

        Args:
            symbol:     Ticker symbol e.g. "NABIL".
            start_date: "YYYY-MM-DD". Defaults to 1 year ago.
            end_date:   "YYYY-MM-DD". Defaults to today.
            size:       Max rows to return (default 500).

        Returns:
            List of dicts with date, open, high, low, close, volume etc.
        """
        sid   = await self._symbol_id(symbol)
        end   = end_date   or date.today().strftime("%Y-%m-%d")
        start = start_date or (date.today() - timedelta(days=365)).strftime("%Y-%m-%d")
        path  = _GET["price_volume_history"] + str(sid)
        result = await self._session.get(path, params={
            "size": str(size),
            "startDate": start,
            "endDate": end,
        })
        if isinstance(result, dict):
            return result.get("content", result)
        return result or []

    async def bulk_price_history(
        self,
        symbols: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        size: int = 500,
        concurrency: int = 5,
    ) -> Dict[str, Any]:
        """
        Fetch price history for multiple tickers in parallel.

        Args:
            symbols:     List of ticker symbols e.g. ["NABIL", "NICA", "ADBL"].
            concurrency: Max simultaneous requests (default 5).

        Returns:
            Dict mapping symbol → list of OHLCV dicts (or {"error": "..."} on failure).
        """
        sem = asyncio.Semaphore(concurrency)

        async def _fetch(sym: str):
            async with sem:
                try:
                    return sym.upper(), await self.price_history(sym, start_date, end_date, size)
                except Exception as exc:
                    return sym.upper(), {"error": str(exc)}

        results = await asyncio.gather(*[_fetch(s) for s in symbols])
        return dict(results)

    # ── market depth ───────────────────────────────────────────────────────────

    async def market_depth(self, symbol: str) -> Any:
        """
        Return bid/ask depth for a symbol.

        Only available during trading hours (Sun-Thu 11:00-15:00 NST).
        """
        sid = await self._symbol_id(symbol)
        result = await self._session.get(_GET["market_depth"] + str(sid) + "/")
        if result is None:
            return {
                "message": "Market is closed. Depth is only available Sun-Thu 11:00-15:00 NST."
            }
        return result

    # ── top lists ──────────────────────────────────────────────────────────────

    async def top_gainers(self) -> List[Dict]:
        """Return top gaining stocks."""
        return await self._session.get(_GET["top_gainers"]) or []

    async def top_losers(self) -> List[Dict]:
        """Return top losing stocks."""
        return await self._session.get(_GET["top_losers"]) or []

    async def top_turnover(self) -> List[Dict]:
        """Return top stocks by turnover."""
        return await self._session.get(_GET["top_turnover"]) or []

    async def top_trade(self) -> List[Dict]:
        """Return top traded stocks."""
        return await self._session.get(_GET["top_trade"]) or []

    async def top_transaction(self) -> List[Dict]:
        """Return top stocks by transaction count."""
        return await self._session.get(_GET["top_transaction"]) or []

    # ── indices ────────────────────────────────────────────────────────────────

    async def nepse_index(self) -> Any:
        """Return current NEPSE index value."""
        return await self._session.get(_GET["nepse_index"])

    async def nepse_subindices(self) -> Any:
        """Return all sector subindices."""
        return await self._session.get(_GET["nepse_subindices"])

    async def index_graph(self, index: str = "nepse") -> Any:
        """
        Return historical graph data for an index.

        Args:
            index: One of nepse, sensitive, float, sensitive_float, banking,
                   dev_bank, finance, hotel_tourism, hydro, investment,
                   life_insurance, manufacturing, microfinance, mutual_fund,
                   non_life_insurance, others, trading.
        """
        key = index.lower()
        if key not in _INDEX_GRAPH_MAP:
            raise ValueError(f"Unknown index '{index}'. Valid: {list(_INDEX_GRAPH_MAP)}")
        return await self._session.post(
            _POST[_INDEX_GRAPH_MAP[key]], payload_type="general"
        )

    # ── securities ─────────────────────────────────────────────────────────────

    async def company_list(self) -> List[Dict]:
        """Return list of all listed companies with sector info."""
        return await self._session.get(_GET["company_list"]) or []

    async def security_list(self) -> List[Dict]:
        """Return list of all securities (symbols, IDs)."""
        result = await self._session.get(_GET["security_list"])
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            return result.get("content", [])
        return []

    async def company_details(self, symbol: str) -> Any:
        """Return detailed info for a company by ticker symbol."""
        sid = await self._symbol_id(symbol)
        return await self._session.post(
            _POST["company_details"] + str(sid), payload_type="scrips"
        )

    async def daily_graph(self, symbol: str) -> Any:
        """Return intraday price graph data for a symbol."""
        sid = await self._symbol_id(symbol)
        return await self._session.post(
            _POST["company_daily_graph"] + str(sid), payload_type="scrips"
        )

    async def sector_scrips(self) -> Dict[str, List[str]]:
        """Return a dict mapping sector name → list of ticker symbols."""
        from collections import defaultdict
        companies = {c["symbol"]: c for c in await self.company_list()}
        result: Dict[str, List[str]] = defaultdict(list)
        for sec in await self.security_list():
            sym = sec["symbol"]
            sector = companies.get(sym, {}).get("sectorName", "Promoter Share")
            result[sector].append(sym)
        return dict(result)

    # ── floorsheet ─────────────────────────────────────────────────────────────

    async def floor_sheet(self, page: int = 0, size: int = 500) -> Any:
        """Return market-wide floorsheet (all trade records)."""
        result = await self._session.post(
            _POST["floor_sheet"],
            payload_type="floor",
            extra_params={"size": str(size), "sort": "contractId,desc", "page": str(page)},
        )
        if isinstance(result, dict) and "floorsheets" in result:
            return result["floorsheets"].get("content", result)
        return result or []

    async def floor_sheet_of(
        self,
        symbol: str,
        business_date: Optional[str] = None,
        size: int = 500,
    ) -> List[Dict]:
        """
        Return floorsheet records for a specific symbol.

        NEPSE does not expose a reliable per-symbol floorsheet endpoint.
        This method fetches the general floorsheet and filters client-side,
        which is the same approach the NEPSE website uses.

        Args:
            symbol:        Ticker symbol e.g. "NABIL".
            business_date: "YYYY-MM-DD". Defaults to today.
            size:          Max rows to fetch before filtering (default 500).
        """
        sym = symbol.upper()
        bd  = business_date or date.today().strftime("%Y-%m-%d")

        result = await self._session.post(
            _POST["floor_sheet"],
            payload_type="floor",
            extra_params={
                "businessDate": bd,
                "size": str(size),
                "sort": "contractid,desc",
            },
        )

        if not result:
            return []

        # unwrap envelope
        if isinstance(result, dict) and "floorsheets" in result:
            content = result["floorsheets"].get("content", [])
        elif isinstance(result, dict):
            content = result.get("content", [])
        else:
            content = result

        # filter by symbol client-side
        return [
            row for row in content
            if str(row.get("stockSymbol", "")).upper() == sym
        ]