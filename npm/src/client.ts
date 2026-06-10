/**
 * client.ts
 * ---------
 * High-level NEPSE client for Node.js / TypeScript.
 *
 * Usage:
 *   import { NepseClient } from "nepse-client";
 *
 *   const nepse = new NepseClient();
 *   const prices = await nepse.todayPrice();
 *   const history = await nepse.priceHistory("NABIL");
 */

import { NepseSession, GET_ENDPOINTS, POST_ENDPOINTS } from "./session.js";
import type {
  NepseClientOptions,
  MarketStatus,
  MarketSummary,
  StockPrice,
  PriceHistoryEntry,
  BulkHistoryResult,
  IndexName,
} from "./types.js";

const INDEX_GRAPH_MAP: Record<string, keyof typeof POST_ENDPOINTS> = {
  nepse:              "nepse_index_graph",
  sensitive:          "sensitive_index_graph",
  float:              "float_index_graph",
  sensitive_float:    "sensitive_float_index_graph",
  banking:            "banking_subindex_graph",
  dev_bank:           "dev_bank_subindex_graph",
  finance:            "finance_subindex_graph",
  hotel_tourism:      "hotel_tourism_subindex_graph",
  hydro:              "hydro_subindex_graph",
  investment:         "investment_subindex_graph",
  life_insurance:     "life_insurance_subindex_graph",
  manufacturing:      "manufacturing_subindex_graph",
  microfinance:       "microfinance_subindex_graph",
  mutual_fund:        "mutual_fund_subindex_graph",
  non_life_insurance: "non_life_insurance_subindex_graph",
  others:             "others_subindex_graph",
  trading:            "trading_subindex_graph",
};

function todayISO(): string {
  return new Date().toISOString().split("T")[0];
}

function yearAgoISO(): string {
  const d = new Date();
  d.setFullYear(d.getFullYear() - 1);
  return d.toISOString().split("T")[0];
}

export class NepseClient {
  private session: NepseSession;
  private symbolMap: Map<string, number> | null = null;

  /**
   * @param opts.baseUrl  Override base URL. Default: https://www.nepalstock.com
   * @param opts.tokenTtl Token TTL in seconds. Default: 45
   * @param opts.wasmPath Path to nepse.wasm. Default: bundled copy.
   */
  constructor(opts: NepseClientOptions = {}) {
    this.session = new NepseSession(opts);
  }

  // ── symbol resolution ───────────────────────────────────────────────────────

  private async symbolId(symbol: string): Promise<number> {
    const sym = symbol.toUpperCase();
    if (!this.symbolMap) await this.loadSymbolMap();
    if (!this.symbolMap!.has(sym)) {
      this.symbolMap = null;
      await this.loadSymbolMap();
    }
    const id = this.symbolMap!.get(sym);
    if (id === undefined) {
      throw new Error(`Symbol '${sym}' not found. Call securityList() for valid symbols.`);
    }
    return id;
  }

  private async loadSymbolMap(): Promise<void> {
    const data = await this.session.get<unknown>(GET_ENDPOINTS.security_list);
    const items: Array<{ symbol: string; id: number }> = Array.isArray(data)
      ? data
      : ((data as Record<string, unknown>)?.content as Array<{ symbol: string; id: number }> ?? []);
    this.symbolMap = new Map(items.map((i) => [i.symbol, i.id]));
  }

  // ── market ──────────────────────────────────────────────────────────────────

  /** Raw market-open data (includes `isOpen` flag). */
  async marketStatus(): Promise<MarketStatus> {
    return this.session.get<MarketStatus>(GET_ENDPOINTS.market_open) as Promise<MarketStatus>;
  }

  /** True if NEPSE is currently open. */
  async isMarketOpen(): Promise<boolean> {
    const data = await this.marketStatus();
    return data?.isOpen === "OPEN";
  }

  /** Today's market summary (turnover, index, transactions etc.). */
  async marketSummary(): Promise<MarketSummary | null> {
    return this.session.get<MarketSummary>(GET_ENDPOINTS.market_summary);
  }

  /** Market-wide supply/demand data. */
  async supplyDemand(): Promise<unknown> {
    return this.session.get(GET_ENDPOINTS.supply_demand);
  }

  // ── prices ──────────────────────────────────────────────────────────────────

