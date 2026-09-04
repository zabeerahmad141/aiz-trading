"""
WebSocket endpoint — streams live market data, AI signals,
and trade events to the frontend dashboard in real-time.
"""
import asyncio
import json
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger

from app.services.broker import get_active_broker
from app.config import settings

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        self.active.discard(ws) if hasattr(self.active, 'discard') else None
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, data: dict):
        dead = []
        for ws in self.active:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()
_quote_cache: list[dict] = []
_quote_cache_at = 0.0
_quote_cache_lock = asyncio.Lock()


async def _get_shared_quotes() -> list[dict]:
    global _quote_cache_at, _quote_cache
    now = asyncio.get_running_loop().time()
    if now - _quote_cache_at < 5:
        return _quote_cache
    async with _quote_cache_lock:
        now = asyncio.get_running_loop().time()
        if now - _quote_cache_at < 5:
            return _quote_cache
        broker = await get_active_broker()
        refreshed = []
        for symbol in settings.watchlist_symbols[:5]:
            try:
                q = await asyncio.wait_for(broker.get_quote(symbol), timeout=8)
                refreshed.append({"symbol": q.symbol, "ltp": q.ltp, "change_pct": q.change_pct, "volume": q.volume})
            except Exception as exc:
                logger.warning("WebSocket quote unavailable for {}: {}", symbol, exc)
        _quote_cache = refreshed
        _quote_cache_at = now
        return _quote_cache


@router.websocket("/live")
async def websocket_live(ws: WebSocket):
    await manager.connect(ws)
    logger.info(f"WebSocket client connected. Total: {len(manager.active)}")
    try:
        while True:
            quotes = await _get_shared_quotes()
            broker = await get_active_broker()

            await manager.broadcast({
                "type": "market_update",
                "timestamp": datetime.utcnow().isoformat(),
                "quotes": quotes,
                "market_open": await broker.is_market_open(),
            })
            await asyncio.sleep(3)  # Push update every 3 seconds
    except WebSocketDisconnect:
        manager.disconnect(ws)
        logger.info(f"WebSocket client disconnected. Remaining: {len(manager.active)}")


async def broadcast_trade_event(event_type: str, data: dict):
    """Called by the trading engine to push trade events to all clients."""
    await manager.broadcast({"type": event_type, "data": data, "timestamp": datetime.utcnow().isoformat()})
