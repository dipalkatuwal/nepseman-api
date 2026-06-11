# nepseman-api

Unofficial async JavaScript/TypeScript client for Nepal Stock Exchange (NEPSE).

Handles WASM-based token deobfuscation and dynamic POST payload computation automatically.

---

## Installation

```bash
npm install nepseman-api
```

Requires Node.js 18+ (uses native `fetch` and `WebAssembly`).

---

## Quick Start

```typescript
import { NepseClient } from "nepseman-api";

const nepse = new NepseClient();

// Is market open?
console.log(await nepse.isMarketOpen());

// Today's prices
const prices = await nepse.todayPrice();
console.log(prices.slice(0, 3));

// NABIL 1-year history
const history = await nepse.priceHistory("NABIL");
console.log(history.slice(0, 5));

// Top gainers
console.log(await nepse.topGainers());
```

---

## API Reference

### Market
```typescript
nepse.marketStatus()       // raw market-open response
nepse.isMarketOpen()       // boolean
nepse.marketSummary()      // turnover, index, transactions
nepse.supplyDemand()       // supply/demand data
```

### Prices
```typescript
nepse.todayPrice(businessDate?)                                    // all securities OHLCV
nepse.liveMarket()                                                 // live ticker (trading hours only)
nepse.priceHistory(symbol, startDate?, endDate?, size?)            // OHLCV history
nepse.bulkPriceHistory(symbols, startDate?, endDate?, size?, concurrency?)
nepse.marketDepth(symbol)                                          // bid/ask depth (trading hours only)
nepse.priceVolume()                                                // daily stats
```

### Top Lists
```typescript
nepse.topGainers()      // top gaining stocks
nepse.topLosers()       // top losing stocks
nepse.topTurnover()     // top by turnover
nepse.topTrade()        // top by trade count
nepse.topTransaction()  // top by transactions
```

### Indices
```typescript
nepse.nepseIndex()        // current NEPSE index
nepse.nepseSubindices()   // all sector subindices
nepse.indexGraph(index)   // "nepse" | "banking" | "hydro" | ...
```

Valid index names: `nepse`, `sensitive`, `float`, `sensitive_float`, `banking`, `dev_bank`,
`finance`, `hotel_tourism`, `hydro`, `investment`, `life_insurance`, `manufacturing`,
`microfinance`, `mutual_fund`, `non_life_insurance`, `others`, `trading`

### Securities
```typescript
nepse.companyList()           // all companies with sector info
nepse.securityList()          // all securities (symbol + id)
nepse.companyDetails(symbol)  // detailed company data
nepse.dailyGraph(symbol)      // intraday graph
nepse.sectorScrips()          // { sector: [symbols] }
```

### Floorsheet
```typescript
nepse.floorSheet(page?, size?)                        // all trade records (paginated)
nepse.floorSheetOf(symbol, businessDate?, size?)      // filtered by symbol (first size rows only)
```

> **Note:** `floorSheetOf()` scans only the first `size` floorsheet records and filters
> client-side. NEPSE does not expose a per-symbol endpoint. For complete results,
> iterate `floorSheet(page)` manually.

---

## TypeScript Support

Full TypeScript types included:

```typescript
import type {
  NepseClientOptions,
  StockPrice,
  PriceHistoryEntry,
  MarketStatus,
  MarketSummary,
  BulkHistoryResult,
  IndexName,
} from "nepseman-api";
```

---

## Live REST API

Don't want to use Node.js? Use the hosted REST API:

**Base URL:** `https://nepseman-api-production.up.railway.app`

```bash
curl https://nepseman-api-production.up.railway.app/api/v1/market/status
curl https://nepseman-api-production.up.railway.app/api/v1/prices/today
curl https://nepseman-api-production.up.railway.app/api/v1/securities/NABIL
```

Interactive docs: `https://nepseman-api-production.up.railway.app/docs`

---

## Disclaimer

This project is **unofficial** and **not affiliated with NEPSE** or nepalstock.com.np.
It reverse-engineers the public-facing web interface for educational and personal use.
Data accuracy is not guaranteed. Do not use in production trading systems.

## License

MIT