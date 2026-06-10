// ── Auth types ─────────────────────────────────────────────────────────────────

export interface TokenResponse {
  accessToken: string;
  refreshToken: string;
  salt1: number;
  salt2: number;
  salt3: number;
  salt4: number;
  salt5: number;
}

// ── Market types ───────────────────────────────────────────────────────────────

export interface MarketStatus {
  id: number;
  isOpen: "OPEN" | "CLOSE";
  [key: string]: unknown;
}

export interface MarketSummary {
  totalTurnover?: number;
  totalTradedShares?: number;
  totalTransactions?: number;
  totalScrips?: number;
  marketCap?: number;
  sensitiveIndex?: number;
  nepseIndex?: number;
  nepseChange?: number;
  [key: string]: unknown;
}

// ── Price types ────────────────────────────────────────────────────────────────

export interface StockPrice {
  symbol?: string;
  securityName?: string;
  openPrice?: number;
  highPrice?: number;
  lowPrice?: number;
  closingPrice?: number;
  totalTradedQuantity?: number;
  totalTradedValue?: number;
  previousClosing?: number;
  percentageChange?: number;
  [key: string]: unknown;
}

export interface PriceHistoryEntry {
  businessDate?: string;
  openPrice?: number;
  highPrice?: number;
  lowPrice?: number;
  closingPrice?: number;
  tradedQuantity?: number;
  amount?: number;
  [key: string]: unknown;
}

export interface BulkHistoryResult {
  [symbol: string]: PriceHistoryEntry[] | { error: string };
}

// ── Index types ────────────────────────────────────────────────────────────────

export type IndexName =
  | "nepse" | "sensitive" | "float" | "sensitive_float"
  | "banking" | "dev_bank" | "finance" | "hotel_tourism"
  | "hydro" | "investment" | "life_insurance" | "manufacturing"
  | "microfinance" | "mutual_fund" | "non_life_insurance"
  | "others" | "trading";

// ── Client options ─────────────────────────────────────────────────────────────

export interface NepseClientOptions {
  /** Override base URL. Default: https://www.nepalstock.com */
  baseUrl?: string;
  /** Token TTL in seconds. Default: 45 */
  tokenTtl?: number;
}
