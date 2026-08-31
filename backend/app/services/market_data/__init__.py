"""
Market data service factory.
Returns the configured market data provider (Angel One, Yahoo Finance, etc.)
"""
from datetime import datetime, timedelta, timezone

from app.config import settings
from app.services.market_data.base import MarketDataProvider, Quote
from loguru import logger


def quote_is_fresh(quote: Quote, max_age_seconds: int = 30) -> bool:
    """Reject stale quotes that are too old for a safe trade evaluation."""
    if quote is None or quote.timestamp is None:
        return False

    tz = quote.timestamp.tzinfo or timezone.utc
    age = (datetime.now(tz) - quote.timestamp).total_seconds()
    return age <= max_age_seconds


def get_market_data_provider() -> MarketDataProvider:
    """
    Returns configured market data provider.
    
    Priority:
    1. Angel One (if credentials available) - FREE, real NSE data
    2. Yahoo Finance (fallback) - FREE, but rate-limited
    """
    provider_name = getattr(settings, 'data_provider', 'yfinance').lower()
    has_angelone_credentials = all([
        settings.angel_api_key,
        settings.angel_client_id,
        settings.angel_password,
        settings.angel_totp_secret,
    ])

    if provider_name == "angelone" and has_angelone_credentials:
        try:
            from app.services.market_data.angelone import AngelOneMarketData
            logger.info("Using Angel One market data provider")
            return AngelOneMarketData()
        except ImportError:
            logger.warning("Angel One SDK not available, falling back to Yahoo Finance")
            return _get_yfinance_provider()

    logger.info("Using Yahoo Finance market data provider")
    return _get_yfinance_provider()


def _get_yfinance_provider() -> MarketDataProvider:
    """Create Yahoo Finance provider."""
    from app.services.market_data.yfinance_provider import YFinanceProvider
    logger.info("Using Yahoo Finance market data provider")
    return YFinanceProvider()


# Singleton market data instance shared across app
_market_data_instance: MarketDataProvider | None = None


async def get_active_market_data() -> MarketDataProvider:
    """
    Get or create the active market data provider.
    
    Handles singleton initialization and connection.
    """
    global _market_data_instance
    if _market_data_instance is None:
        _market_data_instance = get_market_data_provider()
        connected = await _market_data_instance.connect()
        if connected:
            logger.info("✓ Market data provider connected and ready")
        else:
            logger.warning("Market data provider connection failed, will attempt on first call")
    
    return _market_data_instance


def reset_market_data():
    """Reset market data provider (for testing)."""
    global _market_data_instance
    _market_data_instance = None
