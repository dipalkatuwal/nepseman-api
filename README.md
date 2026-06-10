# nepseman-api

> **Unofficial, reverse-engineered REST + WebSocket API for Nepal Stock Exchange (NEPSE) market data.**
> Not affiliated with NEPSE or nepalstock.com.np. Use at your own risk.

**nepseman-api** scrapes and serves live NEPSE data by reverse-engineering the authentication layer of `nepalstock.com.np` — including WASM-based token obfuscation and salt-based payload signing — with no dependency on any third-party NEPSE library.

---

## Quick Start

### Option 1 — Use the live hosted API (no setup needed)

Base URL: **`https://nepseman-api-production.up.railway.app`**

```bash
# Market status
curl https://nepseman-api-production.up.railway.app/api/v1/market/status

# Today's prices
curl https://nepseman-api-production.up.railway.app/api/v1/prices/today

# Top gainers
curl https://nepseman-api-production.up.railway.app/api/v1/prices/top/gainers

# NEPSE index
curl https://nepseman-api-production.up.railway.app/api/v1/indices/nepse

# Company details
curl https://nepseman-api-production.up.railway.app/api/v1/securities/NABIL
```

Interactive docs: **`https://nepseman-api-production.up.railway.app/docs`**

---

### Option 2 — Install and run locally 

**Via pip (from GitHub):**

```bash
pip install git+https://github.com/dipalkatuwal/nepseman-api.git
```

Then run:

```bash
nepseman-api
# → http://localhost:8000
```

**Via Docker:**

```bash
git clone https://github.com/dipalkatuwal/nepseman-api.git
cd nepseman-api
cp .env.example .env
docker compose up -d
```

API available at `http://localhost:8000` · Docs at `http://localhost:8000/docs`

---

## Features

- **Zero third-party NEPSE dependency** — auth implemented from scratch using NEPSE's own WASM binary
- **Fully async** — built on `httpx` + `asyncio` + `asyncpg`, non-blocking end to end
- **PostgreSQL persistence** — every price fetch saved via SQLAlchemy async ORM, queryable with pagination and filtering
- **Alembic migrations** — schema versioned and reproducible
- **WebSocket support** — subscribe to live market data streams
- **CSV export** — any list endpoint supports `?fmt=csv`
- **Symbol validation** — validate tickers with fuzzy suggestions
- **TTL caching** — live data cached 30s, stable data 10 min
- **Rate limiting** — per-IP rate limits via `slowapi`
- **Docker ready** — `docker-compose up` starts everything

---

## Tech Stack

- **FastAPI** + **Uvicorn** — async web framework
- **httpx** — async HTTP client (~3× faster than `requests`)
- **wasmtime** — runs NEPSE's own `.wasm` binary for token decoding
- **SQLAlchemy (async)** + **asyncpg** — PostgreSQL ORM
- **Alembic** — database migrations
- **slowapi** — per-IP rate limiting
- **pydantic-settings** — env-based config

---

## Project Structure

```
nepseman-api/
├── app/
│   ├── main.py                  # FastAPI app — rate limiting, cache headers, health
│   ├── core/
│   │   ├── auth.py              # WASM token parser + payload calculator
│   │   ├── cache.py             # TTL in-memory cache + @cache.ttl decorator
│   │   ├── config.py            # Settings (env vars via pydantic-settings)
│   │   ├── endpoints.py         # All NEPSE endpoint paths
│   │   ├── nepse.wasm           # NEPSE's own WASM binary (bundled)
│   │   ├── session.py           # Async authenticated HTTP session (httpx)
│   │   └── symbols.py           # Symbol validation + fuzzy suggestions
│   ├── db/
│   │   ├── database.py          # SQLAlchemy async engine + session factory
│   │   ├── models.py            # ORM models: MarketSnapshot, MarketSummary
│   │   └── repository.py        # DB queries (save, get, paginate)
│   ├── services/
│   │   └── nepse.py             # All data functions — async + cached
│   ├── models/
│   │   └── responses.py         # Pydantic response models
│   └── api/
│       └── routes/
│           ├── market.py        # /api/v1/market/*
│           ├── prices.py        # /api/v1/prices/*
│           ├── indices.py       # /api/v1/indices/*
│           ├── securities.py    # /api/v1/securities/*
│           ├── meta.py          # /api/v1/floorsheet/*
│           └── ws.py            # /ws  WebSocket
├── alembic/
│   └── versions/
│       └── 001_create_market_tables.py
├── scripts/
│   └── test_all.py
├── tests/
│   ├── test_auth.py
│   └── test_api.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

## API Reference

### System

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Service info |
| GET | `/health` | Uptime, last sync, cache stats |
| POST | `/cache/clear` | Clear all cached data |
| WS | `/ws` | WebSocket live stream |

### Market

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/market/status` | Open/closed status |
| GET | `/api/v1/market/summary` | Today's market summary |
| GET | `/api/v1/market/supply-demand` | Supply & demand |

