"""
session.py
----------
Async authenticated HTTP session for nepalstock.com.
Uses httpx for ~3x faster requests vs requests library.
"""

import json
import logging
import time
from typing import Any, Dict, Optional

import httpx

from app.core.config import settings
from nepseman_api.auth import PayloadParser, TokenParser
from nepseman_api.session import GET_ENDPOINTS

logger = logging.getLogger(__name__)

_DEFAULT_HEADERS = {
    "User-Agent":      "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Accept":          "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection":      "keep-alive",
    "Pragma":          "no-cache",
    "Cache-Control":   "no-cache",
}


class NepseSession:
    BASE_URL = settings.NEPSE_BASE_URL
    TOKEN_TTL = 45  # seconds

    def __init__(self) -> None:
        self._token_parser = TokenParser()
        self._payload_parser = PayloadParser()

        self._access_token: Optional[str] = None
        self._token_details: Optional[Dict[str, Any]] = None
        self._market_open_id: Optional[int] = None
        self._token_timestamp: float = 0.0

        # Track last successful sync for health endpoint
        self.last_sync_at: Optional[float] = None

        # nepalstock.com.np serves an incomplete certificate chain that fails
        # SSL verification. verify=False bypasses this at the httpx level.
        self._client = httpx.AsyncClient(
            verify=False,
            headers={**_DEFAULT_HEADERS, "Referer": f"{self.BASE_URL}/"},
            timeout=httpx.Timeout(15.0, connect=5.0),
            transport=httpx.AsyncHTTPTransport(retries=3, verify=False),
    )

    # ── private helpers ────────────────────────────────────────────────────────

    async def _ensure_authenticated(self) -> None:
        token_age = time.time() - self._token_timestamp
        if self._access_token and token_age < self.TOKEN_TTL:
            return

        if self._access_token:
            logger.debug(f"Token expired after {token_age:.0f}s — re-authenticating.")

        logger.info("Authenticating with NEPSE...")
        url = self.BASE_URL + GET_ENDPOINTS["authenticate"]
        resp = await self._client.get(url)
        resp.raise_for_status()

        raw = resp.json()
        for i in range(1, 6):
            raw[f"salt{i}"] = int(raw[f"salt{i}"])

        self._access_token, _ = self._token_parser.parse_token_response(raw)
        self._token_details = raw
        self._token_timestamp = time.time()
        self._market_open_id = None
        self.last_sync_at = time.time()
        logger.info("Authentication successful.")

    async def _ensure_market_open_id(self) -> int:
        if self._market_open_id is not None:
            return self._market_open_id
        await self._ensure_authenticated()
        url = self.BASE_URL + GET_ENDPOINTS["market_open"]
        resp = await self._client.get(url, headers=self._auth_header())
        resp.raise_for_status()
        self._market_open_id = resp.json()["id"]
        logger.debug(f"market_open_id cached: {self._market_open_id}")
        return self._market_open_id

    def _auth_header(self) -> Dict[str, str]:
        return {
            "Authorization": f"Salter {self._access_token}",
            "Content-Type":  "application/json",
        }

    async def _compute_payload_id(self, which: str) -> int:
        given_id = await self._ensure_market_open_id()
        return self._payload_parser.calculate_payload_id(
            given_id=given_id,
            token_details=self._token_details,
            which=which,
        )

    # ── public interface ───────────────────────────────────────────────────────

    async def get(self, path: str, params: Optional[Dict] = None) -> Any:
        """Authenticated async GET. Returns parsed JSON or None."""
        await self._ensure_authenticated()
        url = self.BASE_URL + path
        resp = await self._client.get(url, headers=self._auth_header(), params=params)
        resp.raise_for_status()
        if not resp.content or not resp.text.strip():
            return None
        self.last_sync_at = time.time()
        return resp.json()

    async def post(
        self,
        path: str,
        payload: Optional[Dict] = None,
        params: Optional[Dict] = None,
        payload_type: Optional[str] = None,
        which: Optional[str] = None,
        extra_params: Optional[Dict] = None,
    ) -> Any:
        """Authenticated async POST. Returns parsed JSON or None."""
        await self._ensure_authenticated()
        url = self.BASE_URL + path

        _type_map = {"scrips": "stock-live", "floor": "sector-live", "general": "general"}
        resolved_which = _type_map.get(payload_type or "", which or "general")

        if payload is None:
            payload = {"id": await self._compute_payload_id(resolved_which)}

        merged_params: Dict = {}
        if params:
            merged_params.update(params)
        if extra_params:
            merged_params.update(extra_params)

        post_headers = {
        **self._auth_header(),
        "Referer": "https://www.nepalstock.com/floor-sheet",
        "Content-Type": "application/json",
        }

        resp = await self._client.post(
            url,
            content=json.dumps(payload),
            headers=post_headers,
            params=merged_params or None,
        )
        resp.raise_for_status()
        if not resp.content or not resp.text.strip():
            return None
        self.last_sync_at = time.time()
        return resp.json()

    async def invalidate(self) -> None:
        self._access_token = None
        self._token_details = None
        self._market_open_id = None
        self._token_timestamp = 0.0
        logger.info("Session invalidated — will re-authenticate on next request.")

    async def aclose(self) -> None:
        await self._client.aclose()


# ── singleton ──────────────────────────────────────────────────────────────────

_session: Optional[NepseSession] = None


async def get_session() -> NepseSession:
    global _session
    if _session is None:
        _session = NepseSession()
    return _session
