"""
Angel One SmartAPI market data provider.
Free NSE market data via Angel One broker.
"""
import asyncio
from datetime import datetime, time as dtime
from typing import Optional
from zoneinfo import ZoneInfo

from loguru import logger

from app.services.market_data.base import MarketDataProvider, Quote, OHLCV
from app.config import settings


class AngelOneMarketData(MarketDataProvider):
    """
    Angel One SmartAPI integration for live market data.
    
    Provides:
    - Real-time quotes (LTP, OHLC, volume)
    - Historical OHLCV data for charting
    - Market status (open/close)
    
    Note: Requires valid Angel One credentials in .env
    (ANGEL_API_KEY, ANGEL_CLIENT_ID, ANGEL_PASSWORD, ANGEL_TOTP_SECRET)
    """

    def __init__(self):
        self.connected = False
        self.smartapi = None
        self.jwt_token = None
        self.instrument_tokens: dict[str, str] = {}  # symbol -> token cache

    async def connect(self) -> bool:
        """Authenticate with Angel One SmartAPI."""
        try:
            # Import here to avoid import error if package not installed
            from SmartApi import SmartConnect
            import pyotp

            if not all([
                settings.angel_api_key,
                settings.angel_client_id,
                settings.angel_password,
                settings.angel_totp_secret,
            ]):
                logger.error("Angel One credentials incomplete in .env")
                return False

            # Initialize connection
            self.smartapi = SmartConnect(api_key=settings.angel_api_key)

            # Generate TOTP for 2FA
            totp = pyotp.TOTP(settings.angel_totp_secret)
            totp_value = totp.now()

            # Login
            login_response = self.smartapi.generateSession(
                settings.angel_client_id,
                settings.angel_password,
                totp_value,
            )

            if login_response.get("status"):
                self.jwt_token = login_response.get("data", {}).get("jwtToken")
                self.connected = True
                logger.info(f"✓ Angel One connected | Client: {settings.angel_client_id}")
                return True
            else:
                logger.error(f"Angel One login failed: {login_response}")
                return False

        except ImportError:
            logger.error("SmartAPI SDK not installed. Install: pip install smartapi-python")
            return False
        except Exception as e:
            logger.error(f"Angel One connection error: {e}")
            return False

    async def get_quote(self, symbol: str) -> Quote:
        """
        Fetch live quote from Angel One.
        
        Falls back to Yahoo Finance if Angel One unavailable.
        """
        if not self.connected:
            logger.warning("Angel One not connected, falling back to Yahoo Finance")
            return await self._get_quote_yfinance(symbol)

        try:
            # Get instrument token for symbol
            token = await self._get_instrument_token(symbol)
            if not token:
                logger.warning(f"Symbol {symbol} not found in Angel One")
                return await self._get_quote_yfinance(symbol)

            # Fetch LTP
            ltp_data = self.smartapi.ltpData(mode="LTP", exchangeTokens={"NSE": [token]})
            
            if not ltp_data or not ltp_data.get("data"):
                logger.warning(f"No quote data for {symbol}, falling back to Yahoo Finance")
                return await self._get_quote_yfinance(symbol)

            ltp_info = ltp_data["data"]["fetched"][0]
            ltp = float(ltp_info.get("ltp", 0))

            # Get historical data for OHLC (use previous day + today)
            ohlcv_list = await self.get_ohlcv(symbol, period="5d", interval="1d")
            
            if ohlcv_list:
                today_candle = ohlcv_list[-1]
                prev_candle = ohlcv_list[-2] if len(ohlcv_list) > 1 else today_candle
                
                change = ltp - prev_candle.close
                change_pct = (change / prev_candle.close * 100) if prev_candle.close else 0
            else:
                change_pct = 0
                today_candle = OHLCV(
                    timestamp=datetime.now(ZoneInfo("Asia/Kolkata")),
                    open=ltp,
                    high=ltp,
                    low=ltp,
                    close=ltp,
                    volume=0,
                )

            return Quote(
                symbol=symbol,
                ltp=round(ltp, 2),
                open=round(today_candle.open, 2),
                high=round(today_candle.high, 2),
                low=round(today_candle.low, 2),
                close=round(today_candle.close, 2),
                volume=int(today_candle.volume),
                change_pct=round(change_pct, 2),
                timestamp=datetime.now(ZoneInfo("Asia/Kolkata")),
            )

        except Exception as e:
            logger.error(f"Angel One quote error for {symbol}: {e}")
            return await self._get_quote_yfinance(symbol)

    async def get_ohlcv(
        self,
        symbol: str,
        period: str = "1d",
        interval: str = "5m",
    ) -> list[OHLCV]:
        """
        Get historical OHLCV data from Angel One.
        Falls back to Yahoo Finance if unavailable.
        """
        if not self.connected:
            return await self._get_ohlcv_yfinance(symbol, period, interval)

        try:
            token = await self._get_instrument_token(symbol)
            if not token:
                return await self._get_ohlcv_yfinance(symbol, period, interval)

            # Map period/interval to Angel One parameters
            from_date = self._calculate_from_date(period)
            
            # Request candlestick data
            candle_data = self.smartapi.getCandleData(
                "NSE",
                token,
                interval,
                from_date,
                datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%d-%m-%Y"),
            )

            if not candle_data or not candle_data.get("data"):
                logger.warning(f"No OHLCV data for {symbol}, falling back")
                return await self._get_ohlcv_yfinance(symbol, period, interval)

            candles = []
            for candle in candle_data["data"]:
                try:
                    ohlcv = OHLCV(
                        timestamp=datetime.fromisoformat(candle[0]),
                        open=float(candle[1]),
                        high=float(candle[2]),
                        low=float(candle[3]),
                        close=float(candle[4]),
                        volume=int(candle[5]),
                    )
                    candles.append(ohlcv)
                except (ValueError, IndexError) as e:
                    logger.debug(f"Skipping invalid candle: {e}")
                    continue

            return candles

        except Exception as e:
            logger.error(f"Angel One OHLCV error for {symbol}: {e}")
            return await self._get_ohlcv_yfinance(symbol, period, interval)

    async def is_market_open(self) -> bool:
        """Check if NSE market is currently open."""
        now = datetime.now(ZoneInfo("Asia/Kolkata"))
        
        # Check if weekend
        if now.weekday() >= 5:
            return False
        
        # Check if within market hours
        open_time = dtime(9, 15)
        close_time = dtime(15, 30)
        
        return open_time <= now.time() <= close_time

    # =========================================================
    # Private methods
    # =========================================================

    async def _get_instrument_token(self, symbol: str) -> Optional[str]:
        """
        Get Angel One instrument token for a symbol.
        Tokens are cached to reduce API calls.
        """
        if symbol in self.instrument_tokens:
            return self.instrument_tokens[symbol]

        try:
            # Request instrument master list (cached by Angel One)
            instruments = self.smartapi.getInstrumentList()
            
            if not instruments:
                logger.warning("Could not fetch instrument list from Angel One")
                return None

            # Find matching symbol (NSE equity only)
            for instrument in instruments:
                if (instrument.get("symbol") == symbol and 
                    instrument.get("exchange_type") == "NSE"):
                    token = instrument.get("exchange_token")
                    self.instrument_tokens[symbol] = token
                    return token

            logger.warning(f"Symbol {symbol} not found in Angel One instrument list")
            return None

        except Exception as e:
            logger.error(f"Instrument token lookup error: {e}")
            return None

    @staticmethod
    def _calculate_from_date(period: str) -> str:
        """Convert period string to from_date for Angel One API."""
        from datetime import timedelta
        
        now = datetime.now(ZoneInfo("Asia/Kolkata"))
        
        period_map = {
            "1d": now - timedelta(days=1),
            "5d": now - timedelta(days=5),
            "1mo": now - timedelta(days=30),
            "3mo": now - timedelta(days=90),
            "1y": now - timedelta(days=365),
        }
        
        from_date = period_map.get(period, now - timedelta(days=30))
        return from_date.strftime("%d-%m-%Y")

    # =========================================================
    # Fallback: Yahoo Finance
    # =========================================================

    async def _get_quote_yfinance(self, symbol: str) -> Quote:
        """Fallback to Yahoo Finance when Angel One unavailable."""
        try:
            import yfinance as yf
            
            ticker = yf.Ticker(f"{symbol}.NS")
            info = ticker.fast_info
            hist = ticker.history(period="1d", interval="1m")

            ltp = float(info.last_price) if hasattr(info, 'last_price') else 0.0
            open_p = float(hist['Open'].iloc[0]) if not hist.empty else ltp
            high = float(hist['High'].max()) if not hist.empty else ltp
            low = float(hist['Low'].min()) if not hist.empty else ltp
            close = float(hist['Close'].iloc[-1]) if not hist.empty else ltp
            volume = int(hist['Volume'].sum()) if not hist.empty else 0
            prev_close = float(info.previous_close) if hasattr(info, 'previous_close') else ltp
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
            logger.error(f"Yahoo Finance fallback failed for {symbol}: {e}")
            raise

    async def _get_ohlcv_yfinance(
        self,
        symbol: str,
        period: str = "1d",
        interval: str = "5m",
    ) -> list[OHLCV]:
        """Fallback to Yahoo Finance for OHLCV data."""
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
            logger.error(f"Yahoo Finance OHLCV fallback failed for {symbol}: {e}")
            return []
