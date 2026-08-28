"""
Yahoo Finance market data provider (fallback).
Used when Angel One unavailable.
"""
import asyncio
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from loguru import logger

from app.services.market_data.base import MarketDataProvider, Quote, OHLCV


class YFinanceProvider(MarketDataProvider):
    """
    Yahoo Finance market data provider.
    
    Fallback option when Angel One unavailable.
    Note: Yahoo Finance is rate-limited, best used with Redis caching.
    """

    quote_cache: dict[str, tuple[float, Quote]] = {}
    quote_cache_ttl = 15.0

    async def connect(self) -> bool:
        """Verify yfinance is available."""
        try:
            import yfinance as yf
            logger.info("✓ Yahoo Finance available (rate-limited, caching recommended)")
            return True
        except ImportError:
            logger.error("yfinance not installed. Install: pip install yfinance")
            return False

    async def get_quote(self, symbol: str) -> Quote:
        """Fetch quote from Yahoo Finance."""
        cached = self.quote_cache.get(symbol)
        if cached and time.monotonic() - cached[0] < self.quote_cache_ttl:
            return cached[1]

        quote = await asyncio.to_thread(self._fetch_quote, symbol)
        if quote.ltp > 0:
            self.quote_cache[symbol] = (time.monotonic(), quote)
        return quote

    @staticmethod
    def _fetch_quote(symbol: str) -> Quote:
        try:
            import yfinance as yf

            ticker = yf.Ticker(f"{symbol}.NS")
            hist = ticker.history(period="5d", interval="1m", auto_adjust=False)
            if hist.empty:
                hist = ticker.history(period="1d", interval="5m", auto_adjust=False)
            if hist.empty:
                raise ValueError(f"No price data found for {symbol}")

            close_series = hist["Close"].dropna()
            open_series = hist["Open"].dropna()
            high_series = hist["High"].dropna()
            low_series = hist["Low"].dropna()
            volume_series = hist["Volume"].dropna()

            if close_series.empty:
                raise ValueError(f"No close data found for {symbol}")

            latest = close_series.iloc[-1]
            prev_close = close_series.iloc[-2] if len(close_series) > 1 else latest
            ltp = float(latest)
            open_p = float(open_series.iloc[0]) if not open_series.empty else ltp
            high = float(high_series.max()) if not high_series.empty else ltp
            low = float(low_series.min()) if not low_series.empty else ltp
            close = float(close_series.iloc[-1]) if not close_series.empty else ltp
            volume = int(volume_series.sum()) if not volume_series.empty else 0
            change_pct = ((ltp - prev_close) / prev_close * 100) if prev_close else 0.0

            return Quote(
                symbol=symbol,
                ltp=round(ltp, 2),
                open=round(open_p, 2),
                high=round(high, 2),
                low=round(low, 2),
                close=round(close, 2),
                volume=volume,
                change_pct=round(change_pct, 2),
                timestamp=datetime.now(ZoneInfo("Asia/Kolkata")),
            )
        except Exception as e:
            logger.warning(f"Yahoo Finance quote fallback failed for {symbol}: {e}. "
                           "The backend will return a safe zero-value quote instead of crashing.")
            return Quote(
                symbol=symbol,
                ltp=0.0,
                open=0.0,
                high=0.0,
                low=0.0,
                close=0.0,
                volume=0,
                change_pct=0.0,
                timestamp=datetime.now(ZoneInfo("Asia/Kolkata")),
            )

    async def get_ohlcv(
        self,
        symbol: str,
        period: str = "1d",
        interval: str = "5m",
    ) -> list[OHLCV]:
        """Fetch OHLCV data from Yahoo Finance."""
        return await asyncio.to_thread(self._fetch_ohlcv, symbol, period, interval)

    @staticmethod
    def _fetch_ohlcv(
        symbol: str,
        period: str,
        interval: str,
    ) -> list[OHLCV]:
        try:
            import yfinance as yf

            ticker = yf.Ticker(f"{symbol}.NS")
            hist = ticker.history(period=period, interval=interval)

            candles = []
            for ts, row in hist.iterrows():
                ohlcv = OHLCV(
                    timestamp=ts.to_pydatetime().replace(tzinfo=ZoneInfo("Asia/Kolkata")),
                    open=float(row["Open"]),
                    high=float(row["High"]),
                    low=float(row["Low"]),
                    close=float(row["Close"]),
                    volume=int(row["Volume"]),
                )
                candles.append(ohlcv)

            return candles
        except Exception as e:
            logger.error(f"Yahoo Finance OHLCV error for {symbol}: {e}")
            return []

    async def is_market_open(self) -> bool:
        """Check if NSE market is currently open."""
        from datetime import time as dtime
        
        now = datetime.now(ZoneInfo("Asia/Kolkata"))
        
        # Check if weekend
        if now.weekday() >= 5:
            return False
        
        # Check if within market hours
        open_time = dtime(9, 15)
        close_time = dtime(15, 30)
        
        return open_time <= now.time() <= close_time
