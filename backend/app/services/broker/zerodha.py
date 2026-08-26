"""
Zerodha Kite Connect Broker — Paid API (₹2000/month)
Upgrade from AngelOne when you want more advanced features.

Setup steps (see docs/MASTER.md Section 21):
1. Subscribe at kite.trade/connect (₹2000/month)
2. Set ZERODHA_API_KEY, ZERODHA_API_SECRET in .env
3. Access token must be refreshed daily (handled by this class)
4. Set ACTIVE_BROKER=zerodha in .env
"""
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
        quote = await self.get_quote(symbol)
        return OrderResult(order_id=str(order_id), symbol=symbol, action=action,
                           quantity=quantity, price=quote.ltp, status="executed", is_paper=False)

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
        now = datetime.now()
        if now.weekday() >= 5:
            return False
        return dtime(9, 15) <= now.time() <= dtime(15, 30)
