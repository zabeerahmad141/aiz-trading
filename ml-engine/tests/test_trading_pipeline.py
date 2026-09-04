import pandas as pd

from src.backtesting.engine import BacktestConfig, BacktestEngine
from src.trading.risk_manager import RiskManager


def test_risk_manager_sizes_atr_trade_and_rejects_hold():
    manager = RiskManager(capital=100000)
    decision = manager.approve_trade("RELIANCE", "BUY", 80, 100, atr=2)

    assert decision["approved"] is True
    assert decision["quantity"] == 400
    assert decision["stop_loss"] == 97.0
    assert decision["target"] == 106.0

    hold = manager.approve_trade("RELIANCE", "HOLD", 99, 100, atr=2)
    assert hold["approved"] is False


def test_risk_manager_blocks_sell_without_position():
    manager = RiskManager(capital=100000)
    decision = manager.approve_trade("TCS", "SELL", 90, 100)
    assert decision["approved"] is False
    assert "No open position" in decision["reason"]


def test_backtest_respects_stop_before_target_and_reports_result():
    candles = pd.DataFrame({
        "close": [100, 101, 98, 100],
        "high": [100, 102, 103, 100],
        "low": [100, 99, 97, 100],
        "signal": ["BUY", "HOLD", "HOLD", "HOLD"],
    })
    result = BacktestEngine(BacktestConfig(
        initial_capital=10000,
        risk_per_trade_pct=1,
        stop_loss_pct=1,
        target_pct=2,
        commission_pct=0,
    )).run(candles)

    assert result.total_trades == 1
    assert result.losing_trades == 1
    assert result.trades[0]["exit_reason"] == "stop_loss"
    assert result.final_capital < result.initial_capital


def test_risk_manager_persists_and_restores_state(tmp_path):
    manager = RiskManager(capital=100000)
    manager.state_path = tmp_path / "risk_state.json"
    manager.open_positions["RELIANCE"] = {"price": 100.0, "quantity": 10}
    manager.daily_pnl = -250.0
    manager.persist_state()

    restored = RiskManager(capital=100000)
    restored.state_path = manager.state_path
    restored.restore_state()
    assert restored.daily_pnl == -250.0
    assert restored.open_positions["RELIANCE"]["quantity"] == 10