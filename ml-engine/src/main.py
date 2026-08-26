"""
ML Engine Main — runs the trading bot loop.
  - Fetches data every PREDICTION_INTERVAL seconds
  - Generates AI signals
  - Applies risk management
  - Executes trades via backend API
  - Retrains model daily at 8 AM
"""
import asyncio
import os
import schedule
import time
from datetime import datetime, time as dtime
from loguru import logger

from src.data.fetcher import fetch_multiple
from src.data.features import engineer_features
from src.models.xgboost_model import XGBoostTradingModel
from src.trading.signal_generator import generate_signals, push_signals_to_backend
from src.trading.risk_manager import RiskManager

WATCHLIST = os.getenv("WATCHLIST", "RELIANCE,TCS,HDFCBANK,INFY,WIPRO").split(",")
CAPITAL = float(os.getenv("TRADING_CAPITAL", "100000"))
PREDICTION_INTERVAL = int(os.getenv("PREDICTION_INTERVAL", "60"))
TRADING_MODE = os.getenv("TRADING_MODE", "paper")

risk_manager = RiskManager(capital=CAPITAL)
model = XGBoostTradingModel()


def is_market_hours() -> bool:
    now = datetime.now()
    if now.weekday() >= 5:
        return False
    return dtime(9, 15) <= now.time() <= dtime(15, 25)


def train_models():
    """Daily model retraining — called at 8 AM IST before market opens."""
    logger.info("Starting daily model retraining...")
    try:
        datasets = fetch_multiple(WATCHLIST)
        combined_dfs = []
        for symbol, df in datasets.items():
            feat_df = engineer_features(df)
            combined_dfs.append(feat_df)

        if not combined_dfs:
            logger.error("No data for retraining")
            return

        import pandas as pd
        all_data = pd.concat(combined_dfs, ignore_index=True)
        results = model.train(all_data, symbol="ALL")
        logger.info(f"Model retrained successfully. Accuracy: {results['accuracy']:.1%}")
    except Exception as e:
        logger.error(f"Retraining failed: {e}")


async def trading_loop():
    logger.info(f"Trading loop started. Mode: {TRADING_MODE} | Symbols: {WATCHLIST}")

    while True:
        try:
            if is_market_hours():
                signals = await generate_signals(WATCHLIST)
                if signals:
                    # Apply risk management
                    approved = []
                    for sig in signals:
                        decision = risk_manager.approve_trade(
                            symbol=sig["symbol"],
                            signal=sig["signal"],
                            confidence=sig["confidence"],
                            ltp=sig["ltp"],
                        )
                        if decision["approved"]:
                            sig.update(decision)
                            approved.append(sig)

                    # Push all signals (including rejected ones) to backend for display
                    await push_signals_to_backend(signals)

                    if approved:
                        logger.info(f"{len(approved)} trades approved for execution")
            else:
                logger.debug("Market closed — waiting...")

        except Exception as e:
            logger.error(f"Trading loop error: {e}")

        await asyncio.sleep(PREDICTION_INTERVAL)


def main():
    logger.info("AI Z ML Engine starting...")

    # Train model on startup if no saved model
    if not os.path.exists("models/xgboost_model.pkl"):
        logger.info("No saved model found — training now...")
        train_models()

    # Schedule daily retraining at 8:00 AM
    schedule.every().day.at("08:00").do(train_models)

    # Run schedule in a thread + trading loop async
    import threading
    def run_schedule():
        while True:
            schedule.run_pending()
            time.sleep(30)

    t = threading.Thread(target=run_schedule, daemon=True)
    t.start()

    asyncio.run(trading_loop())


if __name__ == "__main__":
    main()
