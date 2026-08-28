"""Simple swing-based support and resistance detection."""

from __future__ import annotations

import pandas as pd


class SupportResistanceCalculator:
    """Find recent swing levels and nearest levels around the current price."""

    def __init__(self, window: int = 2):
        if window < 1:
            raise ValueError("window must be positive")
        self.window = window

    def calculate(self, candles: pd.DataFrame) -> dict:
        required = {"high", "low", "close"}
        if not required.issubset(candles.columns):
            raise ValueError(f"candles must contain {sorted(required)}")
        if len(candles) < (self.window * 2 + 1):
            raise ValueError("not enough candles for swing detection")

        highs = candles["high"].astype(float)
        lows = candles["low"].astype(float)
        swing_highs: list[float] = []
        swing_lows: list[float] = []
        for index in range(self.window, len(candles) - self.window):
            high = highs.iloc[index]
            low = lows.iloc[index]
            if high >= highs.iloc[index - self.window:index + self.window + 1].max():
                swing_highs.append(float(high))
            if low <= lows.iloc[index - self.window:index + self.window + 1].min():
                swing_lows.append(float(low))

        price = float(candles["close"].iloc[-1])
        supports = sorted({level for level in swing_lows if level < price}, reverse=True)
        resistances = sorted({level for level in swing_highs if level > price})
        return {
            "support": supports[0] if supports else None,
            "resistance": resistances[0] if resistances else None,
            "supports": supports,
            "resistances": resistances,
        }
