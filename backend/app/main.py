from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from loguru import logger
import redis.asyncio as aioredis

from app.config import settings
from app.database import init_db, engine
from app.routers import auth, trading, market, portfolio, users, websocket
from app.core.startup import create_admin_user


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────
    logger.info("Starting AI Z Trading Engine...")
    await init_db()
    await create_admin_user()
    app.state.redis = await aioredis.from_url(settings.redis_url, decode_responses=True)
    logger.info("AI Z is ready.")
    yield
    # ── Shutdown ─────────────────────────────────────────────
    await app.state.redis.close()
    await engine.dispose()
    logger.info("AI Z shut down cleanly.")


app = FastAPI(
    title="AI Z Trading Engine",
    description="AI-powered automated trading platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.app_env == "development" else None,
    redoc_url=None,
)

# ── Middleware ────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ── Prometheus metrics ────────────────────────────────────────
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# ── Routers ───────────────────────────────────────────────────
app.include_router(auth.router,      prefix="/api/auth",      tags=["auth"])
app.include_router(trading.router,   prefix="/api/trading",   tags=["trading"])
app.include_router(market.router,    prefix="/api/market",    tags=["market"])
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["portfolio"])
app.include_router(users.router,     prefix="/api/users",     tags=["users"])
app.include_router(websocket.router, prefix="/ws",            tags=["websocket"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "aiz-backend", "version": "1.0.0"}


@app.get("/api/status")
async def api_status():
    """Public status endpoint — frontend uses this to verify API connection."""
    from datetime import datetime
    from zoneinfo import ZoneInfo
    ist_now = datetime.now(ZoneInfo("Asia/Kolkata"))
    weekday = ist_now.weekday()
    t = ist_now.time()
    from datetime import time as dtime
    market_open = weekday < 5 and dtime(9, 15) <= t <= dtime(15, 30)
    return {
        "api": "connected",
        "server_time_ist": ist_now.strftime("%Y-%m-%d %H:%M:%S IST"),
        "market_open": market_open,
        "weekday": ist_now.strftime("%A"),
        "broker": settings.active_broker,
        "trading_mode": settings.trading_mode,
    }
