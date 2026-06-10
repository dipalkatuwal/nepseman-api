"""
session.py
----------
Async authenticated HTTP session for nepalstock.com.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, Optional

import httpx

from nepseman_api.auth import PayloadParser, TokenParser
from nepseman_api.exceptions import NepseAuthError, NepseRequestError

logger = logging.getLogger(__name__)

_GET = {
    "authenticate":          "/api/authenticate/prove",
    "market_open":           "/api/nots/nepse-data/market-open",
    "market_summary":        "/api/nots/market-summary/",
    "supply_demand":         "/api/nots/nepse-data/supplydemand",
    "top_gainers":           "/api/nots/top-ten/top-gainer",
    "top_losers":            "/api/nots/top-ten/top-loser",
    "top_turnover":          "/api/nots/top-ten/turnover",
    "top_trade":             "/api/nots/top-ten/trade",
    "top_transaction":       "/api/nots/top-ten/transaction",
    "nepse_index":           "/api/nots/nepse-index",
    "nepse_subindices":      "/api/nots",
    "live_market":           "/api/nots/lives-market",
    "company_list":          "/api/nots/company/list",
    "security_list":         "/api/nots/security?nonDelisted=true",
    "price_volume":          "/api/nots/securityDailyTradeStat/58",
    "price_volume_history":  "/api/nots/market/history/security/",
    "market_depth":          "/api/nots/nepse-data/marketdepth/",
}

_POST = {
    "today_price":         "/api/nots/nepse-data/today-price",
    "floor_sheet":         "/api/nots/nepse-data/floorsheet",
    "company_details":     "/api/nots/security/",
    "company_daily_graph": "/api/nots/market/graphdata/daily/",
    "company_floorsheet":  "/api/nots/security/floorsheet/",
    "nepse_index_graph":              "/api/nots/graph/index/58",
    "sensitive_index_graph":          "/api/nots/graph/index/57",
    "float_index_graph":              "/api/nots/graph/index/62",
    "sensitive_float_index_graph":    "/api/nots/graph/index/63",
    "banking_subindex_graph":         "/api/nots/graph/index/51",
    "dev_bank_subindex_graph":        "/api/nots/graph/index/55",
    "finance_subindex_graph":         "/api/nots/graph/index/60",
    "hotel_tourism_subindex_graph":   "/api/nots/graph/index/52",
    "hydro_subindex_graph":           "/api/nots/graph/index/54",
    "investment_subindex_graph":      "/api/nots/graph/index/67",
    "life_insurance_subindex_graph":  "/api/nots/graph/index/65",
    "manufacturing_subindex_graph":   "/api/nots/graph/index/56",
    "microfinance_subindex_graph":    "/api/nots/graph/index/64",
    "mutual_fund_subindex_graph":     "/api/nots/graph/index/66",
    "non_life_insurance_subindex_graph": "/api/nots/graph/index/59",
    "others_subindex_graph":          "/api/nots/graph/index/53",
    "trading_subindex_graph":         "/api/nots/graph/index/61",
}

_TYPE_MAP = {"scrips": "stock-live", "floor": "sector-live", "general": "general"}

_HEADERS = {
    "User-Agent":      "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Accept":          "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection":      "keep-alive",
    "Pragma":          "no-cache",
    "Cache-Control":   "no-cache",
}

BASE_URL = "https://www.nepalstock.com"
TOKEN_TTL = 45  # seconds


class NepseSession:
    """Low-level authenticated async session. Use NepseClient instead."""

    def __init__(self, base_url: str = BASE_URL) -> None:
        self._base = base_url.rstrip("/")
        self._token_parser = TokenParser()
        self._payload_parser = PayloadParser()

        self._access_token: Optional[str] = None
        self._token_details: Optional[Dict[str, Any]] = None
        self._market_open_id: Optional[int] = None
        self._token_ts: float = 0.0

        self._client = httpx.AsyncClient(
            verify=False,
            headers={**_HEADERS, "Referer": f"{self._base}/"},
            timeout=httpx.Timeout(15.0, connect=5.0),
            transport=httpx.AsyncHTTPTransport(retries=3, verify=False),
        )

    # ── internals ──────────────────────────────────────────────────────────────

    async def _authenticate(self) -> None:
        if self._access_token and (time.time() - self._token_ts) < TOKEN_TTL:
            return
        try:
            resp = await self._client.get(self._base + _GET["authenticate"])
            resp.raise_for_status()
            raw = resp.json()
            for i in range(1, 6):
                raw[f"salt{i}"] = int(raw[f"salt{i}"])
            self._access_token, _ = self._token_parser.parse_token_response(raw)
            self._token_details = raw
            self._token_ts = time.time()
            self._market_open_id = None
            logger.info("NEPSE auth OK")
        except Exception as exc:
            raise NepseAuthError(f"Authentication failed: {exc}") from exc

    async def _market_id(self) -> int:
        if self._market_open_id is not None:
            return self._market_open_id
        await self._authenticate()
        resp = await self._client.get(
            self._base + _GET["market_open"], headers=self._headers()
        )
        resp.raise_for_status()
        self._market_open_id = resp.json()["id"]
        return self._market_open_id

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Salter {self._access_token}", "Content-Type": "application/json"}

    async def _payload_id(self, which: str) -> int:
        return self._payload_parser.calculate_payload_id(
            await self._market_id(), self._token_details, which
        )

    # ── public ─────────────────────────────────────────────────────────────────

    async def get(self, path: str, params: Optional[Dict] = None) -> Any:
        await self._authenticate()
        try:
            resp = await self._client.get(
                self._base + path, headers=self._headers(), params=params
            )
            resp.raise_for_status()
            return resp.json() if resp.content and resp.text.strip() else None
        except NepseAuthError:
            raise
        except Exception as exc:
            raise NepseRequestError(str(exc)) from exc

    async def post(
        self,
        path: str,
        payload_type: str = "general",
        extra_params: Optional[Dict] = None,
    ) -> Any:
        await self._authenticate()
        which = _TYPE_MAP.get(payload_type, "general")
        payload = {"id": await self._payload_id(which)}
        try:
            resp = await self._client.post(
                self._base + path,
                content=json.dumps(payload),
                headers=self._headers(),
                params=extra_params or None,
            )
            resp.raise_for_status()
            return resp.json() if resp.content and resp.text.strip() else None
        except NepseAuthError:
            raise
        except Exception as exc:
            raise NepseRequestError(str(exc)) from exc

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "NepseSession":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.aclose()

    # ── endpoint constants (exposed for advanced use) ──────────────────────────
    GET_ENDPOINTS = _GET
    POST_ENDPOINTS = _POST


# ── module-level aliases (importable directly) ─────────────────────────────────
GET_ENDPOINTS = _GET
POST_ENDPOINTS = _POST
