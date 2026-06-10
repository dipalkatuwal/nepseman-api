"""
symbols.py
----------
Symbol validation with fuzzy suggestions.
Loaded lazily from the live security list; refreshed every 24h.
"""

import logging
import time

logger = logging.getLogger(__name__)

_symbols: set[str] = set()
_loaded_at: float = 0.0
_TTL = 86400  # 24 hours


def _needs_refresh() -> bool:
    return not _symbols or (time.monotonic() - _loaded_at) > _TTL


async def _refresh() -> None:
    global _symbols, _loaded_at
    try:
        # Import here to avoid circular imports
        from app.core.session import get_session
        session = await get_session()
        from nepseman_api.session import GET_ENDPOINTS
        data = await session.get(GET_ENDPOINTS["security_list"])
        if isinstance(data, list):
            _symbols = {item["symbol"].upper() for item in data}
        elif isinstance(data, dict):
            _symbols = {item["symbol"].upper() for item in data.get("content", [])}
        _loaded_at = time.monotonic()
        logger.info(f"Symbol map refreshed: {len(_symbols)} symbols loaded.")
    except Exception as e:
        logger.warning(f"Symbol refresh failed: {e}")


async def is_valid_symbol(symbol: str) -> bool:
    if _needs_refresh():
        await _refresh()
    return symbol.upper() in _symbols


async def get_suggestions(symbol: str, limit: int = 5) -> list[str]:
    """Return fuzzy symbol suggestions using simple prefix + substring matching."""
    if _needs_refresh():
        await _refresh()
    sym = symbol.upper()
    # Exact prefix matches first
    prefix = [s for s in _symbols if s.startswith(sym)]
    # Then substring matches
    substr = [s for s in _symbols if sym in s and s not in prefix]
    results = sorted(prefix) + sorted(substr)
    return results[:limit]


async def all_symbols() -> list[str]:
    if _needs_refresh():
        await _refresh()
    return sorted(_symbols)
