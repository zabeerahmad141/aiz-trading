"""
Trading Signal Generator — orchestrates ML model predictions
into actionable BUY/SELL/HOLD signals with risk parameters.
"""
import os
import httpx
from loguru import logger
from src.data.fetcher import fetch_intraday
from src.data.features import engineer_features, FEATURE_COLUMNS
from src.models.xgboost_model import XGBoostTradingModel

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")
MIN_CONFIDENCE = float(os.getenv("MIN_CONFIDENCE", "65"))

model = XGBoostTradingModel()


async def generate_signals(symbols: list[str]) -> list[dict]:
    """
    Generates trading signals for all symbols in watchlist.
    Called every PREDICTION_INTERVAL seconds during market hours.
    """
    signals = []

    for symbol in symbols:
        try:
            # Fetch recent intraday data
            df = fetch_intraday(symbol, interval="5m")
            if len(df) < 30:
                logger.warning(f"{symbol}: Not enough data ({len(df)} bars)")
                continue

            # Engineer features
            df_feat = engineer_features(df)
            if df_feat.empty:
                continue

            # Get latest feature row (most recent bar)
            latest = df_feat.tail(1)

            # Run ML prediction
            pred = model.predict(latest)

            signal_data = {
                "symbol": symbol,
                "signal": pred["signal"],
                "confidence": pred["confidence"],
                "proba": pred["proba"],
                "ltp": float(df['close'].iloc[-1]),
                "indicators": {
                    "rsi": round(float(latest["rsi"].iloc[0]), 2),
                    "macd": round(float(latest["macd"].iloc[0]), 4),
                    "ema_cross": int(latest["ema_cross"].iloc[0]),
                    "bb_pct": round(float(latest["bb_pct"].iloc[0]), 4),
                },
            }

            signals.append(signal_data)
            logger.info(
                f"{symbol}: {pred['signal']} | Confidence: {pred['confidence']}% | LTP: ₹{signal_data['ltp']:.2f}"
            )

        except Exception as e:
            logger.error(f"Signal generation failed for {symbol}: {e}")

    return signals


async def push_signals_to_backend(signals: list[dict]):
    """Push generated signals to backend via internal API."""
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{BACKEND_URL}/api/trading/ai-signals",
                json={"signals": signals},
                headers={"X-Internal-Key": os.getenv("INTERNAL_API_KEY", "")},
                timeout=10,
            )
    except Exception as e:
        logger.warning(f"Could not push signals to backend: {e}")