  /**
   * All securities' OHLCV for today.
   * @param businessDate Optional "YYYY-MM-DD". Defaults to today.
   */
  async todayPrice(businessDate?: string): Promise<StockPrice[]> {
    const params: Record<string, string> = { size: "500" };
    if (businessDate) params.businessDate = businessDate;
    const result = await this.session.post<unknown>(
      POST_ENDPOINTS.today_price, "floor", params
    );
    if (result && typeof result === "object" && "content" in result) {
      return (result as { content: StockPrice[] }).content;
    }
    return (result as StockPrice[]) ?? [];
  }

  /** Live market ticker data. */
  async liveMarket(): Promise<unknown> {
    return this.session.get(GET_ENDPOINTS.live_market);
  }

  /** Daily price/volume stats. */
  async priceVolume(): Promise<unknown> {
    return this.session.get(GET_ENDPOINTS.price_volume);
  }

  /**
   * OHLCV history for a single ticker.
   * @param symbol     Ticker e.g. "NABIL"
   * @param startDate  "YYYY-MM-DD". Default: 1 year ago.
   * @param endDate    "YYYY-MM-DD". Default: today.
   * @param size       Max rows. Default: 500.
   */
  async priceHistory(
    symbol: string,
    startDate?: string,
    endDate?: string,
    size = 500,
  ): Promise<PriceHistoryEntry[]> {
    const sid   = await this.symbolId(symbol);
    const start = startDate ?? yearAgoISO();
    const end   = endDate   ?? todayISO();
    const path  = GET_ENDPOINTS.price_volume_history + sid;
    const result = await this.session.get<unknown>(path, {
      size: String(size),
      startDate: start,
      endDate: end,
    });
    if (result && typeof result === "object" && "content" in result) {
      return (result as { content: PriceHistoryEntry[] }).content;
    }
    return (result as PriceHistoryEntry[]) ?? [];
  }

  /**
   * Fetch price history for multiple tickers in parallel.
   * @param symbols      Array of ticker symbols.
   * @param concurrency  Max simultaneous requests. Default: 5.
   */
  async bulkPriceHistory(
    symbols: string[],
    startDate?: string,
    endDate?: string,
    size = 500,
    concurrency = 5,
  ): Promise<BulkHistoryResult> {
    const sem = new Semaphore(concurrency);
    const entries = await Promise.all(
      symbols.map(async (sym) => {
        await sem.acquire();
        try {
          const data = await this.priceHistory(sym, startDate, endDate, size);
          return [sym.toUpperCase(), data] as const;
        } catch (err) {
          return [sym.toUpperCase(), { error: String(err) }] as const;
        } finally {
          sem.release();
        }
      })
    );
    return Object.fromEntries(entries);
  }

  /**
   * Bid/ask depth for a symbol (only during market hours Sun-Thu 11:00-15:00 NST).
   */
  async marketDepth(symbol: string): Promise<unknown> {
    const sid = await this.symbolId(symbol);
    const result = await this.session.get(`${GET_ENDPOINTS.market_depth}${sid}/`);
    if (result === null) {
      return { message: "Market is closed. Depth only available Sun-Thu 11:00-15:00 NST." };
    }
    return result;
  }

  // ── top lists ───────────────────────────────────────────────────────────────

  async topGainers():     Promise<StockPrice[]> { return (await this.session.get<StockPrice[]>(GET_ENDPOINTS.top_gainers)) ?? []; }
  async topLosers():      Promise<StockPrice[]> { return (await this.session.get<StockPrice[]>(GET_ENDPOINTS.top_losers)) ?? []; }
  async topTurnover():    Promise<StockPrice[]> { return (await this.session.get<StockPrice[]>(GET_ENDPOINTS.top_turnover)) ?? []; }
  async topTrade():       Promise<StockPrice[]> { return (await this.session.get<StockPrice[]>(GET_ENDPOINTS.top_trade)) ?? []; }
  async topTransaction(): Promise<StockPrice[]> { return (await this.session.get<StockPrice[]>(GET_ENDPOINTS.top_transaction)) ?? []; }

  // ── indices ─────────────────────────────────────────────────────────────────

  /** Current NEPSE index value. */
  async nepseIndex(): Promise<unknown> {
    return this.session.get(GET_ENDPOINTS.nepse_index);
  }

