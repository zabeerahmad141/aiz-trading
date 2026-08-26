"""
Risk Manager — validates every trade before execution.
Protects capital with position sizing, stop-loss, and drawdown limits.

Rules enforced:
  - Max % capital per trade
  - Max number of open positions
  - Stop-loss on every trade
  - Daily loss limit (circuit breaker)
"""
import os
from loguru import logger

MAX_RISK_PCT = float(os.getenv("MAX_RISK_PER_TRADE", "2"))   # % of capital
MAX_POSITIONS = int(os.getenv("MAX_POSITIONS", "5"))
STOP_LOSS_PCT = float(os.getenv("STOP_LOSS_PCT", "1.5"))
TARGET_PCT = float(os.getenv("TARGET_PCT", "3.0"))
DAILY_LOSS_LIMIT_PCT = 5.0   # Stop trading if daily loss exceeds 5%


class RiskManager:
    def __init__(self, capital: float):
        self.capital = capital
        self.daily_pnl = 0.0
        self.open_positions: dict[str, dict] = {}

    def approve_trade(
        self,
        symbol: str,
        signal: str,
        confidence: float,
        ltp: float,
        min_confidence: float = 65.0,
    ) -> dict:
        """
        Returns approval dict: {approved, quantity, stop_loss, target, reason}
        """
        # Check circuit breaker
        if self.daily_pnl < -(self.capital * DAILY_LOSS_LIMIT_PCT / 100):
            return self._reject(f"Daily loss limit reached: ₹{self.daily_pnl:.0f}")

        # Check signal confidence
        if confidence < min_confidence:
            return self._reject(f"Confidence too low: {confidence}% < {min_confidence}%")

        # Check max open positions
        if len(self.open_positions) >= MAX_POSITIONS and symbol not in self.open_positions:
            return self._reject(f"Max positions reached: {MAX_POSITIONS}")

        # Already have position — only allow opposite signal (exit)
        if signal == "BUY" and symbol in self.open_positions:
            return self._reject(f"Already have position in {symbol}")

        if signal == "HOLD":
            return self._reject("HOLD signal — no action required")

        # Position sizing: risk-based
        risk_amount = self.capital * (MAX_RISK_PCT / 100)
        stop_distance = ltp * (STOP_LOSS_PCT / 100)
        quantity = max(1, int(risk_amount / stop_distance))

        # Ensure we have capital for it
        order_value = quantity * ltp
        if order_value > self.capital * 0.4:  # Cap at 40% of capital per trade
            quantity = max(1, int((self.capital * 0.4) / ltp))
            order_value = quantity * ltp

        stop_loss = round(ltp * (1 - STOP_LOSS_PCT / 100), 2)
        target = round(ltp * (1 + TARGET_PCT / 100), 2)

        logger.info(
            f"APPROVED {signal} {quantity}x {symbol} @ ₹{ltp:.2f} | "
            f"SL: ₹{stop_loss} | Target: ₹{target} | Value: ₹{order_value:.0f}"
        )

        return {
            "approved": True,
            "signal": signal,
            "quantity": quantity,
            "stop_loss": stop_loss,
            "target": target,
            "order_value": round(order_value, 2),
            "reason": f"AI confidence: {confidence}%",
        }

    def record_trade(self, symbol: str, action: str, price: float, quantity: int):
        if action == "BUY":
            self.open_positions[symbol] = {"price": price, "quantity": quantity}
        elif action == "SELL":
            if symbol in self.open_positions:
                entry = self.open_positions.pop(symbol)
                pnl = (price - entry["price"]) * quantity
                self.daily_pnl += pnl

    def _reject(self, reason: str) -> dict:
        logger.info(f"Trade REJECTED: {reason}")
        return {"approved": False, "reason": reason}
