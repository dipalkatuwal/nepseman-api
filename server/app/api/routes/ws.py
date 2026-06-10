"""
ws.py
-----
WebSocket endpoint for live NEPSE data streaming.

Connect: ws://localhost:8000/ws

Send a JSON message:
    { "route": "live_market" }
    { "route": "today_price" }
    { "route": "top_gainers" }
    { "route": "top_losers" }
    { "route": "top_turnover" }
    { "route": "nepse_index" }
    { "route": "market_status" }
    { "route": "market_depth", "symbol": "NABIL" }
    { "route": "company_details", "symbol": "NABIL" }

Server responds with JSON data or { "error": "..." }.

For continuous streaming, send { "route": "subscribe", "channel": "live_market", "interval": 10 }
"""

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services import nepse as svc

logger = logging.getLogger(__name__)
router = APIRouter(tags=["WebSocket"])

# Route → handler map
_ROUTES = {
    "live_market":    lambda _: svc.get_live_market(),
    "today_price":    lambda _: svc.get_today_price(),
    "top_gainers":    lambda _: svc.get_top_gainers(),
    "top_losers":     lambda _: svc.get_top_losers(),
    "top_turnover":   lambda _: svc.get_top_turnover(),
    "top_trade":      lambda _: svc.get_top_trade(),
    "top_transaction":lambda _: svc.get_top_transaction(),
    "nepse_index":    lambda _: svc.get_nepse_index(),
    "subindices":     lambda _: svc.get_nepse_subindices(),
    "market_status":  lambda _: svc.get_market_status(),
    "supply_demand":  lambda _: svc.get_supply_demand(),
    "company_list":   lambda _: svc.get_company_list(),
    "security_list":  lambda _: svc.get_security_list(),
    # Symbol-dependent
    "market_depth":   lambda msg: svc.get_market_depth(msg["symbol"]),
    "company_details":lambda msg: svc.get_company_details(msg["symbol"]),
    "price_history":  lambda msg: svc.get_price_history(
                            msg["symbol"],
                            msg.get("start_date"),
                            msg.get("end_date"),
                      ),
    "floor_sheet_of": lambda msg: svc.get_floor_sheet_of(msg["symbol"]),
}

_MIN_INTERVAL = 5    # seconds — don't allow spamming
_MAX_INTERVAL = 300


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info(f"WS connected: {websocket.client}")
    _subscriptions: dict[str, asyncio.Task] = {}

    async def _send(data):
        await websocket.send_text(json.dumps(data, default=str))

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await _send({"error": "Invalid JSON."})
                continue

            route = msg.get("route")

            # ── subscribe ──────────────────────────────────────────────────────
            if route == "subscribe":
                channel  = msg.get("channel")
                interval = max(_MIN_INTERVAL, min(_MAX_INTERVAL, int(msg.get("interval", 10))))

                if channel not in _ROUTES:
                    await _send({"error": f"Unknown channel '{channel}'."})
                    continue

                # Cancel existing subscription for this channel
                if channel in _subscriptions:
                    _subscriptions[channel].cancel()

                async def _stream(ch=channel, iv=interval, m=msg):
                    try:
                        while True:
                            try:
                                result = await _ROUTES[ch](m)
                                await _send({"channel": ch, "data": result})
                            except Exception as e:
                                await _send({"channel": ch, "error": str(e)})
                            await asyncio.sleep(iv)
                    except asyncio.CancelledError:
                        pass

                _subscriptions[channel] = asyncio.create_task(_stream())
                await _send({"subscribed": channel, "interval": interval})

            # ── unsubscribe ────────────────────────────────────────────────────
            elif route == "unsubscribe":
                channel = msg.get("channel")
                if channel in _subscriptions:
                    _subscriptions[channel].cancel()
                    del _subscriptions[channel]
                    await _send({"unsubscribed": channel})
                else:
                    await _send({"error": f"Not subscribed to '{channel}'."})

            # ── one-shot query ─────────────────────────────────────────────────
            elif route in _ROUTES:
                try:
                    result = await _ROUTES[route](msg)
                    await _send({"route": route, "data": result})
                except KeyError as e:
                    await _send({"error": f"Missing field: {e}"})
                except ValueError as e:
                    await _send({"error": str(e)})
                except Exception as e:
                    await _send({"error": str(e)})

            elif route == "ping":
                await _send({"pong": True})

            elif route == "routes":
                await _send({"available_routes": list(_ROUTES.keys())})

            else:
                await _send({
                    "error": f"Unknown route '{route}'.",
                    "available_routes": list(_ROUTES.keys()),
                })

    except WebSocketDisconnect:
        logger.info(f"WS disconnected: {websocket.client}")
    finally:
        for task in _subscriptions.values():
            task.cancel()
