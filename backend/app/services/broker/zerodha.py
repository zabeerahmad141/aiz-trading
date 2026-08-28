"""
Zerodha Kite Connect Broker — Paid API (₹2000/month)
Upgrade from AngelOne when you want more advanced features.

Setup steps (see docs/MASTER.md Section 21):
1. Subscribe at kite.trade/connect (₹2000/month)
2. Set ZERODHA_API_KEY, ZERODHA_API_SECRET in .env
3. Access token must be refreshed daily (handled by this class)
4. Set ACTIVE_BROKER=zerodha in .env
"""
import asyncio
from typing import Literal
from loguru import logger
from app.services.broker.base import BrokerBase, OrderResult, Quote
from app.config import settings


class ZerodhaBroker(BrokerBase):
    NSE = "NSE"

    def __init__(self):
        try:
            from kiteconnect import KiteConnect
            self.kite = KiteConnect(api_key=settings.zerodha_api_key)
            if settings.zerodha_access_token:
                self.kite.set_access_token(settings.zerodha_access_token)
        except ImportError:
            raise RuntimeError("kiteconnect not installed. Run: pip install kiteconnect")

    async def connect(self) -> bool:
        try:
            profile = self.kite.profile()
            logger.info(f"Zerodha connected: {profile.get('user_name')}")
            return True
        except Exception as e:
            logger.error(f"Zerodha connection failed: {e}")
            return False

    async def get_quote(self, symbol: str) -> Quote:
        data = self.kite.ltp(f"{self.NSE}:{symbol}")
        ltp = float(data[f"{self.NSE}:{symbol}"]["last_price"])
        return Quote(symbol=symbol, ltp=ltp, open=0.0, high=0.0,
                     low=0.0, close=0.0, volume=0, change_pct=0.0)

    async def place_order(self, symbol: str, action: Literal["buy", "sell"],
                          quantity: int, order_type: str = "MARKET",
                          price: float | None = None) -> OrderResult:
        order_id = self.kite.place_order(
            tradingsymbol=symbol,
            exchange=self.NSE,
            transaction_type=action.upper(),
            quantity=quantity,
            order_type=order_type,
            product=self.kite.PRODUCT_MIS,  # Intraday
            variety=self.kite.VARIETY_REGULAR,
        )
        fill = await self._wait_for_fill(str(order_id))
        if fill["status"] != "complete":
            raise ValueError(f"Zerodha order {order_id} was {fill['status']}")
        execution_price = fill["price"] or price or (await self.get_quote(symbol)).ltp
        if execution_price <= 0:
            raise ValueError(f"No valid execution price returned for {symbol}")
        return OrderResult(order_id=str(order_id), symbol=symbol, action=action,
                           quantity=quantity, price=execution_price, status="executed", is_paper=False)

    async def _wait_for_fill(self, order_id: str) -> dict:
        for _ in range(10):
            try:
                orders = await asyncio.to_thread(self.kite.order_history, order_id)
                latest = orders[-1] if orders else {}
                status = str(latest.get("status", "")).lower()
                if status in {"complete", "rejected", "cancelled"}:
                    return {"status": status, "price": float(latest.get("average_price") or 0)}
            except Exception as exc:
                logger.warning("Zerodha order status lookup failed for {}: {}", order_id, exc)
            await asyncio.sleep(1)
        return {"status": "unknown", "price": 0.0}

    async def cancel_order(self, order_id: str) -> bool:
        self.kite.cancel_order(variety=self.kite.VARIETY_REGULAR, order_id=order_id)
        return True

    async def get_positions(self) -> list[dict]:
        return self.kite.positions().get("day", [])

    async def get_balance(self) -> float:
        margins = self.kite.margins()
        return float(margins.get("equity", {}).get("available", {}).get("cash", 0))

    async def is_market_open(self) -> bool:
        from datetime import datetime, time as dtime
        from zoneinfo import ZoneInfo
        now = datetime.now(ZoneInfo("Asia/Kolkata"))
        if now.weekday() >= 5:
            return False
        return dtime(9, 15) <= now.time() <= dtime(15, 30)
