"""
endpoints.py  —  Ground-truth NEPSE endpoint map
-------------------------------------------------
GET  = plain authenticated GET, no body
POST = authenticated POST with {"id": <payload_id>} body

Source: basic-bgnr/NepseUnofficialApi  API_ENDPOINTS.json + NepseLib.py
"""

# ── GET endpoints (no payload body needed) ────────────────────────────────────
GET_ENDPOINTS = {
    "authenticate":        "/api/authenticate/prove",
    "market_open":         "/api/nots/nepse-data/market-open",         # also gives dummy_id
    "market_summary":      "/api/nots/market-summary/",
    "supply_demand":       "/api/nots/nepse-data/supplydemand",
    "top_gainers":         "/api/nots/top-ten/top-gainer",
    "top_losers":          "/api/nots/top-ten/top-loser",
    "top_turnover":        "/api/nots/top-ten/turnover",
    "top_trade":           "/api/nots/top-ten/trade",
    "top_transaction":     "/api/nots/top-ten/transaction",
    "nepse_index":         "/api/nots/nepse-index",
    "nepse_subindices":    "/api/nots",
    "live_market":         "/api/nots/lives-market",
    "company_list":        "/api/nots/company/list",
    "security_list":       "/api/nots/security?nonDelisted=true",
    "price_volume":        "/api/nots/securityDailyTradeStat/58",
    # price history: append /{security_id}?&size=500&startDate=X&endDate=Y
    "price_volume_history": "/api/nots/market/history/security/",
    # market depth: append /{security_id}/
    "market_depth":        "/api/nots/nepse-data/marketdepth/",
}

# ── POST endpoints (require {"id": payload_id} body) ─────────────────────────
POST_ENDPOINTS = {
    # payload type: "scrips"
    "today_price":         "/api/nots/nepse-data/today-price",
    "floor_sheet":         "/api/nots/nepse-data/floorsheet",
    # company details:  append /{security_id}
    "company_details":     "/api/nots/security/",
    # daily price graph: append /{security_id}
    "company_daily_graph": "/api/nots/market/graphdata/daily/",
    # floorsheet of company: append /{security_id}?&businessDate=X&size=500
    "company_floorsheet":  "/api/nots/security/floorsheet/",

    # payload type: "general"  (uses salt adjustment)
    "nepse_index_graph":              "/api/nots/graph/index/58",
    "sensitive_index_graph":          "/api/nots/graph/index/57",
    "float_index_graph":              "/api/nots/graph/index/62",
    "sensitive_float_index_graph":    "/api/nots/graph/index/63",
    "banking_subindex_graph":         "/api/nots/graph/index/51",
    "dev_bank_subindex_graph":        "/api/nots/graph/index/55",
    "finance_subindex_graph":         "/api/nots/graph/index/60",
    "hotel_tourism_subindex_graph":   "/api/nots/graph/index/52",
    "hydro_subindex_graph":           "/api/nots/graph/index/54",
    "investment_subindex_graph":      "/api/nots/graph/index/67",
    "life_insurance_subindex_graph":  "/api/nots/graph/index/65",
    "manufacturing_subindex_graph":   "/api/nots/graph/index/56",
    "microfinance_subindex_graph":    "/api/nots/graph/index/64",
    "mutual_fund_subindex_graph":     "/api/nots/graph/index/66",
    "non_life_insurance_subindex_graph": "/api/nots/graph/index/59",
    "others_subindex_graph":          "/api/nots/graph/index/53",
    "trading_subindex_graph":         "/api/nots/graph/index/61",
}

# Payload type per POST endpoint
# "scrips"  → getPOSTPayloadIDForScrips   (no salt adjustment)
# "general" → getPOSTPayloadID            (salt adjustment, threshold < 5)
# "floor"   → getPOSTPayloadIDForFloorSheet (salt adjustment, threshold < 4)
PAYLOAD_TYPE = {
    "today_price":         "floor",
    "floor_sheet":         "floor",
    "company_details":     "scrips",
    "company_daily_graph": "scrips",
    "company_floorsheet":  "floor",
    **{k: "general" for k in POST_ENDPOINTS if "graph" in k},
}
