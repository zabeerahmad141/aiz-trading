"""Deterministic OHLCV backtesting engine for Week 3."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass(frozen=True)
class BacktestConfig:
    initial_capital: float = 100000.0
    risk_per_trade_pct: float = 1.0
    stop_loss_pct: float = 1.5
    target_pct: float = 3.0
    commission_pct: float = 0.1


@dataclass
class BacktestResult:
    initial_capital: float
    final_capital: float
    total_return_pct: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate_pct: float
    max_drawdown_pct: float
    expectancy: float
    trades: list[dict] = field(default_factory=list)


class BacktestEngine:
    """Simulate long-only BUY/SELL signals on historical OHLCV data.

    A signal is executed at that candle's close. Stops and targets are checked
    against subsequent candle highs/lows, with stop loss taking precedence if
    both levels are touched in one candle.
    """

    def __init__(self, config: BacktestConfig | None = None):
        self.config = config or BacktestConfig()

    def run(self, candles: pd.DataFrame) -> BacktestResult:
        required = {"close", "high", "low", "signal"}
        missing = required.difference(candles.columns)
        if missing:
            raise ValueError(f"candles must contain {sorted(required)}")
        if self.config.initial_capital <= 0:
            raise ValueError("initial_capital must be positive")

        data = candles.reset_index(drop=False)
        cash = self.config.initial_capital
        position: dict | None = None
        completed: list[dict] = []
        equity_curve = [cash]

        for index, row in data.iterrows():
            close = float(row["close"])
            if close <= 0:
                continue
            if position is not None:
                exit_price, exit_reason = self._exit_price(position, row)
                if exit_price is not None:
                    pnl = (exit_price - position["entry_price"]) * position["quantity"]
                    commission = (position["entry_price"] * position["quantity"] + exit_price * position["quantity"]) * self.config.commission_pct / 100
                    pnl -= commission
                    cash += position["entry_price"] * position["quantity"] + pnl
                    completed.append({**position, "exit_price": exit_price, "exit_index": index, "exit_reason": exit_reason, "pnl": round(pnl, 2)})
                    position = None

            signal = str(row["signal"]).upper()
            if position is None and signal == "BUY":
                risk_per_share = close * self.config.stop_loss_pct / 100
                position_risk = cash * self.config.risk_per_trade_pct / 100
                quantity = int(position_risk / risk_per_share) if risk_per_share > 0 else 0
                quantity = min(quantity, int(cash / close))
                if quantity > 0:
                    position = {"entry_index": index, "entry_price": close, "quantity": quantity, "stop_loss": close - risk_per_share, "target": close * (1 + self.config.target_pct / 100)}
                    cash -= close * quantity
            equity = cash + (position["quantity"] * close if position else 0)
            equity_curve.append(equity)

        if position is not None:
            final_price = float(data.iloc[-1]["close"])
            pnl = (final_price - position["entry_price"]) * position["quantity"]
            cash += position["entry_price"] * position["quantity"] + pnl
            completed.append({**position, "exit_price": final_price, "exit_index": data.index[-1], "exit_reason": "end_of_data", "pnl": round(pnl, 2)})
            equity_curve.append(cash)

        final_capital = cash
        wins = sum(1 for trade in completed if trade["pnl"] > 0)
        losses = sum(1 for trade in completed if trade["pnl"] < 0)
        returns = [trade["pnl"] for trade in completed]
        peak = self.config.initial_capital
        max_drawdown = 0.0
        for equity in equity_curve:
            peak = max(peak, equity)
            max_drawdown = max(max_drawdown, (peak - equity) / peak * 100)
        return BacktestResult(self.config.initial_capital, round(final_capital, 2), round((final_capital / self.config.initial_capital - 1) * 100, 2), len(completed), wins, losses, round(wins / len(completed) * 100, 2) if completed else 0.0, round(max_drawdown, 2), round(sum(returns) / len(returns), 2) if returns else 0.0, completed)

    @staticmethod
    def _exit_price(position: dict, row: pd.Series) -> tuple[float | None, str]:
        if float(row["low"]) <= position["stop_loss"]:
            return position["stop_loss"], "stop_loss"
        if float(row["high"]) >= position["target"]:
            return position["target"], "target"
        if str(row["signal"]).upper() == "SELL":
            return float(row["close"]), "signal"
        return None, ""
