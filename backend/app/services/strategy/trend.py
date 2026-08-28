"""Trend classification using configurable exponential moving averages."""

from __future__ import annotations

import pandas as pd


class TrendAnalyzer:
    """Classify price trend and check signal alignment."""

    @staticmethod
    def get_trend(
        candles: pd.DataFrame,
        fast_period: int = 9,
        slow_period: int = 21,
        long_period: int = 50,
    ) -> str:
        if not {"close"}.issubset(candles.columns):
            raise ValueError("candles must contain a close column")
        if len(candles) < long_period:
            raise ValueError(f"at least {long_period} candles are required")
        close = candles["close"].astype(float)
        fast = candles.get(f"ema_{fast_period}", close.ewm(span=fast_period, adjust=False).mean()).iloc[-1]
        slow = candles.get(f"ema_{slow_period}", close.ewm(span=slow_period, adjust=False).mean()).iloc[-1]
        long = candles.get(f"ema_{long_period}", close.ewm(span=long_period, adjust=False).mean()).iloc[-1]
        price = float(close.iloc[-1])

        if price > fast > slow > long:
            return "STRONG_BULLISH"
        if price > fast > slow:
            return "BULLISH"
        if price < fast < slow < long:
            return "STRONG_BEARISH"
        if price < fast < slow:
            return "BEARISH"
        return "NEUTRAL"

    @staticmethod
    def is_trend_aligned(trend: str, signal: str) -> bool:
        if signal.upper() == "BUY":
            return trend in {"BULLISH", "STRONG_BULLISH"}
        if signal.upper() == "SELL":
            return trend in {"BEARISH", "STRONG_BEARISH"}
        return signal.upper() == "HOLD"