  /** All sector subindices. */
  async nepseSubindices(): Promise<unknown> {
    return this.session.get(GET_ENDPOINTS.nepse_subindices);
  }

  /**
   * Historical graph data for an index.
   * @param index One of: nepse, sensitive, float, banking, hydro, etc.
   */
  async indexGraph(index: IndexName = "nepse"): Promise<unknown> {
    const key = INDEX_GRAPH_MAP[index];
    if (!key) {
      throw new Error(`Unknown index '${index}'. Valid: ${Object.keys(INDEX_GRAPH_MAP).join(", ")}`);
    }
    return this.session.post(POST_ENDPOINTS[key], "general");
  }

  // ── securities ──────────────────────────────────────────────────────────────

  /** All listed companies with sector info. */
  async companyList(): Promise<unknown[]> {
    return (await this.session.get<unknown[]>(GET_ENDPOINTS.company_list)) ?? [];
  }

  /** All securities (symbols + IDs). */
  async securityList(): Promise<Array<{ symbol: string; id: number }>> {
    const result = await this.session.get<unknown>(GET_ENDPOINTS.security_list);
    if (Array.isArray(result)) return result;
    if (result && typeof result === "object" && "content" in result) {
      return (result as { content: Array<{ symbol: string; id: number }> }).content;
    }
    return [];
  }

  /** Detailed company data for a ticker symbol. */
  async companyDetails(symbol: string): Promise<unknown> {
    const sid = await this.symbolId(symbol);
    return this.session.post(`${POST_ENDPOINTS.company_details}${sid}`, "scrips");
  }

  /** Intraday price graph data for a symbol. */
  async dailyGraph(symbol: string): Promise<unknown> {
    const sid = await this.symbolId(symbol);
    return this.session.post(`${POST_ENDPOINTS.company_daily_graph}${sid}`, "scrips");
  }

  /** Returns `{ sector: [symbols] }` mapping. */
  async sectorScrips(): Promise<Record<string, string[]>> {
    const companies = await this.companyList() as Array<{ symbol: string; sectorName?: string }>;
    const companyMap = new Map(companies.map((c) => [c.symbol, c]));
    const securities = await this.securityList();
    const result: Record<string, string[]> = {};
    for (const sec of securities) {
      const sector = companyMap.get(sec.symbol)?.sectorName ?? "Promoter Share";
      (result[sector] ??= []).push(sec.symbol);
    }
    return result;
  }

  // ── floorsheet ──────────────────────────────────────────────────────────────

  /** Market-wide floorsheet (trade records). */
  async floorSheet(page = 0, size = 500): Promise<unknown> {
    const result = await this.session.post(
      POST_ENDPOINTS.floor_sheet, "floor",
      { size: String(size), sort: "contractId,desc", page: String(page) }
    );
    if (result && typeof result === "object" && "floorsheets" in result) {
      const fs = (result as { floorsheets: { content: unknown } }).floorsheets;
      return fs.content ?? result;
    }
    return result ?? [];
  }

  /** Floorsheet records for a specific company. */
  async floorSheetOf(symbol: string, businessDate?: string, size = 500): Promise<unknown> {
    const sid = await this.symbolId(symbol);
    const bd  = businessDate ?? todayISO();
    const result = await this.session.post(
      `${POST_ENDPOINTS.company_floorsheet}${sid}`, "floor",
      { businessDate: bd, size: String(size), sort: "contractid,desc" }
    );
    if (result && typeof result === "object" && "floorsheets" in result) {
      const fs = (result as { floorsheets: { content: unknown } }).floorsheets;
      return fs.content ?? result;
    }
    return result ?? [];
  }
}

// ── simple semaphore for bulk concurrency ───────────────────────────────────────

class Semaphore {
  private count: number;
  private queue: Array<() => void> = [];

  constructor(concurrency: number) {
    this.count = concurrency;
  }

  acquire(): Promise<void> {
    if (this.count > 0) {
      this.count--;
      return Promise.resolve();
    }
    return new Promise((resolve) => this.queue.push(resolve));
  }

  release(): void {
    const next = this.queue.shift();
    if (next) {
      next();
    } else {
      this.count++;
    }
  }
}
