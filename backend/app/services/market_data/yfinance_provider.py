"""
Yahoo Finance market data provider (fallback).
Used when Angel One unavailable.
"""
import asyncio
import math
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from loguru import logger

from app.services.market_data.base import MarketDataProvider, Quote, OHLCV


_DEMO_BASE_PRICES = {
    "RELIANCE": 2915.0,
    "TCS": 4150.0,
    "HDFCBANK": 1745.0,
    "INFY": 1565.0,
    "WIPRO": 471.0,
    "ICICIBANK": 1250.0,
    "BAJFINANCE": 7035.0,
    "SBIN": 875.0,
    "ITC": 455.0,
    "KOTAKBANK": 1770.0,
    "LT": 3350.0,
    "AXISBANK": 1185.0,
    "BHARTIARTL": 1650.0,
    "HINDUNILVR": 2460.0,
    "MARUTI": 12300.0,
    "SUNPHARMA": 1495.0,
    "TITAN": 3550.0,
    "ULTRACEMCO": 11200.0,
    "ASIANPAINT": 2500.0,
    "HCLTECH": 1600.0,
    "ADANIENT": 3270.0,
    "NTPC": 361.0,
    "POWERGRID": 285.0,
    "M&M": 2900.0,
    "TATASTEEL": 170.0,
    "JSWSTEEL": 955.0,
    "ONGC": 297.0,
    "COALINDIA": 520.0,
    "TECHM": 1585.0,
    "TATAMOTORS": 1040.0,
    "NESTLEIND": 2385.0,
    "DRREDDY": 6320.0,
    "CIPLA": 1460.0,
    "GRASIM": 2360.0,
    "EICHERMOT": 4950.0,
    "HEROMOTOCO": 4650.0,
    "APOLLOHOSP": 6920.0,
    "DIVISLAB": 4080.0,
    "BRITANNIA": 5360.0,
}


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
    def _demo_quote(symbol: str) -> Quote:
        base = _DEMO_BASE_PRICES.get(symbol.upper(), 1000.0)
        drift = (abs(hash(symbol.upper())) % 1000) / 100.0 - 5.0
        ltp = round(base + drift, 2)
        open_p = round(ltp * 0.995, 2)
        high = round(max(ltp, open_p) * 1.01, 2)
        low = round(min(ltp, open_p) * 0.99, 2)
        close = round(ltp, 2)
        volume = 250000 + (abs(hash(symbol.upper())) % 300000)
        change_pct = round(((ltp - open_p) / open_p) * 100, 2) if open_p else 0.0
        return Quote(
            symbol=symbol.upper(),
            ltp=ltp,
            open=open_p,
            high=high,
            low=low,
            close=close,
            volume=volume,
            change_pct=change_pct,
            timestamp=datetime.now(ZoneInfo("Asia/Kolkata")),
            source="demo",
        )

    @staticmethod
    def _fetch_quote(symbol: str) -> Quote:
        try:
            import yfinance as yf

            ticker = yf.Ticker(f"{symbol}.NS")
            hist = ticker.history(period="5d", interval="1m", auto_adjust=False)
            if hist.empty:
                hist = ticker.history(period="1d", interval="5m", auto_adjust=False)
            if hist.empty:
                logger.warning(f"Yahoo Finance returned no price history for {symbol}; using demo fallback values.")
                return YFinanceProvider._demo_quote(symbol)

            close_series = hist["Close"].dropna()
            open_series = hist["Open"].dropna()
            high_series = hist["High"].dropna()
            low_series = hist["Low"].dropna()
            volume_series = hist["Volume"].dropna()

            if close_series.empty:
                logger.warning(f"Yahoo Finance close data missing for {symbol}; using demo fallback values.")
                return YFinanceProvider._demo_quote(symbol)

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
                source="yfinance",
            )
        except Exception as e:
            logger.warning(f"Yahoo Finance quote fallback failed for {symbol}: {e}. Using demo market fallback values.")
            return YFinanceProvider._demo_quote(symbol)

    @staticmethod
    def _demo_ohlcv(symbol: str, interval: str) -> list[OHLCV]:
        """Generate clearly synthetic candles for paper-mode UI observation."""
        interval_minutes = {
            "1m": 1,
            "5m": 5,
            "15m": 15,
            "1h": 60,
            "1d": 1440,
        }.get(interval, 5)
        quote = YFinanceProvider._demo_quote(symbol)
        step = timedelta(minutes=interval_minutes)
        now = datetime.now(ZoneInfo("Asia/Kolkata")).replace(second=0, microsecond=0)
        candles: list[OHLCV] = []
        phase = (abs(hash(symbol.upper())) % 360) * math.pi / 180
        previous_close = quote.ltp * (1 - 0.002)
        for index in range(60):
            wave = math.sin(index * 0.42 + phase) * 0.004
            pullback = math.sin(index * 0.13 + phase * 0.5) * 0.002
            drift = ((index / 59) - 0.5) * 0.002
            close = round(quote.ltp * (1 + wave + pullback + drift), 2)
            open_price = round(previous_close, 2)
            candles.append(OHLCV(
                timestamp=now - step * (59 - index),
                open=open_price,
                high=round(max(open_price, close) * 1.002, 2),
                low=round(min(open_price, close) * 0.998, 2),
                close=close,
                volume=max(1, int((quote.volume // 60) * (1 + abs(wave) * 40))),
            ))
            previous_close = close
        return candles

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

            if hist.empty:
                logger.warning(f"Yahoo Finance returned no OHLCV history for {symbol}; using demo fallback candles.")
                return YFinanceProvider._demo_ohlcv(symbol, interval)

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
            logger.warning(f"Yahoo Finance OHLCV error for {symbol}: {e}; using demo fallback candles.")
            return YFinanceProvider._demo_ohlcv(symbol, interval)

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
