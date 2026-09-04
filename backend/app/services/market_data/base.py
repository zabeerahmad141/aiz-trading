"""
Abstract market data provider interface.
Implementations: Angel One (live), Yahoo Finance (fallback)
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Quote:
    """Real-time quote data."""
    symbol: str
    ltp: float  # Last Traded Price
    open: float
    high: float
    low: float
    close: float
    volume: int
    change_pct: float
    timestamp: datetime
    source: str = "unknown"


@dataclass
class OHLCV:
    """Historical OHLCV candle data."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


class MarketDataProvider(ABC):
    """Abstract base for all market data providers."""

    @abstractmethod
    async def connect(self) -> bool:
        """Authenticate and establish connection."""

    @abstractmethod
    async def get_quote(self, symbol: str) -> Quote:
        """
        Get live quote for a symbol.
        
        Args:
            symbol: Stock symbol (e.g., "HDFCBANK", "TCS")
            
        Returns:
            Quote with real-time data
            
        Raises:
            ConnectionError: If market data service unavailable
            ValueError: If symbol not found
        """

    @abstractmethod
    async def get_ohlcv(
        self,
        symbol: str,
        period: str = "1d",
        interval: str = "5m",
    ) -> list[OHLCV]:
        """
        Get historical OHLCV candles for charting and analysis.
        
        Args:
            symbol: Stock symbol (e.g., "HDFCBANK")
            period: Time period ("1d", "5d", "1mo", "3mo", "1y")
            interval: Candle interval ("1m", "5m", "15m", "1h", "1d")
            
        Returns:
            List of OHLCV candles, most recent last
        """

    @abstractmethod
    async def is_market_open(self) -> bool:
        """Check if NSE market is currently open."""
