"""Convert an ML signal and candles into a risk-aware trade decision."""

from __future__ import annotations

import pandas as pd

from app.services.risk import ATRCalculator, PositionSizer, RiskValidator
from .entry_validator import EntryValidator
from .market_regime import MarketRegimeDetector


class SignalProcessor:
    """Apply deterministic strategy and risk gates before execution."""

    def __init__(self, settings):
        self.settings = settings
        self.atr = ATRCalculator()
        self.entry_validator = EntryValidator(
            min_score=getattr(settings, "min_entry_score", 60),
            volume_threshold=getattr(settings, "min_volume_ratio", 1.5),
        )
        self.regime_detector = MarketRegimeDetector()
        self.risk_validator = RiskValidator(
            minimum_risk_reward=getattr(settings, "min_risk_reward_ratio", 1.5)
        )

    def process(self, signal: dict, candles: pd.DataFrame, capital: float) -> dict:
        action = str(signal.get("signal", "HOLD")).upper()
        entry = float(signal.get("ltp", 0))
        result = {"approved": False, "symbol": signal.get("symbol"), "signal": action, "reason": ""}
        if action not in {"BUY", "SELL"}:
            result["reason"] = "Only BUY and SELL signals can be traded"
            return result
        if entry <= 0:
            result["reason"] = "Signal has no valid entry price"
            return result

        regime = self.regime_detector.detect_regime(
            candles,
            atr_period=getattr(self.settings, "atr_period", 14),
            max_volatility_pct=getattr(self.settings, "max_volatility_pct", 5.0),
        )
        if regime == "VOLATILE":
            result["reason"] = "Trading blocked in volatile regime"
            result["regime"] = regime
            return result
        if action == "BUY" and regime != "TRENDING_UP":
            result["reason"] = f"BUY not allowed in {regime} regime"
            result["regime"] = regime
            return result
        if action == "SELL" and regime != "TRENDING_DOWN":
            result["reason"] = f"SELL not allowed in {regime} regime"
            result["regime"] = regime
            return result

        entry_result = self.entry_validator._validate(candles, action)
        if not entry_result["valid"]:
            result.update({"reason": "Entry score below threshold", "entry_score": entry_result["score"], "regime": regime})
            return result

        atr = self.atr.calculate_atr(candles, getattr(self.settings, "atr_period", 14))
        stop = self.atr.get_atr_stop(entry, atr, getattr(self.settings, "atr_stop_multiplier", 1.5), action.lower())
        target = self.atr.get_atr_target(entry, atr, getattr(self.settings, "atr_target_multiplier", 3.0), action.lower())
        risk = self.risk_validator.validate(entry, stop, target, action)
        if not risk["valid"]:
            result.update({"reason": risk["reason"], "regime": regime, "entry_score": entry_result["score"]})
            return result

        quantity = PositionSizer.calculate_quantity(
            capital,
            getattr(self.settings, "risk_percent_per_trade", 1.0),
            entry,
            stop,
            getattr(self.settings, "max_capital_allocation_pct", 20.0),
            max_quantity=getattr(self.settings, "max_position_size", None),
        )
        if quantity <= 0:
            result["reason"] = "Position size is zero"
            return result
        result.update({"approved": True, "quantity": quantity, "ltp": entry, "stop_loss": round(stop, 2), "target": round(target, 2), "atr": round(atr, 4), "regime": regime, "entry_score": entry_result["score"], "risk_reward": risk["risk_reward"], "reason": "Strategy and risk checks passed"})
        return result
