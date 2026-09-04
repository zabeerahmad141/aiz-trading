import pandas as pd

from app.services.risk.atr_calculator import ATRCalculator
from app.services.risk.position_sizer import PositionSizer
from app.services.risk.risk_validator import RiskValidator
from app.services.strategy.entry_validator import EntryValidator
from app.services.strategy.market_regime import MarketRegimeDetector


def _candles() -> pd.DataFrame:
    close = [100, 101, 102, 103, 104, 105, 106, 107, 108, 109]
    return pd.DataFrame({
        "open": [value - 0.5 for value in close],
        "high": [value + 1 for value in close],
        "low": [value - 1 for value in close],
        "close": close,
        "volume": [100] * len(close),
    })


def test_atr_stop_and_target_follow_trade_side():
    assert ATRCalculator.get_atr_stop(100, 2, side="buy") == 97
    assert ATRCalculator.get_atr_target(100, 2, side="buy") == 106
    assert ATRCalculator.get_atr_stop(100, 2, side="sell") == 103
    assert ATRCalculator.get_atr_target(100, 2, side="sell") == 94


def test_position_sizing_respects_risk_and_capital_limits():
    quantity = PositionSizer.calculate_quantity(100000, 1, 100, 95, max_capital_allocation=20)
    assert quantity == 200


def test_risk_validator_rejects_bad_reward_ratio():
    result = RiskValidator(1.5).validate(100, 95, 105, "BUY")
    assert result["valid"] is False
    assert result["risk_reward"] == 1.0


def test_entry_validator_requires_multiple_confirmations():
    candles = _candles()
    candles["ema_9"] = candles["close"] - 1
    candles["ema_21"] = candles["close"] - 2
    candles["rsi"] = 50
    candles["macd"] = 2
    candles["macd_signal"] = 1
    result = EntryValidator(volume_threshold=1).validate_buy_setup(candles)
    assert result["valid"] is True
    assert result["score"] == 100


def test_market_regime_detects_uptrend():
    assert MarketRegimeDetector.detect_regime(_candles(), atr_period=3) == "TRENDING_UP"