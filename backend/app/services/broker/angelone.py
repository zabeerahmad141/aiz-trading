"""Angel One SmartAPI broker adapter."""
import asyncio
from datetime import datetime, time as dtime
from typing import Literal, Optional
from zoneinfo import ZoneInfo

import pyotp
from SmartApi import SmartConnect
from loguru import logger

from app.config import settings
from app.services.broker.base import BrokerBase, OrderResult, Quote


class AngelOneBroker(BrokerBase):
    NSE_EXCHANGE = "NSE"
    PRODUCT_INTRADAY = "INTRADAY"

    def __init__(self):
        self.api = SmartConnect(api_key=settings.angel_api_key)
        self.session_data = None
        self.instrument_tokens: dict[str, str] = {}

    async def connect(self) -> bool:
        try:
            totp = pyotp.TOTP(settings.angel_totp_secret).now()
            self.session_data = await asyncio.to_thread(
                self.api.generateSession,
                settings.angel_client_id,
                settings.angel_password,
                totp,
            )
            if self.session_data and self.session_data.get("status"):
                logger.info("Angel One connected successfully")
                return True
            logger.error("Angel One login failed: {}", self.session_data)
        except Exception as exc:
            logger.error("Angel One connection error: {}", exc)
        return False

    async def _get_instrument_token(self, symbol: str) -> Optional[str]:
        symbol = symbol.strip().upper()
        if symbol in self.instrument_tokens:
            return self.instrument_tokens[symbol]
        try:
            instruments = await asyncio.to_thread(self.api.getInstrumentList)
            for instrument in instruments or []:
                if instrument.get("symbol") == symbol and instrument.get("exchange_type") == "NSE":
                    token = instrument.get("exchange_token")
                    if token:
                        self.instrument_tokens[symbol] = str(token)
                        return str(token)
        except Exception as exc:
            logger.error("Angel One instrument lookup failed for {}: {}", symbol, exc)
        return None

    async def get_quote(self, symbol: str) -> Quote:
        symbol = symbol.strip().upper()
        token = await self._get_instrument_token(symbol)
        if not token:
            raise ValueError(f"No Angel One instrument token found for {symbol}")
        response = await asyncio.to_thread(
            self.api.ltpData,
            mode="LTP",
            exchangeTokens={self.NSE_EXCHANGE: [token]},
        )
        fetched = response.get("data", {}).get("fetched", []) if response else []
        ltp = float(fetched[0].get("ltp", 0)) if fetched else 0.0
        if ltp <= 0:
            raise ValueError(f"No valid quote returned for {symbol}")
        return Quote(symbol=symbol, ltp=ltp, open=ltp, high=ltp, low=ltp, close=ltp, volume=0, change_pct=0.0)

    async def place_order(self, symbol: str, action: Literal["buy", "sell"], quantity: int, order_type: str = "MARKET", price: float | None = None) -> OrderResult:
        token = await self._get_instrument_token(symbol)
        if not token:
            raise ValueError(f"No Angel One instrument token found for {symbol}")
        order_params = {
            "variety": "NORMAL", "tradingsymbol": symbol.strip().upper(), "symboltoken": token,
            "transactiontype": action.upper(), "exchange": self.NSE_EXCHANGE, "ordertype": order_type,
            "producttype": self.PRODUCT_INTRADAY, "duration": "DAY", "price": str(price or 0),
            "squareoff": "0", "stoploss": "0", "quantity": str(quantity),
        }
        response = await asyncio.to_thread(self.api.placeOrder, order_params)
        order_id = response.get("data", {}).get("orderid") if response else None
        if not response or not response.get("status") or not order_id:
            raise ValueError(f"Angel One rejected order: {response}")
        fill = await self._wait_for_fill(str(order_id))
        if fill["status"] != "complete":
            raise ValueError(f"Angel One order {order_id} was {fill['status']}")
        execution_price = fill["price"] or price or (await self.get_quote(symbol)).ltp
        if execution_price <= 0:
            raise ValueError(f"No valid execution price returned for {symbol}")
        return OrderResult(str(order_id), symbol.strip().upper(), action, quantity, execution_price, "executed", False)

    async def _wait_for_fill(self, order_id: str) -> dict:
        for _ in range(10):
            try:
                response = await asyncio.to_thread(self.api.orderBook)
                for order in response.get("data", []) or []:
                    if str(order.get("orderid")) == order_id:
                        status = str(order.get("orderstatus", "")).lower()
                        if status in {"complete", "rejected", "cancelled"}:
                            return {"status": status, "price": float(order.get("averageprice") or 0)}
            except Exception as exc:
                logger.warning("Angel One order status lookup failed for {}: {}", order_id, exc)
            await asyncio.sleep(1)
        return {"status": "unknown", "price": 0.0}

    async def cancel_order(self, order_id: str) -> bool:
        response = await asyncio.to_thread(self.api.cancelOrder, order_id, "NORMAL")
        return bool(response and response.get("status"))

    async def get_positions(self) -> list[dict]:
        response = await asyncio.to_thread(self.api.position)
        return response.get("data", []) or []

    async def get_balance(self) -> float:
        response = await asyncio.to_thread(self.api.rmsLimit)
        return float(response.get("data", {}).get("availablecash", 0))

    async def is_market_open(self) -> bool:
        now = datetime.now(ZoneInfo("Asia/Kolkata"))
        return now.weekday() < 5 and dtime(9, 15) <= now.time() <= dtime(15, 30)
