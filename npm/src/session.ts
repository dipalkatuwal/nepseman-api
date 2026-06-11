/**
 * session.ts
 * ----------
 * Authenticated HTTP session for nepalstock.com using the native fetch API (Node 18+).
 */

import { TokenParser, calculatePayloadId, type RawTokenResponse, type PayloadType } from "./auth.js";
process.env["NODE_TLS_REJECT_UNAUTHORIZED"] = "0";

export const GET_ENDPOINTS = {
  authenticate:         "/api/authenticate/prove",
  market_open:          "/api/nots/nepse-data/market-open",
  market_summary:       "/api/nots/market-summary/",
  supply_demand:        "/api/nots/nepse-data/supplydemand",
  top_gainers:          "/api/nots/top-ten/top-gainer",
  top_losers:           "/api/nots/top-ten/top-loser",
  top_turnover:         "/api/nots/top-ten/turnover",
  top_trade:            "/api/nots/top-ten/trade",
  top_transaction:      "/api/nots/top-ten/transaction",
  nepse_index:          "/api/nots/nepse-index",
  nepse_subindices:     "/api/nots",
  live_market:          "/api/nots/lives-market",
  company_list:         "/api/nots/company/list",
  security_list:        "/api/nots/security?nonDelisted=true",
  price_volume:         "/api/nots/securityDailyTradeStat/58",
  price_volume_history: "/api/nots/market/history/security/",
  market_depth:         "/api/nots/nepse-data/marketdepth/",
} as const;

export const POST_ENDPOINTS = {
  today_price:          "/api/nots/nepse-data/today-price",
  floor_sheet:          "/api/nots/nepse-data/floorsheet",
  company_details:      "/api/nots/security/",
  company_daily_graph:  "/api/nots/market/graphdata/daily/",
  company_floorsheet:   "/api/nots/security/floorsheet/",
  nepse_index_graph:              "/api/nots/graph/index/58",
  sensitive_index_graph:          "/api/nots/graph/index/57",
  float_index_graph:              "/api/nots/graph/index/62",
  sensitive_float_index_graph:    "/api/nots/graph/index/63",
  banking_subindex_graph:         "/api/nots/graph/index/51",
  dev_bank_subindex_graph:        "/api/nots/graph/index/55",
  finance_subindex_graph:         "/api/nots/graph/index/60",
  hotel_tourism_subindex_graph:   "/api/nots/graph/index/52",
  hydro_subindex_graph:           "/api/nots/graph/index/54",
  investment_subindex_graph:      "/api/nots/graph/index/67",
  life_insurance_subindex_graph:  "/api/nots/graph/index/65",
  manufacturing_subindex_graph:   "/api/nots/graph/index/56",
  microfinance_subindex_graph:    "/api/nots/graph/index/64",
  mutual_fund_subindex_graph:     "/api/nots/graph/index/66",
  non_life_insurance_subindex_graph: "/api/nots/graph/index/59",
  others_subindex_graph:          "/api/nots/graph/index/53",
  trading_subindex_graph:         "/api/nots/graph/index/61",
} as const;

const TYPE_MAP: Record<string, PayloadType> = {
  scrips:  "stock-live",
  floor:   "sector-live",
  general: "general",
};

const DEFAULT_HEADERS = {
  "User-Agent":      "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0",
  "Accept":          "application/json, text/plain, */*",
  "Accept-Language": "en-US,en;q=0.5",
  "Cache-Control":   "no-cache",
};

export interface SessionOptions {
  baseUrl?: string;
  tokenTtl?: number;
  wasmPath?: string;
}

export class NepseSession {
  private baseUrl: string;
  private tokenTtl: number;
  private wasmPath?: string;

  private parser = new TokenParser();
  private parserReady = false;

  private accessToken: string | null = null;
  private tokenDetails: RawTokenResponse | null = null;
  private marketOpenId: number | null = null;
  private tokenTimestamp = 0;

  constructor(opts: SessionOptions = {}) {
    this.baseUrl  = (opts.baseUrl ?? "https://www.nepalstock.com").replace(/\/$/, "");
    this.tokenTtl = opts.tokenTtl ?? 45;
    this.wasmPath = opts.wasmPath;
  }

  // ── private ──────────────────────────────────────────────────────────────────

  private async ensureParser(): Promise<void> {
    if (!this.parserReady) {
      await this.parser.init(this.wasmPath);
      this.parserReady = true;
    }
  }

  private async authenticate(): Promise<void> {
    const age = (Date.now() - this.tokenTimestamp) / 1000;
    if (this.accessToken && age < this.tokenTtl) return;

    await this.ensureParser();
    const url = `${this.baseUrl}${GET_ENDPOINTS.authenticate}`;
    const resp = await fetch(url, { headers: DEFAULT_HEADERS });
    if (!resp.ok) throw new Error(`Auth failed: ${resp.status} ${resp.statusText}`);

    const raw = await resp.json() as Record<string, unknown>;
    for (let i = 1; i <= 5; i++) raw[`salt${i}`] = Number(raw[`salt${i}`]);

    const tokenRaw = raw as unknown as RawTokenResponse;
    const { accessToken } = this.parser.parseTokens(tokenRaw);
    this.accessToken = accessToken;
    this.tokenDetails = tokenRaw;
    this.tokenTimestamp = Date.now();
    this.marketOpenId = null;
  }

  private async getMarketOpenId(): Promise<number> {
    if (this.marketOpenId !== null) return this.marketOpenId;
    await this.authenticate();
    const resp = await fetch(`${this.baseUrl}${GET_ENDPOINTS.market_open}`, {
      headers: this.authHeaders(),
    });
    if (!resp.ok) throw new Error(`market-open failed: ${resp.status}`);
    const data = await resp.json() as { id: number };
    this.marketOpenId = data.id;
    return this.marketOpenId;
  }

  private authHeaders(): Record<string, string> {
    return {
      ...DEFAULT_HEADERS,
      "Authorization": `Salter ${this.accessToken}`,
      "Content-Type": "application/json",
    };
  }

  private async payloadId(which: PayloadType): Promise<number> {
    return calculatePayloadId(await this.getMarketOpenId(), this.tokenDetails!, which);
  }

  // ── public ───────────────────────────────────────────────────────────────────

  async get<T = unknown>(path: string, params?: Record<string, string>): Promise<T | null> {
    await this.authenticate();
    let url = `${this.baseUrl}${path}`;
    if (params) url += "?" + new URLSearchParams(params).toString();
    const resp = await fetch(url, { headers: this.authHeaders() });
    if (!resp.ok) throw new Error(`GET ${path} failed: ${resp.status}`);
    const text = await resp.text();
    return text.trim() ? JSON.parse(text) as T : null;
  }

  async post<T = unknown>(
    path: string,
    payloadType: string = "general",
    extraParams?: Record<string, string>,
  ): Promise<T | null> {
    await this.authenticate();
    const which = TYPE_MAP[payloadType] ?? "general";
    const payload = { id: await this.payloadId(which) };

    let url = `${this.baseUrl}${path}`;
    if (extraParams) url += "?" + new URLSearchParams(extraParams).toString();

    const resp = await fetch(url, {
      method: "POST",
      headers: this.authHeaders(),
      body: JSON.stringify(payload),
    });
    if (!resp.ok) throw new Error(`POST ${path} failed: ${resp.status}`);
    const text = await resp.text();
    return text.trim() ? JSON.parse(text) as T : null;
  }
}
