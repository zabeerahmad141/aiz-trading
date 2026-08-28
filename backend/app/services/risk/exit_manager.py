"""ATR-based position exit decisions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time


@dataclass(frozen=True)
class ExitDecision:
    should_exit: bool
    reason: str
    exit_price: float | None = None
    trailing_stop: float | None = None


class ExitManager:
    """Evaluate stop, target, trailing-stop, and square-off conditions."""

    def __init__(self, trailing_multiplier: float = 2.0, square_off: time = time(15, 20)):
        self.trailing_multiplier = trailing_multiplier
        self.square_off = square_off

    def evaluate(
        self,
        side: str,
        entry_price: float,
        current_price: float,
        stop_loss: float,
        target: float,
        atr: float | None = None,
        now: datetime | None = None,
    ) -> ExitDecision:
        if min(entry_price, current_price, stop_loss, target) <= 0:
            raise ValueError("all prices must be positive")
        side = side.upper()
        if side not in {"BUY", "SELL"}:
            raise ValueError("side must be BUY or SELL")

        if side == "BUY":
            if current_price <= stop_loss:
                return ExitDecision(True, "stop_loss", current_price)
            if current_price >= target:
                return ExitDecision(True, "target", current_price)
            trailing = current_price - atr * self.trailing_multiplier if atr and atr > 0 else None
        else:
            if current_price >= stop_loss:
                return ExitDecision(True, "stop_loss", current_price)
            if current_price <= target:
                return ExitDecision(True, "target", current_price)
            trailing = current_price + atr * self.trailing_multiplier if atr and atr > 0 else None

        if now and now.time() >= self.square_off:
            return ExitDecision(True, "square_off", current_price, trailing)
        return ExitDecision(False, "hold", None, trailing)
