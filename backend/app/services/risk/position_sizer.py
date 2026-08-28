"""Risk-based position sizing."""

from __future__ import annotations


class PositionSizer:
    """Size a position from account risk and a protective stop."""

    @staticmethod
    def calculate_quantity(
        capital: float,
        risk_percent: float,
        entry_price: float,
        stop_loss_price: float,
        max_capital_allocation: float = 20.0,
        min_quantity: int = 0,
        max_quantity: int | None = None,
    ) -> int:
        if capital <= 0 or entry_price <= 0:
            return 0
        if risk_percent <= 0 or max_capital_allocation <= 0:
            return 0
        risk_per_share = abs(entry_price - stop_loss_price)
        if risk_per_share <= 0:
            return 0

        risk_amount = capital * (risk_percent / 100)
        quantity_by_risk = int(risk_amount / risk_per_share)
        quantity_by_capital = int((capital * max_capital_allocation / 100) / entry_price)
        quantity = min(quantity_by_risk, quantity_by_capital)
        if max_quantity is not None:
            quantity = min(quantity, max_quantity)
        return max(quantity, min_quantity if quantity >= min_quantity else 0)
