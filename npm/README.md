# nepse-client

Unofficial async JavaScript/TypeScript client for Nepal Stock Exchange (NEPSE).

Handles WASM-based token deobfuscation and dynamic POST payload computation automatically.

> ⚠️ **Nepal IP required.** `nepalstock.com` blocks non-Nepal IPs.

---

## Installation

```bash
npm install nepse-client
```

Requires Node.js 18+ (uses native `fetch` and `WebAssembly`).

---

## Quick start

```typescript
import { NepseClient } from "nepse-client";

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

## API reference

### Market
```typescript
nepse.marketStatus()       // raw market-open response
nepse.isMarketOpen()       // boolean
nepse.marketSummary()      // turnover, index, transactions
nepse.supplyDemand()       // supply/demand data
```

### Prices
```typescript
nepse.todayPrice(businessDate?)                          // all securities OHLCV
nepse.liveMarket()                                       // live ticker
nepse.priceHistory(symbol, startDate?, endDate?, size?)  // OHLCV history
nepse.bulkPriceHistory(symbols, start?, end?, size?, concurrency?)
nepse.marketDepth(symbol)                                // bid/ask depth
nepse.priceVolume()                                      // daily stats
```

### Top lists
```typescript
nepse.topGainers() | nepse.topLosers() | nepse.topTurnover()
nepse.topTrade()   | nepse.topTransaction()
```

### Indices
```typescript
nepse.nepseIndex()           // current NEPSE index
nepse.nepseSubindices()      // all sector subindices
nepse.indexGraph(index)      // "nepse" | "banking" | "hydro" | ...
```

### Securities
```typescript
nepse.companyList()          // all companies with sectors
nepse.securityList()         // all securities (symbol + id)
nepse.companyDetails(symbol) // detailed company data
nepse.dailyGraph(symbol)     // intraday graph
nepse.sectorScrips()         // { sector: [symbols] }
```

### Floorsheet
```typescript
nepse.floorSheet(page?, size?)
nepse.floorSheetOf(symbol, businessDate?, size?)
```

---

## TypeScript support

Full TypeScript types are included. Key types:

```typescript
import type {
  NepseClientOptions,
  StockPrice,
  PriceHistoryEntry,
  MarketStatus,
  MarketSummary,
  BulkHistoryResult,
  IndexName,
} from "nepse-client";
```

---

## License

MIT
