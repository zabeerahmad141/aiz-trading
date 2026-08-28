"""Market regime classification from trend and ATR percentage."""

from __future__ import annotations

import pandas as pd


class MarketRegimeDetector:
    """Classify conditions so unsuitable regimes can be filtered."""

    @staticmethod
    def detect_regime(
        candles: pd.DataFrame,
        atr_period: int = 14,
        max_volatility_pct: float = 5.0,
    ) -> str:
        required = {"high", "low", "close"}
        if not required.issubset(candles.columns):
            raise ValueError(f"candles must contain {sorted(required)}")
        if len(candles) < atr_period:
            raise ValueError(f"at least {atr_period} candles are required")

        close = candles["close"].astype(float)
        high = candles["high"].astype(float)
        low = candles["low"].astype(float)
        true_range = pd.concat(
            [high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()],
            axis=1,
        ).max(axis=1)
        atr = true_range.ewm(alpha=1 / atr_period, adjust=False, min_periods=atr_period).mean().iloc[-1]
        price = close.iloc[-1]
        if price <= 0:
            raise ValueError("latest close must be positive")
        if (atr / price) * 100 > max_volatility_pct:
            return "VOLATILE"

        fast = close.ewm(span=9, adjust=False).mean().iloc[-1]
        slow = close.ewm(span=21, adjust=False).mean().iloc[-1]
        if fast > slow and price > fast:
            return "TRENDING_UP"
        if fast < slow and price < fast:
            return "TRENDING_DOWN"
        return "SIDEWAYS"

    @staticmethod
    def get_strategy_adjustment(regime: str) -> dict[str, float | bool]:
        adjustments = {
            "TRENDING_UP": {"allow_buy": True, "allow_sell": False, "position_size_multiplier": 1.0, "take_profit_multiple": 3.0},
            "TRENDING_DOWN": {"allow_buy": False, "allow_sell": True, "position_size_multiplier": 0.8, "take_profit_multiple": 2.0},
            "SIDEWAYS": {"allow_buy": False, "allow_sell": False, "position_size_multiplier": 0.5, "take_profit_multiple": 1.5},
            "VOLATILE": {"allow_buy": False, "allow_sell": False, "position_size_multiplier": 0.3, "take_profit_multiple": 1.0},
        }
        return adjustments.get(regime, adjustments["SIDEWAYS"])
