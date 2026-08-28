"""Historical candle loading and validation for backtests."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = {"close", "high", "low", "signal"}


def load_candles(source: str | Path | pd.DataFrame) -> pd.DataFrame:
    """Load candles from a DataFrame or CSV and validate the backtest schema."""
    if isinstance(source, pd.DataFrame):
        candles = source.copy()
    else:
        candles = pd.read_csv(source)
    missing = REQUIRED_COLUMNS.difference(candles.columns)
    if missing:
        raise ValueError(f"candles must contain {sorted(missing)}")
    for column in ("close", "high", "low"):
        candles[column] = pd.to_numeric(candles[column], errors="raise")
    if candles.empty:
        raise ValueError("candles cannot be empty")
    if (candles[["close", "high", "low"]] <= 0).any().any():
        raise ValueError("candle prices must be positive")
    return candles.reset_index(drop=True)
