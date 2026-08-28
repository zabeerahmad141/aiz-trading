"""Multi-confirmation entry validation for strategy signals."""

from __future__ import annotations

import pandas as pd


class EntryValidator:
    """Score BUY and SELL setups from enriched OHLCV candles."""

    def __init__(self, min_score: int = 60, volume_threshold: float = 1.5):
        self.min_score = min_score
        self.volume_threshold = volume_threshold

    def validate_buy_setup(self, candles: pd.DataFrame) -> dict:
        return self._validate(candles, "BUY")

    def validate_sell_setup(self, candles: pd.DataFrame) -> dict:
        return self._validate(candles, "SELL")

    def _validate(self, candles: pd.DataFrame, side: str) -> dict:
        required = {"close", "volume"}
        missing = required.difference(candles.columns)
        if missing:
            raise ValueError(f"missing entry columns: {sorted(missing)}")
        if len(candles) < 2:
            raise ValueError("at least two candles are required")

        latest = candles.iloc[-1]
        previous = candles.iloc[-2]
        close = float(latest["close"])
        close_previous = float(previous["close"])
        fast = self._indicator(candles, "ema_9", 9)
        slow = self._indicator(candles, "ema_21", 21)
        score = 0
        reasons: list[str] = []

        trend_ok = close > fast > slow if side == "BUY" else close < fast < slow
        score, reasons = self._record(score, reasons, trend_ok, 25, f"{side.title()} trend aligned", "Trend not aligned")

        if "rsi" in candles:
            rsi = float(latest["rsi"])
            momentum_ok = 35 <= rsi <= 65
            score, reasons = self._record(score, reasons, momentum_ok, 20, f"RSI {rsi:.1f} in entry range", f"RSI {rsi:.1f} outside entry range")
        else:
            reasons.append("RSI unavailable")

        if "macd" in candles and "macd_signal" in candles:
            macd_ok = float(latest["macd"]) > float(latest["macd_signal"]) if side == "BUY" else float(latest["macd"]) < float(latest["macd_signal"])
            score, reasons = self._record(score, reasons, macd_ok, 20, "MACD confirms direction", "MACD does not confirm direction")
        else:
            reasons.append("MACD unavailable")

        average_volume = candles["volume"].astype(float).tail(20).mean()
        volume_ratio = float(latest["volume"]) / average_volume if average_volume > 0 else 0.0
        volume_ok = volume_ratio >= self.volume_threshold
        score, reasons = self._record(score, reasons, volume_ok, 20, f"Volume {volume_ratio:.1f}x average", f"Volume {volume_ratio:.1f}x average")

        price_action_ok = close > close_previous if side == "BUY" else close < close_previous
        score, reasons = self._record(score, reasons, price_action_ok, 15, "Price action confirms direction", "Price action does not confirm direction")

        return {"valid": score >= self.min_score, "score": score, "side": side, "reasons": reasons, "volume_ratio": round(volume_ratio, 2)}

    @staticmethod
    def _indicator(candles: pd.DataFrame, column: str, period: int) -> float:
        if column in candles:
            return float(candles[column].iloc[-1])
        return float(candles["close"].ewm(span=period, adjust=False).mean().iloc[-1])

    @staticmethod
    def _record(score: int, reasons: list[str], valid: bool, points: int, success: str, failure: str) -> tuple[int, list[str]]:
        if valid:
            score += points
            reasons.append(success)
        else:
            reasons.append(failure)
        return score, reasons
