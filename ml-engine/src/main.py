"""
ML Engine Main

Responsibilities:

  - Fetch market data
  - Generate AI signals
  - Apply risk management
  - Execute approved trades through backend
  - Publish signals to frontend
  - Retrain model daily
"""

import asyncio
import os
import schedule
import time

from datetime import (
    datetime,
    time as dtime,
)

from loguru import logger

from src.data.fetcher import fetch_multiple
from src.data.features import engineer_features
from src.models.xgboost_model import (
    XGBoostTradingModel,
)
from src.trading.signal_generator import (
    generate_signals,
    push_signals_to_backend,
)
from src.trading.risk_manager import (
    RiskManager,
)
from src.trading.executor import (
    execute_trade,
)


WATCHLIST = os.getenv(
    "WATCHLIST",
    (
        "RELIANCE,TCS,HDFCBANK,"
        "INFY,WIPRO"
    ),
).split(",")

WATCHLIST = [
    symbol.strip().upper()
    for symbol in WATCHLIST
    if symbol.strip()
]

CAPITAL = float(
    os.getenv(
        "TRADING_CAPITAL",
        "100000",
    )
)

PREDICTION_INTERVAL = int(
    os.getenv(
        "PREDICTION_INTERVAL",
        "60",
    )
)

TRADING_MODE = os.getenv(
    "TRADING_MODE",
    "paper",
)


risk_manager = RiskManager(
    capital=CAPITAL
)

model = XGBoostTradingModel()


def is_market_hours() -> bool:
    """
    NSE market hours in IST.

    09:15 - 15:25

    We stop new AI processing slightly before
    the official close.
    """

    from zoneinfo import ZoneInfo

    now = datetime.now(
        ZoneInfo("Asia/Kolkata")
    )

    if now.weekday() >= 5:
        return False

    return (
        dtime(9, 15)
        <= now.time()
        <= dtime(15, 25)
    )


def train_models():
    """
    Daily model retraining.

    Called at 08:00 before market opens.
    """

    logger.info(
        "Starting daily model retraining..."
    )

    try:

        datasets = fetch_multiple(
            WATCHLIST
        )

        combined_dfs = []

        for symbol, df in datasets.items():

            feat_df = engineer_features(
                df
            )

            if not feat_df.empty:
                combined_dfs.append(
                    feat_df
                )

        if not combined_dfs:

            logger.error(
                "No data available "
                "for retraining"
            )

            return

        import pandas as pd

        all_data = pd.concat(
            combined_dfs,
            ignore_index=True,
        )

        results = model.train(
            all_data,
            symbol="ALL",
        )

        logger.info(
            "Model retrained successfully. "
            f"Accuracy: "
            f"{results['accuracy']:.1%}"
        )

    except Exception as e:

        logger.error(
            f"Retraining failed: {e}"
        )


async def trading_loop():

    logger.info(
        "Trading loop started. "
        f"Mode: {TRADING_MODE} | "
        f"Symbols: {WATCHLIST}"
    )

    while True:

        try:

            if not is_market_hours():

                logger.debug(
                    "Market closed — waiting..."
                )

                await asyncio.sleep(
                    PREDICTION_INTERVAL
                )

                continue

            # -------------------------------------------------
            # Generate AI signals
            # -------------------------------------------------
            signals = await generate_signals(
                WATCHLIST
            )

            if not signals:

                logger.debug(
                    "No signals generated."
                )

                await asyncio.sleep(
                    PREDICTION_INTERVAL
                )

                continue

            # -------------------------------------------------
            # Apply risk management
            # -------------------------------------------------
            approved = []

            for sig in signals:

                decision = (
                    risk_manager.approve_trade(
                        symbol=sig["symbol"],
                        signal=sig["signal"],
                        confidence=sig[
                            "confidence"
                        ],
                        ltp=sig["ltp"],
                        min_confidence=float(
                            os.getenv(
                                "MIN_CONFIDENCE",
                                "65",
                            )
                        ),
                    )
                )

                if decision["approved"]:

                    sig.update(
                        decision
                    )

                    approved.append(
                        sig
                    )

                else:

                    # Keep rejection reason
                    # for frontend visibility.
                    sig.update(
                        decision
                    )

            # -------------------------------------------------
            # Push ALL signals to backend
            # -------------------------------------------------
            await push_signals_to_backend(
                signals
            )

            # -------------------------------------------------
            # Execute approved trades
            # -------------------------------------------------
            if not approved:

                logger.info(
                    "No trades approved "
                    "by risk manager."
                )

            else:

                logger.info(
                    f"{len(approved)} "
                    "trade(s) approved "
                    "for execution."
                )

                for sig in approved:

                    # Double-check market status
                    # immediately before execution.
                    if not is_market_hours():

                        logger.warning(
                            "Market closed "
                            "before execution. "
                            f"Skipping "
                            f"{sig['symbol']}"
                        )

                        continue

                    result = await execute_trade(
                        sig
                    )

                    if result:

                        execution_price = float(
                            result["price"]
                        )

                        execution_quantity = int(
                            result["quantity"]
                        )

                        risk_manager.record_trade(
                            symbol=sig["symbol"],
                            action=sig["signal"],
                            price=execution_price,
                            quantity=execution_quantity,
                        )

                    else:

                        logger.warning(
                            "Execution failed "
                            f"for {sig['symbol']}"
                        )

        except Exception as e:

            logger.exception(
                f"Trading loop error: {e}"
            )

        await asyncio.sleep(
            PREDICTION_INTERVAL
        )


def main():

    logger.info(
        "AI Z ML Engine starting..."
    )

    # ---------------------------------------------------------
    # Train model on first startup
    # ---------------------------------------------------------
    if not os.path.exists(
        "models/xgboost_model.pkl"
    ):

        logger.info(
            "No saved model found — "
            "training now..."
        )

        train_models()

    # ---------------------------------------------------------
    # Daily retraining
    # ---------------------------------------------------------
    schedule.every().day.at(
        "08:00"
    ).do(train_models)

    # ---------------------------------------------------------
    # Run schedule in background thread
    # ---------------------------------------------------------
    import threading

    def run_schedule():

        while True:

            schedule.run_pending()

            time.sleep(30)

    thread = threading.Thread(
        target=run_schedule,
        daemon=True,
    )

    thread.start()

    # ---------------------------------------------------------
    # Start async trading loop
    # ---------------------------------------------------------
    asyncio.run(
        trading_loop()
    )


if __name__ == "__main__":
    main()
