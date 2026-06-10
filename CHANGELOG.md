# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.0.0] - 2025-06-01

### Added

- **Independent WASM-based authentication** — zero dependency on any
  third-party NEPSE library. Auth is implemented from scratch by invoking
  NEPSE's own `nepse.wasm` binary via `wasmtime`, calling its exported
  functions (`cdx`, `rdx`, `bdx`, `ndx`, `mdx`) to compute JWT slice
  positions and strip injected characters from the obfuscated access token.

- **Fully async HTTP layer** — all network I/O uses `httpx` + `asyncio`.
  Authenticated session is managed in `app/core/session.py` with automatic
  token refresh on expiry.

- **TTL in-memory cache** (`app/core/cache.py`) — `@cache.ttl(seconds=N)`
  decorator with per-function keying. TTLs: live data 30 s, index data 60 s,
  stable data 600 s. Cache stats exposed on `GET /health`.

- **Rate limiting** — per-IP request throttling via `slowapi`
  (default 60 req/min).

- **WebSocket endpoint** (`/ws`) — supports one-shot route queries and
  continuous channel subscriptions with configurable polling intervals.
  Available channels: `live_market`, `today_price`, `top_gainers`,
  `top_losers`, `top_turnover`, `top_trade`, `top_transaction`,
  `nepse_index`, `subindices`, `market_status`, `supply_demand`,
  `market_depth`, `company_details`, `price_history`, `floor_sheet_of`.

- **CSV export** — all list endpoints support `?fmt=csv` query parameter to
  stream a `text/csv` response with `Content-Disposition: attachment`.

- **Symbol validation + fuzzy suggestions** (`app/core/symbols.py`) —
  `GET /api/v1/securities/validate/{symbol}` returns `is_valid` and a
  ranked list of nearest-match suggestions for unknown tickers.

- **Bulk parallel OHLCV history** — `GET /api/v1/securities/history/bulk`
  accepts a comma-separated `symbols` parameter (up to 50) and fetches all
  histories concurrently via `asyncio.gather` with a configurable semaphore
  (default concurrency 5). Supports JSON and long-format CSV output.

- **Docker + docker-compose** — single-command deployment via
  `docker-compose up -d`.

- **GitHub Actions CI** — three-job pipeline: unit tests on Python 3.11 and
  3.12 (`pytest`), `ruff` lint, and Docker build + health-check smoke test.

- **Pip-installable package** (`pyproject.toml`) — WASM binary bundled via
  `MANIFEST.in`; installable directly from GitHub with
  `pip install git+https://...`.

### REST endpoints added

| Route | Description |
|-------|-------------|
| `GET /api/v1/market/status` | Market open/closed status |
| `GET /api/v1/market/summary` | Daily market summary |
| `GET /api/v1/market/supply-demand` | Supply & demand figures |
| `GET /api/v1/prices/today` | All stock prices (with CSV export) |
| `GET /api/v1/prices/live` | Live market feed |
| `GET /api/v1/prices/volume` | Price & volume data |
| `GET /api/v1/prices/top/{gainers,losers,turnover,trade,transaction}` | Top-N lists |
| `GET /api/v1/indices/nepse` | NEPSE composite index |
| `GET /api/v1/indices/subindices` | All sector sub-indices |
| `GET /api/v1/indices/graph/{index_name}` | Time-series graph for any index |
| `GET /api/v1/securities/companies` | Full company list |
| `GET /api/v1/securities/list` | Security list (with CSV export) |
| `GET /api/v1/securities/sectors` | Companies grouped by sector |
| `GET /api/v1/securities/validate/{symbol}` | Symbol validation + suggestions |
| `GET /api/v1/securities/{symbol}` | Company details |
| `GET /api/v1/securities/{symbol}/graph` | Daily price graph |
| `GET /api/v1/securities/{symbol}/history` | OHLCV history (with CSV export) |
| `GET /api/v1/securities/{symbol}/depth` | Market depth (live hours only) |
| `GET /api/v1/securities/history/bulk` | Parallel multi-ticker OHLCV |
| `GET /api/v1/floorsheet/` | Paginated full floorsheet |
| `GET /api/v1/floorsheet/{symbol}` | Per-symbol floorsheet |
| `GET /health` | Uptime, last sync, cache stats |
| `POST /cache/clear` | Flush in-memory cache |

[Unreleased]: https://github.com/yourname/nepse_scrapper/compare/v2.0.0...HEAD
[2.0.0]: https://github.com/yourname/nepse_scrapper/releases/tag/v2.0.0
