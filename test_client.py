"""
test_client.py
--------------
Manual end-to-end test for the nepseman_api package.
Tests all available API methods against live NEPSE data.

Run:
    python test_client.py
"""

import asyncio
from nepseman_api import NepseClient


async def test(label: str, coro):
    try:
        result = await coro
        if result:
            print(f"  ✅  {label}")
        else:
            print(f"  ⚠️  {label} — returned empty")
    except Exception as e:
        print(f"  ❌  {label} — {e}")


async def main():
    print("\n🚀  nepseman_api end-to-end test\n")

    async with NepseClient() as nepse:

        print("── Market ──────────────────────────────────")
        await test("market_status",       nepse.market_status())
        await test("market_summary",      nepse.market_summary())
        await test("supply_demand",       nepse.supply_demand())

        print("\n── Prices ──────────────────────────────────")
        await test("today_price",         nepse.today_price())
        await test("live_market",         nepse.live_market())
        await test("price_volume",        nepse.price_volume())

        print("\n── Top Lists ───────────────────────────────")
        await test("top_gainers",         nepse.top_gainers())
        await test("top_losers",          nepse.top_losers())
        await test("top_turnover",        nepse.top_turnover())
        await test("top_trade",           nepse.top_trade())
        await test("top_transaction",     nepse.top_transaction())

        print("\n── Indices ─────────────────────────────────")
        await test("nepse_index",         nepse.nepse_index())
        await test("nepse_subindices",    nepse.nepse_subindices())

        print("\n── Securities ──────────────────────────────")
        await test("company_list",        nepse.company_list())
        await test("security_list",       nepse.security_list())
        await test("company_details(NABIL)", nepse.company_details("NABIL"))
        await test("price_history(NABIL)",   nepse.price_history("NABIL"))
        await test("market_depth(NABIL)",    nepse.market_depth("NABIL"))

        print("\n── Floorsheet ──────────────────────────────")
        await test("floor_sheet",         nepse.floor_sheet())
        await test("floor_sheet_of(NABIL)", nepse.floor_sheet_of("NABIL"))

    print("\n✅  Done\n")


if __name__ == "__main__":
    asyncio.run(main())