"""
Paper Trading Broker — simulates orders without real money.
Default mode. Switch to live by changing ACTIVE_BROKER in .env
"""
import uuid
from datetime import datetime, time as dtime
from typing import Literal
import yfinance as yf
from loguru import logger

from app.services.broker.base import BrokerBase, OrderResult, Quote
from app.config import settings


class PaperBroker(BrokerBase):
    """
    Simulated paper trading broker.
    Uses yfinance for real market data but never places real orders.
    Perfect for testing the AI engine safely.
    """

    def __init__(self):
        self.capital = settings.trading_capital
        self.positions: dict[str, dict] = {}
        self.order_history: list[dict] = []

    async def connect(self) -> bool:
        logger.info("Paper trading broker connected. No real money at risk.")
        return True

    async def get_quote(self, symbol: str) -> Quote:
        # Append .NS for NSE symbols
        ticker = yf.Ticker(f"{symbol}.NS")
        info = ticker.fast_info
        hist = ticker.history(period="1d", interval="1m")

        ltp = float(info.last_price) if hasattr(info, 'last_price') else 0.0
        open_p = float(hist['Open'].iloc[0]) if not hist.empty else ltp
        high = float(hist['High'].max()) if not hist.empty else ltp
        low = float(hist['Low'].min()) if not hist.empty else ltp
        close = float(hist['Close'].iloc[-1]) if not hist.empty else ltp
        volume = int(hist['Volume'].sum()) if not hist.empty else 0
        prev_close = float(info.previous_close) if hasattr(info, 'previous_close') and info.previous_close else ltp
        change_pct = ((ltp - prev_close) / prev_close * 100) if prev_close else 0.0

        return Quote(
            symbol=symbol,
            ltp=round(ltp, 2),
            open=round(open_p, 2),
            high=round(high, 2),
            low=round(low, 2),
            close=round(close, 2),
            volume=volume,
            change_pct=round(change_pct, 2),
        )

    async def place_order(
        self,
        symbol: str,
        action: Literal["buy", "sell"],
        quantity: int,
        order_type: str = "MARKET",
        price: float | None = None,
    ) -> OrderResult:
        quote = await self.get_quote(symbol)
        exec_price = price or quote.ltp
        order_id = str(uuid.uuid4())[:12].upper()
        cost = exec_price * quantity

        if action == "buy":
            if cost > self.capital:
                raise ValueError(f"Insufficient paper capital: need ₹{cost:.0f}, have ₹{self.capital:.0f}")
            self.capital -= cost
            self.positions[symbol] = {
                "quantity": quantity,
                "avg_price": exec_price,
                "opened_at": datetime.utcnow().isoformat(),
            }
            logger.info(f"[PAPER] BUY {quantity}x {symbol} @ ₹{exec_price:.2f} | Order: {order_id}")
        else:
            self.positions.pop(symbol, None)
            self.capital += cost
            logger.info(f"[PAPER] SELL {quantity}x {symbol} @ ₹{exec_price:.2f} | Order: {order_id}")

        result = OrderResult(
            order_id=order_id,
            symbol=symbol,
            action=action,
            quantity=quantity,
            price=exec_price,
            status="executed",
            is_paper=True,
        )
        self.order_history.append(result.__dict__)
        return result

    async def cancel_order(self, order_id: str) -> bool:
        logger.info(f"[PAPER] Cancel order {order_id}")
        return True

    async def get_positions(self) -> list[dict]:
        return [{"symbol": k, **v} for k, v in self.positions.items()]

    async def get_balance(self) -> float:
        return round(self.capital, 2)

    async def is_market_open(self) -> bool:
        now = datetime.now()
        if now.weekday() >= 5:  # Saturday/Sunday
            return False
        open_t = dtime(9, 15)
        close_t = dtime(15, 30)
        current = now.time()
        return open_t <= current <= close_t
