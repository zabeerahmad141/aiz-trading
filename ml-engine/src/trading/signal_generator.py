"""
Trading Signal Generator — orchestrates ML model predictions
into actionable BUY/SELL/HOLD signals with risk parameters.
"""
import os
import uuid
import httpx
from loguru import logger
from src.data.fetcher import fetch_intraday
from src.data.features import engineer_features, FEATURE_COLUMNS
from src.models.xgboost_model import XGBoostTradingModel

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")
MIN_CONFIDENCE = float(os.getenv("MIN_CONFIDENCE", "65"))
CONFIRMATION_CANDLES = int(os.getenv("CONFIRMATION_CANDLES", "10"))
MIN_CONFIRMATIONS = int(os.getenv("MIN_CONFIRMATIONS", "6"))

model = XGBoostTradingModel()


async def generate_signals(
    symbols: list[str],
    model_instance: XGBoostTradingModel | None = None,
) -> list[dict]:
    """
    Generates trading signals for all symbols in watchlist.
    Called every PREDICTION_INTERVAL seconds during market hours.
    """
    signals = []
    active_model = model_instance or model

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

            # Validate the latest model direction against recent candles.
            # The newest row is used for the trade price; older rows confirm persistence.
            confirmation_window = df_feat.tail(CONFIRMATION_CANDLES)
            latest = confirmation_window.tail(1)

            # Run ML prediction
            pred = active_model.predict(latest)
            candle_predictions = [
                active_model.predict(confirmation_window.iloc[[index]])["signal"]
                for index in range(len(confirmation_window))
            ]
            confirmed_count = candle_predictions.count(pred["signal"])
            atr_values = confirmation_window["atr"].astype(float)
            atr_valid = bool((atr_values > 0).all())
            confirmation_passed = (
                pred["signal"] == "HOLD"
                or (confirmed_count >= MIN_CONFIRMATIONS and atr_valid)
            )
            final_signal = pred["signal"] if confirmation_passed else "HOLD"
            validation_reason = (
                "Confirmed across recent candles"
                if confirmation_passed
                else f"Rejected: {confirmed_count}/{len(confirmation_window)} candle confirmation; ATR valid={atr_valid}"
            )

            signal_data = {
                "execution_id": str(uuid.uuid4()),
                "symbol": symbol,
                "signal": final_signal,
                "raw_signal": pred["signal"],
                "confidence": pred["confidence"],
                "proba": pred["proba"],
                "ltp": float(df['close'].iloc[-1]),
                "confirmation_candles": len(confirmation_window),
                "confirmation_count": confirmed_count,
                "confirmation_required": MIN_CONFIRMATIONS,
                "atr_valid": atr_valid,
                "validation_reason": validation_reason,
                "indicators": {
                    "rsi": round(float(latest["rsi"].iloc[0]), 2),
                    "macd": round(float(latest["macd"].iloc[0]), 4),
                    "ema_cross": int(latest["ema_cross"].iloc[0]),
                    "bb_pct": round(float(latest["bb_pct"].iloc[0]), 4),
                    "atr": round(float(latest["atr"].iloc[0]), 4),
                },
                "atr": round(float(latest["atr"].iloc[0]), 4),
            }

            signals.append(signal_data)
            logger.info(
                f"{symbol}: {final_signal} | Raw: {pred['signal']} | "
                f"Confidence: {pred['confidence']}% | "
                f"Confirmation: {confirmed_count}/{len(confirmation_window)} | "
                f"LTP: ₹{signal_data['ltp']:.2f}"
            )

        except Exception as e:
            logger.error(f"Signal generation failed for {symbol}: {e}")

    return signals


async def push_signals_to_backend(signals: list[dict]):
    """Push generated signals to backend via internal API."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BACKEND_URL}/api/trading/ai-signals",
                json={"signals": signals},
                headers={"X-Internal-Key": os.getenv("INTERNAL_API_KEY", "")},
                timeout=10,
            )
            response.raise_for_status()
    except Exception as e:
        logger.warning(f"Could not push signals to backend: {e}")
