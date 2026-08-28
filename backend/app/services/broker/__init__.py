"""
Broker factory — returns the right broker based on config.
To add a new broker: add it here and create broker/yourbroker.py
"""
from app.config import settings
from app.services.broker.base import BrokerBase


def get_broker() -> BrokerBase:
    """
    Returns the configured broker instance.
    Controlled by ACTIVE_BROKER in .env
    """
    # Live execution requires both the broker selection and live mode.
    broker_name = settings.active_broker.lower()
    if settings.trading_mode.lower() != "live":
        broker_name = "paper"

    if broker_name == "angelone":
        from app.services.broker.angelone import AngelOneBroker
        return AngelOneBroker()

    elif broker_name == "zerodha":
        from app.services.broker.zerodha import ZerodhaBroker
        return ZerodhaBroker()

    else:  # Default: paper trading
        from app.services.broker.paper_trader import PaperBroker
        return PaperBroker()


# Singleton broker instance shared across the app
_broker_instance: BrokerBase | None = None


async def get_active_broker() -> BrokerBase:
    global _broker_instance
    if _broker_instance is None:
        _broker_instance = get_broker()
        await _broker_instance.connect()
    return _broker_instance
