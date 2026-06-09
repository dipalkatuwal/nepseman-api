"""
scripts/test_all.py
-------------------
Smoke test for every service function.
Run from repo root:  python scripts/test_all.py

Requires a Nepal IP — nepalstock.com geo-blocks foreign requests.
"""

import asyncio
import json
import sys
from datetime import date, timedelta

sys.path.insert(0, ".")

from app.services import nepse as svc

PASS = "✅"
FAIL = "❌"


def section(title):
    print(f"\n{'='*60}\n  {title}\n{'='*60}")


async def run(label, fn, *args, limit=2, **kwargs):
    try:
        result = await fn(*args, **kwargs)
        if isinstance(result, list):
            print(f"{PASS}  {label}  ({len(result)} records)")
            for item in result[:limit]:
                print("     ", json.dumps(item, default=str)[:120])
        elif isinstance(result, dict):
            print(f"{PASS}  {label}")
            print("     ", json.dumps(result, default=str)[:200])
        else:
            print(f"{PASS}  {label}  →  {result}")
        return result
    except Exception as e:
        print(f"{FAIL}  {label}")
        print(f"     {type(e).__name__}: {e}")
        return None


async def main():
    print("\n🇳🇵  nepseman-apiv2 — Full Service Test")
    print("  (needs Nepal IP)\n")

    TODAY    = date.today().strftime("%Y-%m-%d")
    YEAR_AGO = (date.today() - timedelta(days=365)).strftime("%Y-%m-%d")

    section("1. Market")
    await run("is_market_open",    svc.is_market_open)
    await run("get_market_status", svc.get_market_status)
    await run("get_market_summary",svc.get_market_summary)
    await run("get_supply_demand", svc.get_supply_demand)

    section("2. Prices")
    await run("get_today_price",    svc.get_today_price)
    await run("get_live_market",    svc.get_live_market)
    await run("get_price_volume",   svc.get_price_volume)
    await run("get_top_gainers",    svc.get_top_gainers)
    await run("get_top_losers",     svc.get_top_losers)
    await run("get_top_turnover",   svc.get_top_turnover)
    await run("get_top_trade",      svc.get_top_trade)
    await run("get_top_transaction",svc.get_top_transaction)

    section("3. Indices")
    await run("get_nepse_index",       svc.get_nepse_index)
    await run("get_nepse_subindices",  svc.get_nepse_subindices)
    await run("get_index_graph(nepse)",svc.get_index_graph, "nepse")
    await run("get_index_graph(banking)",svc.get_index_graph, "banking")

    section("4. Securities")
    await run("get_company_list",  svc.get_company_list)
    await run("get_security_list", svc.get_security_list)
    await run("get_sector_scrips", svc.get_sector_scrips)

    SYMBOL = "NABIL"
    print(f"\n  → Per-ticker tests using: {SYMBOL}")
    await run(f"get_company_details({SYMBOL})",   svc.get_company_details,  SYMBOL)
    await run(f"get_daily_scrip_graph({SYMBOL})", svc.get_daily_scrip_graph,SYMBOL)
    await run(f"get_price_history({SYMBOL})",     svc.get_price_history,    SYMBOL, YEAR_AGO, TODAY)
    await run(f"get_market_depth({SYMBOL})",      svc.get_market_depth,     SYMBOL)

    section("5. Floorsheet")
    await run("get_floor_sheet",            svc.get_floor_sheet)
    await run(f"get_floor_sheet_of({SYMBOL})", svc.get_floor_sheet_of, SYMBOL)

    print(f"\n{'='*60}\n  Done.\n{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(main())
