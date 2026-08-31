"""
Risk Manager — validates every trade before execution.

Protects capital with:
  - Maximum risk per trade
  - Maximum number of open positions
  - Stop-loss
  - Target
  - Daily loss circuit breaker
  - Duplicate position protection
  - SELL only when an existing position is available
"""

import os

from loguru import logger


MAX_RISK_PCT = float(
    os.getenv("MAX_RISK_PER_TRADE", "2")
)

MAX_POSITIONS = int(
    os.getenv("MAX_POSITIONS", "5")
)

STOP_LOSS_PCT = float(
    os.getenv("STOP_LOSS_PCT", "1.5")
)

TARGET_PCT = float(
    os.getenv("TARGET_PCT", "3.0")
)

ATR_STOP_MULTIPLIER = float(
    os.getenv("ATR_STOP_MULTIPLIER", "1.5")
)

ATR_TARGET_MULTIPLIER = float(
    os.getenv("ATR_TARGET_MULTIPLIER", "3.0")
)

DAILY_LOSS_LIMIT_PCT = float(
    os.getenv("DAILY_LOSS_LIMIT_PCT", "5.0")
)


class RiskManager:
    def __init__(self, capital: float):
        self.capital = capital
        self.daily_pnl = 0.0

        # symbol -> {
        #     "price": float,
        #     "quantity": int
        # }
        self.open_positions: dict[str, dict] = {}

    def approve_trade(
        self,
        symbol: str,
        signal: str,
        confidence: float,
        ltp: float,
        atr: float | None = None,
        min_confidence: float = 65.0,
    ) -> dict:
        """
        Validate an AI signal before execution.

        Returns:
            {
                approved,
                signal,
                quantity,
                stop_loss,
                target,
                order_value,
                reason
            }
        """

        symbol = symbol.strip().upper()
        signal = signal.strip().upper()

        # -----------------------------------------------------
        # 1. Validate price
        # -----------------------------------------------------
        if ltp <= 0:
            return self._reject(
                f"Invalid LTP: ₹{ltp}"
            )

        # -----------------------------------------------------
        # 2. Daily loss circuit breaker
        # -----------------------------------------------------
        daily_loss_limit = (
            self.capital *
            DAILY_LOSS_LIMIT_PCT /
            100
        )

        if self.daily_pnl <= -daily_loss_limit:
            return self._reject(
                f"Daily loss limit reached: "
                f"₹{self.daily_pnl:.2f}"
            )

        # -----------------------------------------------------
        # 3. HOLD = no trade
        # -----------------------------------------------------
        if signal == "HOLD":
            return self._reject(
                "HOLD signal — no action required"
            )

        # -----------------------------------------------------
        # 4. Validate signal
        # -----------------------------------------------------
        if signal not in ("BUY", "SELL"):
            return self._reject(
                f"Invalid signal: {signal}"
            )

        # -----------------------------------------------------
        # 5. Confidence check
        # -----------------------------------------------------
        if confidence < min_confidence:
            return self._reject(
                f"Confidence too low: "
                f"{confidence}% < {min_confidence}%"
            )

        # -----------------------------------------------------
        # 6. SELL
        #
        # Long-only strategy:
        # SELL is allowed only if we already own the symbol.
        # -----------------------------------------------------
        if signal == "SELL":

            if symbol not in self.open_positions:
                return self._reject(
                    f"No open position to sell: {symbol}"
                )

            position = self.open_positions[symbol]

            quantity = int(
                position["quantity"]
            )

            if quantity <= 0:
                return self._reject(
                    f"Invalid position quantity: "
                    f"{symbol}"
                )

            order_value = quantity * ltp

            logger.info(
                f"APPROVED SELL "
                f"{quantity}x {symbol} "
                f"@ ₹{ltp:.2f}"
            )

            return {
                "approved": True,
                "signal": "SELL",
                "quantity": quantity,
                "stop_loss": None,
                "target": None,
                "order_value": round(
                    order_value,
                    2,
                ),
                "reason": (
                    f"AI confidence: "
                    f"{confidence}%"
                ),
            }

        # -----------------------------------------------------
        # 7. BUY duplicate position check
        # -----------------------------------------------------
        if symbol in self.open_positions:
            return self._reject(
                f"Already have position in {symbol}"
            )

        # -----------------------------------------------------
        # 8. Maximum number of positions
        # -----------------------------------------------------
        if len(self.open_positions) >= MAX_POSITIONS:
            return self._reject(
                f"Max positions reached: "
                f"{MAX_POSITIONS}"
            )

        # -----------------------------------------------------
        # 9. Risk-based position sizing
        #
        # Example:
        # Capital = ₹100,000
        # Risk = 2%
        # Risk amount = ₹2,000
        # SL = 1.5%
        # -----------------------------------------------------
        risk_amount = (
            self.capital *
            MAX_RISK_PCT /
            100
        )

        stop_distance = (
            atr * ATR_STOP_MULTIPLIER
            if atr and atr > 0
            else ltp * STOP_LOSS_PCT / 100
        )

        if stop_distance <= 0:
            return self._reject(
                "Invalid stop-loss distance"
            )

        quantity = max(
            1,
            int(
                risk_amount /
                stop_distance
            ),
        )

        # -----------------------------------------------------
        # 10. Maximum capital allocation = 40%
        # -----------------------------------------------------
        max_order_value = (
            self.capital * 0.40
        )

        order_value = quantity * ltp

        if order_value > max_order_value:

            quantity = int(
                max_order_value / ltp
            )

            if quantity < 1:
                return self._reject(
                    f"Insufficient capital for "
                    f"{symbol} @ ₹{ltp:.2f}"
                )

            order_value = quantity * ltp

        # -----------------------------------------------------
        # 11. Stop loss
        # -----------------------------------------------------
        stop_loss = round(ltp - stop_distance, 2)

        # -----------------------------------------------------
        # 12. Target
        # -----------------------------------------------------
        target = round(
            ltp + (atr * ATR_TARGET_MULTIPLIER if atr and atr > 0 else ltp * TARGET_PCT / 100),
            2,
        )

        logger.info(
            f"APPROVED BUY "
            f"{quantity}x {symbol} "
            f"@ ₹{ltp:.2f} | "
            f"SL: ₹{stop_loss} | "
            f"Target: ₹{target} | "
            f"Value: ₹{order_value:.0f}"
        )

        return {
            "approved": True,
            "signal": "BUY",
            "quantity": quantity,
            "stop_loss": stop_loss,
            "target": target,
            "order_value": round(
                order_value,
                2,
            ),
            "reason": (
                f"AI confidence: "
                f"{confidence}%"
            ),
        }

    def record_trade(
        self,
        symbol: str,
        action: str,
        price: float,
        quantity: int,
    ):
        """
        Keep the in-memory risk state synchronized
        with executed trades.
        """

        symbol = symbol.strip().upper()
        action = action.strip().upper()

        if action == "BUY":

            self.open_positions[symbol] = {
                "price": price,
                "quantity": quantity,
            }

            logger.info(
                f"Risk position opened: "
                f"{symbol} | "
                f"Qty: {quantity} | "
                f"Entry: ₹{price:.2f}"
            )

        elif action == "SELL":

            if symbol not in self.open_positions:
                logger.warning(
                    f"Cannot record SELL — "
                    f"no risk position: {symbol}"
                )
                return

            entry = self.open_positions.pop(
                symbol
            )

            entry_quantity = int(
                entry["quantity"]
            )

            pnl = (
                price -
                entry["price"]
            ) * entry_quantity

            self.daily_pnl += pnl

            logger.info(
                f"Risk position closed: "
                f"{symbol} | "
                f"Entry: ₹{entry['price']:.2f} | "
                f"Exit: ₹{price:.2f} | "
                f"Qty: {entry_quantity} | "
                f"PnL: ₹{pnl:.2f} | "
                f"Daily PnL: ₹{self.daily_pnl:.2f}"
            )

    def _reject(
        self,
        reason: str,
    ) -> dict:

        logger.info(
            f"Trade REJECTED: {reason}"
        )

        return {
            "approved": False,
            "reason": reason,
        }
