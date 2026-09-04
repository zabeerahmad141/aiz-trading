"""
Trade Executor

The ML engine does NOT communicate directly with a broker.

Flow:

ML Engine
    ↓
Risk Manager
    ↓
Executor
    ↓
Backend API
    ↓
Broker
"""

import os

import httpx
from loguru import logger


BACKEND_URL = os.getenv(
    "BACKEND_URL",
    "http://backend:8000",
)

INTERNAL_API_KEY = os.getenv(
    "INTERNAL_API_KEY",
    "",
)


async def execute_trade(
    signal: dict,
) -> dict | None:
    """
    Execute one risk-approved trade
    through the backend API.
    """

    if not signal.get("approved"):
        logger.warning(
            "Executor received "
            "unapproved signal: "
            f"{signal.get('symbol')}"
        )
        return None

    required_fields = [
        "symbol",
        "signal",
        "quantity",
    ]

    for field in required_fields:
        if field not in signal:
            logger.error(
                f"Missing execution field: {field}"
            )
            return None

    if not INTERNAL_API_KEY:
        logger.error(
            "INTERNAL_API_KEY is not configured. "
            "Trade execution blocked."
        )
        return None

    payload = {
        "execution_id": signal.get("execution_id"),
        "symbol": signal["symbol"],
        "action": signal["signal"].lower(),
        "quantity": int(
            signal["quantity"]
        ),
        "stop_loss": signal.get(
            "stop_loss"
        ),
        "target_price": signal.get(
            "target"
        ),
        "ai_signal": signal.get(
            "signal"
        ),
        "ai_confidence": signal.get(
            "confidence"
        ),
        "ai_reason": signal.get(
            "reason"
        ),
        "ltp": signal.get(
            "ltp"
        ),
    }

    try:

        async with httpx.AsyncClient() as client:

            response = await client.post(
                (
                    f"{BACKEND_URL}"
                    "/api/trading/ai-order"
                ),
                json=payload,
                headers={
                    "X-Internal-Key":
                        INTERNAL_API_KEY,
                },
                timeout=15,
            )

            response.raise_for_status()

            result = response.json()

            logger.info(
                f"TRADE EXECUTED | "
                f"{signal['signal']} "
                f"{signal['quantity']}x "
                f"{signal['symbol']} | "
                f"Order: "
                f"{result.get('order_id')}"
            )

            return result

    except httpx.HTTPStatusError as e:

        logger.error(
            f"Backend rejected trade "
            f"{signal.get('symbol')}: "
            f"HTTP {e.response.status_code} | "
            f"{e.response.text}"
        )

    except Exception as e:

        logger.error(
            f"Trade execution failed for "
            f"{signal.get('symbol')}: {e}"
        )

    return None
