"""
main.py
-------
nepseman-api — FastAPI application entry point.

Run with:  uvicorn app.main:app --reload --port 8000
"""

import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.routes import indices, market, meta, prices, securities
from app.api.routes.ws import router as ws_router
from app.core.cache import cache
from app.core.config import settings

# ── logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ── rate limiter ──────────────────────────────────────────────────────────────

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])

# ── lifespan ──────────────────────────────────────────────────────────────────

_startup_time = time.time()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀  nepseman-api starting up…")
    try:
        from app.core.session import get_session
        from app.core.symbols import all_symbols
        await get_session()
        await all_symbols()
        logger.info("✅  Session and symbol map warmed up.")
    except Exception as e:
        logger.warning(f"⚠️  Warm-up failed (geo-block?): {e}")
    yield
    try:
        from app.core.session import _session
        if _session:
            await _session.aclose()
    except Exception:
        pass
    logger.info("🛑  nepseman-api shutting down.")

# ── app ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="nepseman-api",
    description=(
        "**nepseman-api** — Unofficial, reverse-engineered REST + WebSocket API "
        "for NEPSE (Nepal Stock Exchange) market data.\n\n"
        "Scrapes and exposes live prices, indices, floor sheets, market depth, "
        "and security data by authenticating directly against nepalstock.com.np.\n\n"
        "**How it works:** Handles WASM-based token obfuscation and salt-based "
        "payload signing — all implemented from scratch without any third-party "
        "NEPSE library.\n\n"
        "⚠️ **Unofficial & unsupported** — not affiliated with NEPSE or "
        "nepalstock.com.np. Use at your own risk."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cache-Control middleware
@app.middleware("http")
async def add_cache_headers(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path.startswith("/api/v1"):
        if any(x in path for x in ["/live", "/depth", "/status", "/floorsheet"]):
            response.headers["Cache-Control"] = f"public, max-age={settings.CACHE_TTL_LIVE}"
        elif any(x in path for x in ["/companies", "/list", "/sectors"]):
            response.headers["Cache-Control"] = f"public, max-age={settings.CACHE_TTL_DEFAULT}"
        else:
            response.headers["Cache-Control"] = "public, max-age=60"
    return response

# ── routes ────────────────────────────────────────────────────────────────────

PREFIX = "/api/v1"

app.include_router(market.router,     prefix=PREFIX)
app.include_router(prices.router,     prefix=PREFIX)
app.include_router(indices.router,    prefix=PREFIX)
app.include_router(securities.router, prefix=PREFIX)
app.include_router(meta.router,       prefix=PREFIX)
app.include_router(ws_router)

# ── system endpoints ──────────────────────────────────────────────────────────

@app.get("/", tags=["System"])
def root():
    return {
        "service":     "nepseman-api",
        "description": "Unofficial reverse-engineered NEPSE data API",
        "version":     "1.0.0",
        "docs":        "/docs",
        "redoc":       "/redoc",
        "ws":          "/ws",
        "status":      "ok",
    }


@app.get("/health", tags=["System"])
async def health():
    from app.core.session import _session
    uptime_seconds = int(time.time() - _startup_time)

    last_sync = None
    if _session and _session.last_sync_at:
        last_sync = datetime.fromtimestamp(_session.last_sync_at, tz=timezone.utc).isoformat()

    return {
        "status":         "ok",
        "service":        "nepseman-api",
        "version":        "1.0.0",
        "uptime_seconds": uptime_seconds,
        "last_sync_at":   last_sync,
        "cache":          cache.stats(),
    }


@app.post("/cache/clear", tags=["System"])
async def clear_cache():
    cache.clear()
    return {"cleared": True}


# ── entry point ───────────────────────────────────────────────────────────────

def main():
    import sys

    import uvicorn
    print("\n┌──────────────────────────────────────────────┐", file=sys.stderr)
    print("│           nepseman-api v2.0.0                │", file=sys.stderr)
    print("│  Unofficial reverse-engineered NEPSE API     │", file=sys.stderr)
    print("├──────────────────────────────────────────────┤", file=sys.stderr)
    print("│  📖  Docs    →  http://localhost:8000/docs   │", file=sys.stderr)
    print("│  🔌  API     →  http://localhost:8000/api/v1 │", file=sys.stderr)
    print("│  ❤️   Health  →  http://localhost:8000/health │", file=sys.stderr)
    print("└──────────────────────────────────────────────┘\n", file=sys.stderr)
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()
