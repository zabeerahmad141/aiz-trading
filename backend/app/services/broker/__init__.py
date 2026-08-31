"""
Broker factory — returns the right broker based on config.
To add a new broker: add it here and create broker/yourbroker.py
"""
from app.config import get_settings
from app.services.broker.base import BrokerBase


def get_broker() -> BrokerBase:
    """
    Returns the configured broker instance.
    Live execution is blocked unless the configuration explicitly opts in.
    """
    settings = get_settings()

    if not settings.is_live_trading_allowed:
        from app.services.broker.paper_trader import PaperBroker
        return PaperBroker()

    broker_name = settings.active_broker.lower()

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
