# nepseman-api

> **Unofficial, reverse-engineered REST API for Nepal Stock Exchange (NEPSE) market data.**
> Not affiliated with NEPSE or nepalstock.com.np. Use at your own risk.

This monorepo contains three things:

| Package | Description | Install |
|---------|-------------|---------|
| `server/` | FastAPI server — self-host the full REST API | Docker / Railway |
| `nepseman_api/` | Python client library | `pip install nepseman-api` |
| `npm/` | TypeScript client library | `npm install nepseman-api` |

---

## Live API

No setup needed — use the hosted API directly:

**Base URL:** `https://nepseman-api-production.up.railway.app`

```bash
curl https://nepseman-api-production.up.railway.app/api/v1/market/status
curl https://nepseman-api-production.up.railway.app/api/v1/prices/today
curl https://nepseman-api-production.up.railway.app/api/v1/securities/NABIL
```

Interactive docs: `https://nepseman-api-production.up.railway.app/docs`

---

## Python Client

```bash
pip install nepseman-api
```

```python
import asyncio
from nepseman_api import NepseClient

async def main():
    async with NepseClient() as nepse:
        print(await nepse.market_status())
        print(await nepse.today_price())
        print(await nepse.price_history("NABIL"))

asyncio.run(main())
```

→ Full docs: [pypi.org/project/nepseman-api](https://pypi.org/project/nepseman-api)

---

## TypeScript Client

```bash
npm install nepseman-api
```

```typescript
import { NepseClient } from "nepseman-api";

const nepse = new NepseClient();
const status = await nepse.marketStatus();
```

---

## Self-Host the API

### Docker

```bash
git clone https://github.com/dipalkatuwal/nepseman-api.git
cd nepseman-api/server
cp .env.example .env
docker compose up -d
```

API at `http://localhost:8000` · Docs at `http://localhost:8000/docs`

### Local development

```bash
cd server
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
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
| GET | `/api/v1/prices/today` | All stock prices |
| GET | `/api/v1/prices/today?fmt=csv` | Download as CSV |
| GET | `/api/v1/prices/live` | Live market data |
| GET | `/api/v1/prices/top/gainers` | Top gainers |
| GET | `/api/v1/prices/top/losers` | Top losers |
| GET | `/api/v1/prices/top/turnover` | Top by turnover |
| GET | `/api/v1/prices/top/trade` | Top by trade count |
| GET | `/api/v1/prices/top/transaction` | Top by transactions |

### PostgreSQL Snapshots

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/prices/snapshots` | Persisted snapshots (paginated) |
| GET | `/api/v1/prices/snapshots?symbol=NABIL` | Filter by symbol |
| GET | `/api/v1/prices/snapshots?business_date=2026-06-10` | Filter by date |
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
| GET | `/api/v1/securities/history/bulk?symbols=NABIL,NICA` | Bulk OHLCV |

### Floorsheet

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/floorsheet/` | Full floorsheet (paginated) |
| GET | `/api/v1/floorsheet/{symbol}` | Floorsheet for a company |

---

## Features

- **Zero third-party NEPSE dependency** — auth implemented from scratch using NEPSE's own WASM binary
- **Fully async** — built on `httpx` + `asyncio` + `asyncpg`
- **PostgreSQL persistence** — every price fetch saved via SQLAlchemy async ORM
- **Alembic migrations** — schema versioned and reproducible
- **WebSocket support** — subscribe to live market data streams
- **CSV export** — any list endpoint supports `?fmt=csv`
- **TTL caching** — live data cached 30s, stable data 10 min
- **Rate limiting** — per-IP via `slowapi`
- **Docker ready** — `docker compose up` starts everything

---

## Tech Stack

- **FastAPI** + **Uvicorn** — async web framework
- **httpx** — async HTTP client
- **wasmtime** — runs NEPSE's own `.wasm` binary for token decoding
- **SQLAlchemy (async)** + **asyncpg** — PostgreSQL ORM
- **Alembic** — database migrations
- **slowapi** — rate limiting
- **pydantic-settings** — env-based config

---

## Project Structure

```
nepseman-api/
├── nepseman_api/     ← Python client (pip install nepseman-api)
├── npm/              ← TypeScript client (npm install nepseman-api)
├── server/           ← FastAPI server
│   ├── app/
│   ├── alembic/
│   ├── scripts/
│   ├── tests/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── requirements.txt
├── README.md
└── LICENSE
```

---

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `403 Forbidden` | Foreign IP geo-blocked | Run from a Nepal network |
| `SSL error` | Incomplete NEPSE cert chain | Client bypasses automatically |
| `Connection refused (5432)` | PostgreSQL not running | `docker compose up postgres` |
| `Symbol 'XYZ' not found` | Invalid ticker | Check `/api/v1/securities/validate/XYZ` |
| `live_market` empty | Outside trading hours | Available Sun–Thu 11:00–15:00 NST |

---

## Disclaimer

This project is **unofficial** and **not affiliated with NEPSE** or nepalstock.com.np. It reverse-engineers the public-facing web interface for educational and personal use. Data accuracy is not guaranteed. Do not use in production trading systems.

## License

MIT