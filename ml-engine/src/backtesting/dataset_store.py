"""Local historical dataset storage for offline backtesting."""

from __future__ import annotations

import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from src.backtesting.loader import load_candles


DATASET_COLUMNS = {"timestamp", "open", "high", "low", "close", "volume", "signal"}


def save_dataset(candles: pd.DataFrame, path: str | Path, *, symbol: str, source: str) -> Path:
    """Validate and save a reusable CSV dataset plus a JSON manifest."""
    missing = DATASET_COLUMNS.difference(candles.columns)
    if missing:
        raise ValueError(f"dataset must contain {sorted(missing)}")
    validated = candles.copy()
    validated["timestamp"] = pd.to_datetime(validated["timestamp"], utc=True)
    for column in ("open", "high", "low", "close", "volume"):
        validated[column] = pd.to_numeric(validated[column], errors="raise")
    if validated.empty or (validated[["open", "high", "low", "close"]] <= 0).any().any():
        raise ValueError("dataset must contain positive OHLC prices")
    if (validated["high"] < validated[["open", "close"]].max(axis=1)).any():
        raise ValueError("high must be at least open and close")
    if (validated["low"] > validated[["open", "close"]].min(axis=1)).any():
        raise ValueError("low must be at most open and close")
    if (validated["volume"] < 0).any():
        raise ValueError("volume cannot be negative")

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    validated.to_csv(target, index=False)
    manifest = {
        "symbol": symbol.upper(),
        "source": source,
        "rows": len(validated),
        "start": validated["timestamp"].min().isoformat(),
        "end": validated["timestamp"].max().isoformat(),
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }
    target.with_suffix(".json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return target


def load_dataset(path: str | Path) -> tuple[pd.DataFrame, dict]:
    """Load a validated local dataset and its manifest."""
    target = Path(path)
    candles = pd.read_csv(target)
    missing = DATASET_COLUMNS.difference(candles.columns)
    if missing:
        raise ValueError(f"dataset must contain {sorted(missing)}")
    candles["timestamp"] = pd.to_datetime(candles["timestamp"], utc=True)
    load_candles(candles)
    manifest_path = target.with_suffix(".json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    return candles, manifest


def generate_demo_dataset(rows: int = 500, *, symbol: str = "RELIANCE") -> pd.DataFrame:
    """Create clearly labelled deterministic data for offline engineering tests."""
    if rows < 30:
        raise ValueError("rows must be at least 30")
    start = datetime(2024, 1, 2, 9, 15, tzinfo=timezone.utc)
    previous = 2500.0
    records = []
    for index in range(rows):
        movement = math.sin(index * 0.17) * 0.004 + math.sin(index * 0.037) * 0.002
        open_price = previous
        close = round(open_price * (1 + movement), 2)
        high = round(max(open_price, close) * 1.002, 2)
        low = round(min(open_price, close) * 0.998, 2)
        records.append({
            "timestamp": start + timedelta(minutes=5 * index),
            "symbol": symbol.upper(),
            "open": round(open_price, 2),
            "high": high,
            "low": low,
            "close": close,
            "volume": 100000 + (index % 11) * 12500,
            "signal": "BUY" if index % 37 == 5 else "SELL" if index % 37 == 24 else "HOLD",
        })
        previous = close
    return pd.DataFrame(records)