"""
tests/test_api.py
-----------------
Unit / integration tests for all REST routes.

Strategy
--------
- All tests use FastAPI's TestClient (synchronous, no real event loop needed).
- The entire ``app.services.nepse`` module is patched via unittest.mock so
  no Nepal IP, no WASM execution, and no network access is required.
- Each test group mirrors one router prefix.

Run:
    pytest tests/test_api.py -v
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

# ---------------------------------------------------------------------------
# Shared sample payloads
# ---------------------------------------------------------------------------

SAMPLE_SECURITY_LIST = [
    {"id": 1, "symbol": "NABIL", "name": "Nabil Bank"},
    {"id": 2, "symbol": "NICA",  "name": "NIC Asia Bank"},
]

SAMPLE_OHLCV = [
    {"date": "2025-01-01", "open": 1000, "high": 1050, "low": 990, "close": 1020, "volume": 5000},
    {"date": "2025-01-02", "open": 1020, "high": 1080, "low": 1010, "close": 1060, "volume": 6200},
]

SAMPLE_COMPANY = {"symbol": "NABIL", "name": "Nabil Bank", "sectorName": "Commercial Banks"}

SAMPLE_INDEX = {"index": "NEPSE", "value": 2450.12, "change": 12.5}

SAMPLE_SUBINDICES = [
    {"index": "Banking", "value": 1200.0},
    {"index": "Finance", "value": 800.0},
]

SAMPLE_MARKET_STATUS = {"isOpen": "OPEN", "id": 1}

SAMPLE_MARKET_SUMMARY = {"totalTurnover": 5_000_000, "totalTransactions": 12_000}

SAMPLE_SUPPLY_DEMAND = {"totalBuyQuantity": 500_000, "totalSellQuantity": 480_000}

SAMPLE_TOP_GAINERS = [{"symbol": "NABIL", "percentageChange": 5.2}]
SAMPLE_TOP_LOSERS  = [{"symbol": "NICA",  "percentageChange": -3.1}]
SAMPLE_TODAY_PRICE = [{"symbol": "NABIL", "lastTradedPrice": 1020, "totalTradedQuantity": 5000}]
SAMPLE_LIVE_MARKET = [{"symbol": "NABIL", "ltp": 1020}]
SAMPLE_PRICE_VOLUME = [{"symbol": "NABIL", "totalTradedQuantity": 5000}]
SAMPLE_FLOOR_SHEET  = [{"contractId": 1, "buyerMemberId": 10, "sellerMemberId": 20}]
SAMPLE_DEPTH = {"buy": [{"price": 1010, "quantity": 100}], "sell": [{"price": 1030, "quantity": 200}]}

VALID_SYMBOLS = {"NABIL", "NICA"}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client():
    """Shared TestClient for the whole module."""
    # Disable lifespan so we skip the warm-up network calls.
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


def _patch_svc(**overrides):
    """
    Return a dict of AsyncMock patches for every public service function.

    ``overrides`` lets individual tests replace specific mocks.
    """
    defaults = {
        # market
        "get_market_status":   AsyncMock(return_value=SAMPLE_MARKET_STATUS),
        "get_market_summary":  AsyncMock(return_value=SAMPLE_MARKET_SUMMARY),
        "get_supply_demand":   AsyncMock(return_value=SAMPLE_SUPPLY_DEMAND),
        # prices
        "get_today_price":     AsyncMock(return_value=SAMPLE_TODAY_PRICE),
        "get_live_market":     AsyncMock(return_value=SAMPLE_LIVE_MARKET),
        "get_price_volume":    AsyncMock(return_value=SAMPLE_PRICE_VOLUME),
        "get_top_gainers":     AsyncMock(return_value=SAMPLE_TOP_GAINERS),
        "get_top_losers":      AsyncMock(return_value=SAMPLE_TOP_LOSERS),
        "get_top_turnover":    AsyncMock(return_value=SAMPLE_TOP_GAINERS),
        "get_top_trade":       AsyncMock(return_value=SAMPLE_TOP_GAINERS),
        "get_top_transaction": AsyncMock(return_value=SAMPLE_TOP_GAINERS),
        # indices
        "get_nepse_index":     AsyncMock(return_value=SAMPLE_INDEX),
        "get_nepse_subindices":AsyncMock(return_value=SAMPLE_SUBINDICES),
        "get_index_graph":     AsyncMock(return_value={"points": []}),
        # securities
        "get_company_list":    AsyncMock(return_value=[SAMPLE_COMPANY]),
        "get_security_list":   AsyncMock(return_value=SAMPLE_SECURITY_LIST),
        "get_sector_scrips":   AsyncMock(return_value={"Commercial Banks": ["NABIL"]}),
        "get_company_details": AsyncMock(return_value=SAMPLE_COMPANY),
        "get_daily_scrip_graph":AsyncMock(return_value={"points": []}),
        "get_price_history":   AsyncMock(return_value=SAMPLE_OHLCV),
        "get_market_depth":    AsyncMock(return_value=SAMPLE_DEPTH),
        "get_bulk_price_history": AsyncMock(return_value={"NABIL": SAMPLE_OHLCV, "NICA": SAMPLE_OHLCV}),
        # floorsheet
        "get_floor_sheet":     AsyncMock(return_value=SAMPLE_FLOOR_SHEET),
        "get_floor_sheet_of":  AsyncMock(return_value=SAMPLE_FLOOR_SHEET),
    }
    defaults.update(overrides)
    return defaults


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def with_svc(mocks: dict):
    """Patch every key in *mocks* inside ``app.services.nepse``.

    Routes call ``svc.<fn>()`` where ``svc`` is the module object, so patching
    the source module is sufficient — no need to also patch each importer.
    """
    return patch.multiple("app.services.nepse", **{fn: mock for fn, mock in mocks.items()})


# ---------------------------------------------------------------------------
# System endpoints
# ---------------------------------------------------------------------------

class TestSystem:
    def test_root(self, client):
        r = client.get("/")
        assert r.status_code == 200
        body = r.json()
        assert body["service"] == "nepseman-api"
        assert "docs" in body

    def test_health(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert "uptime_seconds" in body
        assert "cache" in body

    def test_cache_clear(self, client):
        r = client.post("/cache/clear")
        assert r.status_code == 200
        assert r.json()["cleared"] is True


# ---------------------------------------------------------------------------
# Market routes
# ---------------------------------------------------------------------------

class TestMarket:
    def test_status_happy(self, client):
        mocks = _patch_svc()
        with with_svc(mocks):
            r = client.get("/api/v1/market/status")
        assert r.status_code == 200
        assert r.json()["isOpen"] == "OPEN"

    def test_status_502_on_service_failure(self, client):
        mocks = _patch_svc(get_market_status=AsyncMock(side_effect=RuntimeError("upstream down")))
        with with_svc(mocks):
            r = client.get("/api/v1/market/status")
        assert r.status_code == 502

    def test_summary_happy(self, client):
        mocks = _patch_svc()
        with with_svc(mocks):
            r = client.get("/api/v1/market/summary")
        assert r.status_code == 200
        assert "totalTurnover" in r.json()

    def test_supply_demand_happy(self, client):
        mocks = _patch_svc()
        with with_svc(mocks):
            r = client.get("/api/v1/market/supply-demand")
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Prices routes
# ---------------------------------------------------------------------------

class TestPrices:
    def test_today_price_happy(self, client):
        mocks = _patch_svc()
        with with_svc(mocks):
            r = client.get("/api/v1/prices/today")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert data[0]["symbol"] == "NABIL"

    def test_today_price_csv(self, client):
        mocks = _patch_svc()
        with with_svc(mocks):
            r = client.get("/api/v1/prices/today?fmt=csv")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/csv")
        assert "NABIL" in r.text

    def test_today_price_502(self, client):
        mocks = _patch_svc(get_today_price=AsyncMock(side_effect=Exception("boom")))
        with with_svc(mocks):
            r = client.get("/api/v1/prices/today")
        assert r.status_code == 502

    def test_live_market_happy(self, client):
        mocks = _patch_svc()
        with with_svc(mocks):
            r = client.get("/api/v1/prices/live")
        assert r.status_code == 200

    def test_price_volume_happy(self, client):
        mocks = _patch_svc()
        with with_svc(mocks):
            r = client.get("/api/v1/prices/volume")
        assert r.status_code == 200

    @pytest.mark.parametrize("sub", ["gainers", "losers", "turnover", "trade", "transaction"])
    def test_top_lists_happy(self, client, sub):
        mocks = _patch_svc()
        with with_svc(mocks):
            r = client.get(f"/api/v1/prices/top/{sub}")
        assert r.status_code == 200

    def test_top_gainers_502(self, client):
        mocks = _patch_svc(get_top_gainers=AsyncMock(side_effect=Exception("timeout")))
        with with_svc(mocks):
            r = client.get("/api/v1/prices/top/gainers")
        assert r.status_code == 502


# ---------------------------------------------------------------------------
# Indices routes
# ---------------------------------------------------------------------------

class TestIndices:
    def test_nepse_index_happy(self, client):
        mocks = _patch_svc()
        with with_svc(mocks):
            r = client.get("/api/v1/indices/nepse")
        assert r.status_code == 200
        assert r.json()["index"] == "NEPSE"

    def test_subindices_happy(self, client):
        mocks = _patch_svc()
        with with_svc(mocks):
            r = client.get("/api/v1/indices/subindices")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_index_graph_valid(self, client):
        mocks = _patch_svc()
        with with_svc(mocks):
            r = client.get("/api/v1/indices/graph/banking")
        assert r.status_code == 200

    def test_index_graph_invalid_name_400(self, client):
        mocks = _patch_svc(
            get_index_graph=AsyncMock(side_effect=ValueError("Unknown index 'invalid_xyz'"))
        )
        with with_svc(mocks):
            r = client.get("/api/v1/indices/graph/invalid_xyz")
        assert r.status_code == 400
        assert "invalid_xyz" in r.json()["detail"]

    def test_index_graph_502(self, client):
        mocks = _patch_svc(get_index_graph=AsyncMock(side_effect=RuntimeError("upstream")))
        with with_svc(mocks):
            r = client.get("/api/v1/indices/graph/nepse")
        assert r.status_code == 502


# ---------------------------------------------------------------------------
# Securities routes
# ---------------------------------------------------------------------------

class TestSecurities:
    def test_company_list_happy(self, client):
        mocks = _patch_svc()
        with with_svc(mocks):
            r = client.get("/api/v1/securities/companies")
        assert r.status_code == 200
        assert r.json()[0]["symbol"] == "NABIL"

    def test_security_list_happy(self, client):
        mocks = _patch_svc()
        with with_svc(mocks):
            r = client.get("/api/v1/securities/list")
        assert r.status_code == 200
        assert len(r.json()) == 2

    def test_security_list_csv(self, client):
        mocks = _patch_svc()
        with with_svc(mocks):
            r = client.get("/api/v1/securities/list?fmt=csv")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/csv")
        # CSV must contain the header and the symbol
        assert "symbol" in r.text
        assert "NABIL" in r.text

    def test_sectors_happy(self, client):
        mocks = _patch_svc()
        with with_svc(mocks):
            r = client.get("/api/v1/securities/sectors")
        assert r.status_code == 200
        assert "Commercial Banks" in r.json()

    def test_validate_known_symbol(self, client):
        with (
            patch("app.core.symbols.is_valid_symbol", new=AsyncMock(return_value=True)),
            patch("app.core.symbols.get_suggestions",  new=AsyncMock(return_value=[])),
        ):
            r = client.get("/api/v1/securities/validate/NABIL")
        assert r.status_code == 200
        body = r.json()
        assert body["is_valid"] is True
        assert body["symbol"] == "NABIL"
        assert body["suggestions"] == []

    def test_validate_unknown_symbol(self, client):
        with (
            patch("app.core.symbols.is_valid_symbol", new=AsyncMock(return_value=False)),
            patch("app.core.symbols.get_suggestions",  new=AsyncMock(return_value=["NABIL", "NICA"])),
        ):
            r = client.get("/api/v1/securities/validate/NABIL123")
        assert r.status_code == 200
        body = r.json()
        assert body["is_valid"] is False
        assert "NABIL" in body["suggestions"]

    def test_company_details_happy(self, client):
        mocks = _patch_svc()
        with with_svc(mocks):
            r = client.get("/api/v1/securities/NABIL")
        assert r.status_code == 200
        assert r.json()["symbol"] == "NABIL"

    def test_company_details_404_bad_symbol(self, client):
        mocks = _patch_svc(
            get_company_details=AsyncMock(side_effect=ValueError("Symbol 'BADTICKER' not found."))
        )
        with with_svc(mocks):
            r = client.get("/api/v1/securities/BADTICKER")
        assert r.status_code == 404
        assert "BADTICKER" in r.json()["detail"]

    def test_company_details_502(self, client):
        mocks = _patch_svc(
            get_company_details=AsyncMock(side_effect=RuntimeError("connection reset"))
        )
        with with_svc(mocks):
            r = client.get("/api/v1/securities/NABIL")
        assert r.status_code == 502

    def test_scrip_graph_happy(self, client):
        mocks = _patch_svc()
        with with_svc(mocks):
            r = client.get("/api/v1/securities/NABIL/graph")
        assert r.status_code == 200

    def test_scrip_graph_404_bad_symbol(self, client):
        mocks = _patch_svc(
            get_daily_scrip_graph=AsyncMock(side_effect=ValueError("Symbol 'FAKE' not found."))
        )
        with with_svc(mocks):
            r = client.get("/api/v1/securities/FAKE/graph")
        assert r.status_code == 404

    def test_price_history_happy(self, client):
        mocks = _patch_svc()
        with with_svc(mocks):
            r = client.get("/api/v1/securities/NABIL/history")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert data[0]["close"] == 1020

    def test_price_history_csv(self, client):
        mocks = _patch_svc()
        with with_svc(mocks):
            r = client.get("/api/v1/securities/NABIL/history?fmt=csv")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/csv")
        assert "close" in r.text
        assert "1020" in r.text

    def test_price_history_404_bad_symbol(self, client):
        mocks = _patch_svc(
            get_price_history=AsyncMock(side_effect=ValueError("Symbol 'FAKE' not found."))
        )
        with with_svc(mocks):
            r = client.get("/api/v1/securities/FAKE/history")
        assert r.status_code == 404

    def test_market_depth_happy(self, client):
        mocks = _patch_svc()
        with with_svc(mocks):
            r = client.get("/api/v1/securities/NABIL/depth")
        assert r.status_code == 200
        assert "buy" in r.json()

    def test_market_depth_404_bad_symbol(self, client):
        mocks = _patch_svc(
            get_market_depth=AsyncMock(side_effect=ValueError("Symbol 'FAKE' not found."))
        )
        with with_svc(mocks):
            r = client.get("/api/v1/securities/FAKE/depth")
        assert r.status_code == 404

    # -- bulk endpoint --------------------------------------------------------

    def test_bulk_history_happy(self, client):
        mocks = _patch_svc()
        with with_svc(mocks):
            r = client.get("/api/v1/securities/history/bulk?symbols=NABIL,NICA")
        assert r.status_code == 200
        body = r.json()
        assert "NABIL" in body
        assert "NICA" in body
        assert isinstance(body["NABIL"], list)

    def test_bulk_history_csv(self, client):
        mocks = _patch_svc()
        with with_svc(mocks):
            r = client.get("/api/v1/securities/history/bulk?symbols=NABIL,NICA&fmt=csv")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/csv")
        # Long-format CSV must have a symbol column
        assert "symbol" in r.text
        assert "NABIL" in r.text

    def test_bulk_history_empty_symbols_400(self, client):
        mocks = _patch_svc()
        with with_svc(mocks):
            r = client.get("/api/v1/securities/history/bulk?symbols=")
        assert r.status_code == 400

    def test_bulk_history_too_many_symbols_400(self, client):
        mocks = _patch_svc()
        symbols = ",".join([f"SYM{i:02d}" for i in range(51)])  # 51 symbols
        with with_svc(mocks):
            r = client.get(f"/api/v1/securities/history/bulk?symbols={symbols}")
        assert r.status_code == 400

    def test_bulk_history_502(self, client):
        mocks = _patch_svc(
            get_bulk_price_history=AsyncMock(side_effect=RuntimeError("upstream failure"))
        )
        with with_svc(mocks):
            r = client.get("/api/v1/securities/history/bulk?symbols=NABIL")
        assert r.status_code == 502


# ---------------------------------------------------------------------------
# Floorsheet routes
# ---------------------------------------------------------------------------

class TestFloorsheet:
    def test_floor_sheet_happy(self, client):
        mocks = _patch_svc()
        with with_svc(mocks):
            r = client.get("/api/v1/floorsheet/")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_floor_sheet_502(self, client):
        mocks = _patch_svc(get_floor_sheet=AsyncMock(side_effect=Exception("db error")))
        with with_svc(mocks):
            r = client.get("/api/v1/floorsheet/")
        assert r.status_code == 502

    def test_floor_sheet_of_happy(self, client):
        mocks = _patch_svc()
        with with_svc(mocks):
            r = client.get("/api/v1/floorsheet/NABIL")
        assert r.status_code == 200

    def test_floor_sheet_of_404_bad_symbol(self, client):
        mocks = _patch_svc(
            get_floor_sheet_of=AsyncMock(side_effect=ValueError("Symbol 'BADTICKER' not found."))
        )
        with with_svc(mocks):
            r = client.get("/api/v1/floorsheet/BADTICKER")
        assert r.status_code == 404

    def test_floor_sheet_of_502(self, client):
        mocks = _patch_svc(get_floor_sheet_of=AsyncMock(side_effect=Exception("upstream")))
        with with_svc(mocks):
            r = client.get("/api/v1/floorsheet/NABIL")
        assert r.status_code == 502