### Prices

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/prices/today` | All stock prices (auto-persisted to PostgreSQL) |
| GET | `/api/v1/prices/today?fmt=csv` | Download as CSV |
| GET | `/api/v1/prices/today?persist=false` | Fetch without saving to DB |
| GET | `/api/v1/prices/live` | Live market data |
| GET | `/api/v1/prices/top/gainers` | Top gainers |
| GET | `/api/v1/prices/top/losers` | Top losers |
| GET | `/api/v1/prices/top/turnover` | Top by turnover |
| GET | `/api/v1/prices/top/trade` | Top by trade count |
| GET | `/api/v1/prices/top/transaction` | Top by transactions |

### PostgreSQL Snapshots

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/prices/snapshots` | Query persisted snapshots (paginated) |
| GET | `/api/v1/prices/snapshots?symbol=NABIL` | Filter by symbol |
| GET | `/api/v1/prices/snapshots?business_date=2025-06-09` | Filter by date |
| GET | `/api/v1/prices/snapshots?limit=100&offset=0` | Pagination |
| GET | `/api/v1/prices/snapshots/{symbol}/latest` | Latest snapshot for a symbol |

### Indices

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/indices/nepse` | NEPSE index |
| GET | `/api/v1/indices/subindices` | All sub-indices |
| GET | `/api/v1/indices/graph/{index_name}` | Index graph data |

### Securities

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/securities/companies` | All listed companies |
| GET | `/api/v1/securities/list` | Securities list |
| GET | `/api/v1/securities/sectors` | Grouped by sector |
| GET | `/api/v1/securities/validate/{symbol}` | Validate + fuzzy suggestions |
| GET | `/api/v1/securities/{symbol}` | Company details |
| GET | `/api/v1/securities/{symbol}/history` | OHLCV price history |
| GET | `/api/v1/securities/{symbol}/depth` | Market depth |
| GET | `/api/v1/securities/history/bulk?symbols=NABIL,NICA` | Parallel bulk OHLCV |

### Floorsheet

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/floorsheet/` | Full floorsheet (paginated) |
| GET | `/api/v1/floorsheet/{symbol}` | Floorsheet for a company |

---

## WebSocket

Connect to `ws://localhost:8000/ws`

```json
{ "route": "live_market" }
{ "route": "subscribe", "channel": "live_market", "interval": 10 }
{ "route": "unsubscribe", "channel": "live_market" }
```

---

## Testing

```bash
# Unit tests (no network or DB needed)
pytest tests/ -v

# Smoke test all endpoints (Nepal IP + running server required)
python scripts/test_all.py
```

---

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `SSL: CERTIFICATE_VERIFY_FAILED` | Incomplete NEPSE cert chain | Set `NEPSE_VERIFY_SSL=false` in `.env` |
| `403` / connection refused | Foreign IP geo-blocked | Run from a Nepal network |
| `Connection refused (5432)` | PostgreSQL not running | `docker-compose up postgres` |
| `Symbol 'XYZ' not found` | Invalid ticker | Check `/api/v1/securities/validate/XYZ` |
| Token expired errors | NEPSE session TTL | Automatic — session re-authenticates every 45s |

---


## Deployment

### Run Alembic migrations before (re)deploying

Always migrate the database before rolling out a new image so schema changes
are applied before the app starts serving traffic:

```bash
docker compose run --rm nepse-api alembic upgrade head
```

This runs in a throwaway container against the live `postgres` service and
exits cleanly when done.

### Zero-downtime redeploy

Rebuild and restart only the API container without touching postgres or nginx:

```bash
docker compose up -d --no-deps --build nepse-api
```

`--no-deps` prevents Compose from restarting dependency services (postgres,
nginx), so the database stays up and in-flight connections are unaffected.
`--build` rebuilds the image from the current source before starting the
new container. Docker Compose stops the old container and starts the new one
with a brief gap (single-instance downtime); for true zero-downtime you would
front this with nginx upstream health checks and run two API replicas.

### Crash recovery

Both `nepse-api` and `postgres` are configured with `restart: unless-stopped`.
If either crashes, Docker restarts it automatically without manual intervention.
Combined with the healthcheck (`/health` polled every 30 s), Docker will also
restart the container if it becomes unresponsive.

### Full stack bring-up

```bash
# First run — build image, migrate, start everything
docker compose up -d --build
docker compose run --rm nepse-api alembic upgrade head

# Subsequent deploys
docker compose run --rm nepse-api alembic upgrade head
docker compose up -d --no-deps --build nepse-api
```

## Disclaimer

This project is **unofficial** and **not affiliated with NEPSE** or nepalstock.com.np in any way. It reverse-engineers the public-facing web interface for educational and personal use. Data accuracy is not guaranteed. Do not use in production trading systems.

---

## License

MIT