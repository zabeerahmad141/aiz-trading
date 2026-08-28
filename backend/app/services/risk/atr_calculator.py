"""ATR-based volatility, stop-loss, and target calculations."""

from __future__ import annotations

import pandas as pd


class ATRCalculator:
    """Calculate Wilder-style ATR values from OHLCV candles."""

    @staticmethod
    def calculate_atr(candles: pd.DataFrame, period: int = 14) -> float:
        if period < 1:
            raise ValueError("period must be positive")
        required = {"high", "low", "close"}
        missing = required.difference(candles.columns)
        if missing:
            raise ValueError(f"missing candle columns: {sorted(missing)}")
        if len(candles) < period:
            raise ValueError(f"at least {period} candles are required")

        high = candles["high"].astype(float)
        low = candles["low"].astype(float)
        close = candles["close"].astype(float)
        true_range = pd.concat(
            [high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()],
            axis=1,
        ).max(axis=1)
        return float(true_range.ewm(alpha=1 / period, adjust=False, min_periods=period).mean().iloc[-1])

    @staticmethod
    def get_atr_stop(entry: float, atr: float, multiplier: float = 1.5, side: str = "buy") -> float:
        distance = ATRCalculator._distance(atr, multiplier)
        normalized_side = side.lower()
        if normalized_side == "buy":
            return entry - distance
        if normalized_side == "sell":
            return entry + distance
        raise ValueError("side must be 'buy' or 'sell'")

    @staticmethod
    def get_atr_target(entry: float, atr: float, multiplier: float = 3.0, side: str = "buy") -> float:
        distance = ATRCalculator._distance(atr, multiplier)
        normalized_side = side.lower()
        if normalized_side == "buy":
            return entry + distance
        if normalized_side == "sell":
            return entry - distance
        raise ValueError("side must be 'buy' or 'sell'")

    @staticmethod
    def get_atr_percentage(atr: float, price: float) -> float:
        if price <= 0:
            raise ValueError("price must be positive")
        return (atr / price) * 100

    @staticmethod
    def _distance(atr: float, multiplier: float) -> float:
        if atr <= 0 or multiplier <= 0:
            raise ValueError("atr and multiplier must be positive")
        return atr * multiplier
