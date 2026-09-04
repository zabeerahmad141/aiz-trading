"""
Angel One SmartAPI market data provider.
Free NSE market data via Angel One broker.
"""
import asyncio
import json
import os
from urllib.request import urlopen
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
        self._instrument_master_loaded = False
        self._connect_lock = asyncio.Lock()
        self._max_request_attempts = max(1, int(os.getenv("ANGELONE_MAX_REQUEST_ATTEMPTS", "1")))
        self._reconnect_delay = max(0.0, float(os.getenv("ANGELONE_RECONNECT_DELAY_SECONDS", "1")))
        self._next_connect_attempt = 0.0

    @staticmethod
    def _instrument_master_url() -> str:
        return "https://margincalculator.angelone.in/OpenAPI_File/files/OpenAPIScripMaster.json"

    async def _load_instrument_master(self) -> bool:
        """Load Angel One's public scrip master for symbol-token resolution."""
        if self._instrument_master_loaded:
            return True

        try:
            def download_master():
                with urlopen(self._instrument_master_url(), timeout=15) as response:
                    return json.loads(response.read().decode("utf-8"))

            instruments = await asyncio.to_thread(download_master)
            for instrument in instruments or []:
                if instrument.get("exch_seg") != "NSE":
                    continue
                symbol = str(instrument.get("symbol", "")).upper()
                if symbol.endswith("-EQ"):
                    symbol = symbol[:-3]
                token = instrument.get("token") or instrument.get("symboltoken")
                if symbol and token:
                    self.instrument_tokens.setdefault(symbol, str(token))

            self._instrument_master_loaded = bool(self.instrument_tokens)
            logger.info("Loaded {} NSE instrument tokens from Angel One scrip master", len(self.instrument_tokens))
            return self._instrument_master_loaded
        except Exception as exc:
            logger.error("Angel One scrip master download failed: {}", exc)
            return False

    @staticmethod
    def _sdk_supports_ltp_lookup(smartapi_obj) -> bool:
        """Return True when the live quote method uses the compatible signature.

        This SDK version expects:
        SmartConnect.ltpData(exchange, tradingsymbol, symboltoken)
        not the newer dict-based format used in some examples.
        """
        return hasattr(smartapi_obj, "ltpData")

    async def connect(self) -> bool:
        """Authenticate with Angel One SmartAPI."""
        now = asyncio.get_running_loop().time()
        if now < self._next_connect_attempt:
            return False
        async with self._connect_lock:
            now = asyncio.get_running_loop().time()
            if now < self._next_connect_attempt:
                return False
            return await self._connect_once()

    async def _connect_once(self) -> bool:
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
            login_response = await asyncio.to_thread(
                self.smartapi.generateSession,
                settings.angel_client_id,
                settings.angel_password,
                totp_value,
            )

            if login_response.get("status"):
                self.jwt_token = login_response.get("data", {}).get("jwtToken")
                self.connected = True
                masked_client = f"***{settings.angel_client_id[-4:]}"
                logger.info("✓ Angel One connected | Client: {}", masked_client)
                return True
            else:
                logger.error("Angel One login failed with status=false")
                self._next_connect_attempt = asyncio.get_running_loop().time() + 30
                return False

        except ImportError:
            logger.error("SmartAPI SDK not installed. Install: pip install smartapi-python")
            return False
        except Exception as e:
            logger.error(f"Angel One connection error: {e}")
            self.connected = False
            self._next_connect_attempt = asyncio.get_running_loop().time() + 30
            return False

    def _invalidate_connection(self):
        self.connected = False
        self.jwt_token = None
        self.smartapi = None

    async def _call_with_reconnect(self, operation):
        """Retry one broker request after re-authentication, without retry storms."""
        for attempt in range(self._max_request_attempts):
            if not self.connected and not await self.connect():
                break
            try:
                response = await asyncio.to_thread(operation)
                if response and response.get("status", True):
                    return response
                raise ConnectionError("Angel One returned an unsuccessful response")
            except Exception as exc:
                self._invalidate_connection()
                if attempt + 1 < self._max_request_attempts:
                    logger.warning("Angel One request failed; reconnecting before retry: {}", exc)
                    if self._reconnect_delay:
                        await asyncio.sleep(self._reconnect_delay)
        return None

    async def get_quote(self, symbol: str) -> Quote:
        """
        Fetch live quote from Angel One.
        
        Falls back to Yahoo Finance if Angel One unavailable.
        """
        if not self.connected and not await self.connect():
            if settings.is_live_trading_allowed:
                raise ConnectionError("Angel One is unavailable; live trading is halted")
            logger.warning("Angel One not connected, falling back to Yahoo Finance")
            return await self._get_quote_yfinance(symbol)

        try:
            # Get instrument token for symbol
            token = await self._get_instrument_token(symbol)
            if not token:
                logger.warning(f"Symbol {symbol} not found in Angel One")
                return await self._get_quote_yfinance(symbol)

            # Fetch LTP
            ltp_data = await self._call_with_reconnect(
                lambda: self.smartapi.ltpData(
                    exchange="NSE",
                    tradingsymbol=self._angel_tradingsymbol(symbol),
                    symboltoken=str(token),
                )
            )
            
            if not ltp_data or not ltp_data.get("data"):
                logger.warning(f"No quote data for {symbol}, falling back to Yahoo Finance")
                return await self._get_quote_yfinance(symbol)

            ltp_payload = ltp_data.get("data", {})
            if isinstance(ltp_payload, dict) and isinstance(ltp_payload.get("fetched"), list):
                ltp_info = ltp_payload["fetched"][0] if ltp_payload["fetched"] else {}
            elif isinstance(ltp_payload, dict):
                ltp_info = ltp_payload
            else:
                ltp_info = ltp_payload[0] if ltp_payload else {}
            ltp = float(ltp_info.get("ltp", 0) or 0)
            if ltp <= 0:
                raise ValueError(f"Angel One returned no valid LTP for {symbol}")

            # ltpData already includes session OHLC and change fields. Avoid
            # a second historical request for every symbol in the watchlist.
            previous_close = float(ltp_info.get("close", ltp) or ltp)
            open_price = float(ltp_info.get("open", ltp) or ltp)
            high_price = float(ltp_info.get("high", ltp) or ltp)
            low_price = float(ltp_info.get("low", ltp) or ltp)
            volume = int(float(ltp_info.get("tradeVolume", 0) or 0))
            change_pct = float(ltp_info.get("percentChange", 0) or 0)

            return Quote(
                symbol=symbol,
                ltp=round(ltp, 2),
                open=round(open_price, 2),
                high=round(high_price, 2),
                low=round(low_price, 2),
                close=round(previous_close, 2),
                volume=volume,
                change_pct=round(change_pct, 2),
                timestamp=datetime.now(ZoneInfo("Asia/Kolkata")),
                source="angelone",
            )

        except Exception as e:
            logger.error(f"Angel One quote error for {symbol}: {e}")
            if settings.is_live_trading_allowed:
                raise ConnectionError(f"Angel One quote unavailable for {symbol}; live trading is halted") from e
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
            if settings.is_live_trading_allowed:
                raise ConnectionError("Angel One is unavailable; live trading is halted")
            return await self._get_ohlcv_yfinance(symbol, period, interval)

        try:
            token = await self._get_instrument_token(symbol)
            if not token:
                return await self._get_ohlcv_yfinance(symbol, period, interval)

            # Map period/interval to Angel One parameters
            from_date = self._calculate_from_date(period)
            
            # Request candlestick data
            candle_data = await self._call_with_reconnect(
                lambda: self.smartapi.getCandleData({
                    "exchange": "NSE",
                    "symboltoken": token,
                    "interval": self._angel_interval(interval),
                    "fromdate": from_date,
                    "todate": datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%d-%m-%Y"),
                })
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
            if settings.is_live_trading_allowed:
                raise ConnectionError(f"Angel One OHLCV unavailable for {symbol}; live trading is halted") from e
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

        if not await self._load_instrument_master():
            return None

        return self.instrument_tokens.get(symbol)

    @staticmethod
    def _angel_interval(interval: str) -> str:
        return {
            "1m": "ONE_MINUTE",
            "5m": "FIVE_MINUTE",
            "15m": "FIFTEEN_MINUTE",
            "1h": "ONE_HOUR",
            "1d": "ONE_DAY",
        }.get(interval, "FIVE_MINUTE")

    @staticmethod
    def _angel_tradingsymbol(symbol: str) -> str:
        normalized = symbol.strip().upper()
        return normalized if normalized.endswith("-EQ") else f"{normalized}-EQ"

    async def _legacy_get_instrument_token(self, symbol: str) -> Optional[str]:
        """Deprecated compatibility placeholder; token resolution uses the public master."""
        return self.instrument_tokens.get(symbol)

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
