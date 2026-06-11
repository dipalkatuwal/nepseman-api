# nepseman-api

> Unofficial async Python client for Nepal Stock Exchange (NEPSE) market data.
> Not affiliated with NEPSE or nepalstock.com.np. Use at your own risk.

Reverse-engineers the authentication layer of `nepalstock.com.np` — including WASM-based token obfuscation and salt-based payload signing — with no dependency on any third-party NEPSE library.

## Installation

```bash
pip install nepseman-api
```

## Quick Start

```python
import asyncio
from nepseman_api import NepseClient

async def main():
    async with NepseClient() as nepse:
        # Market status
        status = await nepse.market_status()
        print(status)

        # Today's prices
        prices = await nepse.today_price()
        print(prices[:5])

        # Price history for a stock
        history = await nepse.price_history("NABIL")
        print(history[:5])

asyncio.run(main())
```

## Available Methods

### Market
```python
await nepse.market_status()       # Open/closed status
await nepse.is_market_open()      # Returns True/False
await nepse.market_summary()      # Today's summary (turnover, transactions)
await nepse.supply_demand()       # Market-wide supply & demand
```

### Prices
```python
await nepse.today_price()                        # All stock prices
await nepse.today_price(business_date="2026-06-10")  # Specific date
await nepse.live_market()                        # Live ticker (trading hours only)
await nepse.price_volume()                       # Price/volume stats
```

### Top Lists
```python
await nepse.top_gainers()      # Top gaining stocks
await nepse.top_losers()       # Top losing stocks
await nepse.top_turnover()     # Top by turnover
await nepse.top_trade()        # Top by trade count
await nepse.top_transaction()  # Top by transactions
```

### Indices
```python
await nepse.nepse_index()          # NEPSE index value
await nepse.nepse_subindices()     # All sector subindices
await nepse.index_graph("banking") # Historical graph data
```

### Securities
```python
await nepse.company_list()              # All listed companies
await nepse.security_list()             # All securities with IDs
await nepse.sector_scrips()             # Grouped by sector
await nepse.company_details("NABIL")    # Company details
await nepse.daily_graph("NABIL")        # Intraday graph
await nepse.price_history("NABIL")      # OHLCV history (1 year default)
await nepse.price_history(
    "NABIL",
    start_date="2025-01-01",
    end_date="2025-12-31",
    size=500,
)
await nepse.market_depth("NABIL")       # Bid/ask depth (trading hours only)
```

### Bulk History
```python
# Fetch history for multiple stocks in parallel
results = await nepse.bulk_price_history(
    ["NABIL", "NICA", "ADBL"],
    start_date="2025-01-01",
    concurrency=5,
)
# {"NABIL": [...], "NICA": [...], "ADBL": [...]}
```

### Floorsheet
```python
await nepse.floor_sheet()                    # All trade records (paginated)
await nepse.floor_sheet(page=1, size=500)
await nepse.floor_sheet_of("NABIL")         # Filtered by symbol (first 500 rows only)
```

> **Note:** `floor_sheet_of()` scans only the first `size` floorsheet records.
> NEPSE does not expose a per-symbol endpoint. For complete results,
> iterate `floor_sheet(page=N)` and filter manually.

## Index Names

Valid values for `index_graph()`:

`nepse`, `sensitive`, `float`, `sensitive_float`, `banking`, `dev_bank`,
`finance`, `hotel_tourism`, `hydro`, `investment`, `life_insurance`,
`manufacturing`, `microfinance`, `mutual_fund`, `non_life_insurance`,
`others`, `trading`

## Notes

- **Trading hours** — `live_market()` and `market_depth()` only return data Sun–Thu 11:00–15:00 NST
- **Floorsheet** — `floor_sheet_of()` filters client-side from the general floorsheet (NEPSE does not expose a per-symbol endpoint)
- **SSL** — NEPSE serves an incomplete certificate chain; the client bypasses SSL verification automatically

## Live API

Don't want to run Python? Use the hosted REST API:

**Base URL:** `https://nepseman-api-production.up.railway.app`

```bash
curl https://nepseman-api-production.up.railway.app/api/v1/market/status
curl https://nepseman-api-production.up.railway.app/api/v1/prices/today
curl https://nepseman-api-production.up.railway.app/api/v1/securities/NABIL
```

Interactive docs: `https://nepseman-api-production.up.railway.app/docs`

## Disclaimer

This project is **unofficial** and **not affiliated with NEPSE** or nepalstock.com.np. It reverse-engineers the public-facing web interface for educational and personal use. Data accuracy is not guaranteed. Do not use in production trading systems.

## License

MIT
