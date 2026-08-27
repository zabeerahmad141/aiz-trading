"""
AngelOne SmartAPI Broker — Free live trading.
Get API key at: https://smartapi.angelone.in
"""
import pyotp
from typing import Literal
from loguru import logger
from SmartApi import SmartConnect

from app.services.broker.base import BrokerBase, OrderResult, Quote
from app.config import settings


class AngelOneBroker(BrokerBase):
    """
    AngelOne SmartAPI integration.
    Free API — supports NSE/BSE live data and order placement.

    Setup steps (see docs/MASTER.md Section 8):
    1. Open free AngelOne account at angelone.in
    2. Go to smartapi.angelone.in → Create App → Get API key
    3. Set ANGEL_API_KEY, ANGEL_CLIENT_ID, ANGEL_PASSWORD, ANGEL_TOTP_SECRET in .env
    """

    NSE_EXCHANGE = "NSE"
    PRODUCT_INTRADAY = "INTRADAY"

    def __init__(self):
        self.api = SmartConnect(api_key=settings.angel_api_key)
        self.session_data = None

    async def connect(self) -> bool:
        try:
            totp = pyotp.TOTP(settings.angel_totp_secret).now()
            self.session_data = self.api.generateSession(
                settings.angel_client_id,
                settings.angel_password,
                totp,
            )
            if self.session_data and self.session_data.get("status"):
                logger.info("AngelOne SmartAPI connected successfully.")
                return True
            logger.error(f"AngelOne login failed: {self.session_data}")
            return False
        except Exception as e:
            logger.error(f"AngelOne connection error: {e}")
            return False

    async def get_quote(self, symbol: str) -> Quote:
        try:
            data = self.api.ltpData(self.NSE_EXCHANGE, symbol, "")
            ltp = float(data.get("data", {}).get("ltp", 0))
            return Quote(
                symbol=symbol,
                ltp=ltp,
                open=0.0, high=0.0, low=0.0, close=0.0, volume=0,
                change_pct=0.0,
            )
        except Exception as e:
            logger.error(f"AngelOne quote error for {symbol}: {e}")
            raise

    async def place_order(
        self,
        symbol: str,
        action: Literal["buy", "sell"],
        quantity: int,
        order_type: str = "MARKET",
        price: float | None = None,
    ) -> OrderResult:
        order_params = {
            "variety": "NORMAL",
            "tradingsymbol": symbol,
            "symboltoken": "",  # Lookup from instrument list
            "transactiontype": action.upper(),
            "exchange": self.NSE_EXCHANGE,
            "ordertype": order_type,
            "producttype": self.PRODUCT_INTRADAY,
            "duration": "DAY",
            "price": str(price or 0),
            "squareoff": "0",
            "stoploss": "0",
            "quantity": str(quantity),
        }
        resp = self.api.placeOrder(order_params)
        order_id = resp.get("data", {}).get("orderid", "UNKNOWN")
        quote = await self.get_quote(symbol)

        return OrderResult(
            order_id=order_id,
            symbol=symbol,
            action=action,
            quantity=quantity,
            price=quote.ltp,
            status="executed",
            is_paper=False,
        )

    async def cancel_order(self, order_id: str) -> bool:
        self.api.cancelOrder(order_id, "NORMAL")
        return True

    async def get_positions(self) -> list[dict]:
        result = self.api.position()
        return result.get("data", []) or []

    async def get_balance(self) -> float:
        rms = self.api.rmsLimit()
        return float(rms.get("data", {}).get("availablecash", 0))

    async def is_market_open(self) -> bool:
        from datetime import datetime, time as dtime
        from zoneinfo import ZoneInfo
        now = datetime.now(ZoneInfo("Asia/Kolkata"))
        if now.weekday() >= 5:
            return False
        return dtime(9, 15) <= now.time() <= dtime(15, 30)
