# AI Z Trading Platform - Week 1 Implementation Guide

## 🎯 Week 1 Goals
Fix the 4 critical blockers to enable paper trading with real Angel One market data

---

## TASK 1: Install SmartAPI SDK (30 minutes)

### Step 1.1: Update requirements.txt
**File:** `backend/requirements.txt`

**Change:**
```diff
- # smartapi-python==1.3.4
+ smartapi-python==1.3.4
```

### Step 1.2: Rebuild Docker Image
```bash
cd c:\Users\Z\Desktop\trading_project\aiz-trading1
docker compose -f docker-compose.dev.yml build backend
```

### Step 1.3: Verify Installation
```bash
docker compose -f docker-compose.dev.yml up backend -d
docker compose -f docker-compose.dev.yml exec backend python -c "import SmartApi; print('✅ SmartAPI imported successfully')"
```

**Expected Output:**
```
✅ SmartAPI imported successfully
```

---

## TASK 2: Create Market Data Service Layer (2-3 hours)

### Step 2.1: Create Base Market Data Provider
**New File:** `backend/app/services/market_data/__init__.py`

```python
"""
Market Data Service — provides real market data from various sources.
Separated from broker to enable: real prices + paper trading
"""
from app.config import settings

async def get_market_data_provider():
    """Returns the configured market data provider."""
    provider_name = settings.data_provider.lower()
    
    if provider_name == "angelone":
        from app.services.market_data.angelone import AngelOneMarketData
        provider = AngelOneMarketData()
        await provider.connect()
        return provider
    else:  # Default to Angel One
        from app.services.market_data.angelone import AngelOneMarketData
        provider = AngelOneMarketData()
        await provider.connect()
        return provider

# Singleton instance
_provider_instance = None

async def get_active_market_data() -> 'MarketDataProvider':
    global _provider_instance
    if _provider_instance is None:
        _provider_instance = await get_market_data_provider()
    return _provider_instance
```

### Step 2.2: Create Base Provider Class
**New File:** `backend/app/services/market_data/base.py`

```python
"""
Abstract base for all market data providers.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List
import pandas as pd


@dataclass
class Quote:
    symbol: str
    ltp: float
    open: float
    high: float
    low: float
    close: float
    volume: int
    change_pct: float


class MarketDataProvider(ABC):
    """Abstract market data provider interface."""

    @abstractmethod
    async def connect(self) -> bool:
        """Authenticate and connect to data source."""
        pass

    @abstractmethod
    async def get_quote(self, symbol: str) -> Quote:
        """Get live quote for a symbol."""
        pass

    @abstractmethod
    async def get_historical(
        self,
        symbol: str,
        period: str = "1d",
        interval: str = "5m",
    ) -> pd.DataFrame:
        """
        Get historical OHLCV data.
        
        Returns DataFrame with columns:
        - time (datetime index)
        - open, high, low, close, volume
        """
        pass

    @abstractmethod
    async def is_market_open(self) -> bool:
        """Check if market is currently open."""
        pass

    @abstractmethod
    def get_available_symbols(self) -> List[str]:
        """Get list of available trading symbols."""
        pass
```

### Step 2.3: Create Angel One Market Data Provider
**New File:** `backend/app/services/market_data/angelone.py`

```python
"""
AngelOne Market Data Provider — get real NSE quotes from SmartAPI.
"""
import pyotp
import pandas as pd
from datetime import datetime, time as dtime
from zoneinfo import ZoneInfo
from loguru import logger
from SmartApi import SmartConnect

from app.services.market_data.base import MarketDataProvider, Quote
from app.config import settings


class AngelOneMarketData(MarketDataProvider):
    """Provides real NSE market data via Angel One SmartAPI."""

    NSE_EXCHANGE = "NSE"

    def __init__(self):
        self.api = SmartConnect(api_key=settings.angel_api_key)
        self.session_data = None
        self.auth_token = None
        self.feed_token = None

    async def connect(self) -> bool:
        """Authenticate with Angel One."""
        try:
            if not settings.angel_api_key:
                logger.error("ANGEL_API_KEY not configured")
                return False

            totp = pyotp.TOTP(settings.angel_totp_secret).now()
            self.session_data = self.api.generateSession(
                settings.angel_client_id,
                settings.angel_password,
                totp,
            )

            if self.session_data and self.session_data.get("status"):
                self.auth_token = self.session_data.get("data", {}).get("jwtToken")
                self.feed_token = self.session_data.get("data", {}).get("feedToken")
                logger.info("AngelOne market data connected ✅")
                return True

            logger.error(f"AngelOne auth failed: {self.session_data}")
            return False

        except Exception as e:
            logger.error(f"AngelOne connection error: {e}")
            return False

    async def get_quote(self, symbol: str) -> Quote:
        """Fetch live quote from Angel One."""
        try:
            if not self.session_data:
                raise RuntimeError("Not connected to Angel One")

            data = self.api.ltpData(self.NSE_EXCHANGE, symbol, "")

            if not data or data.get("status") != True:
                raise ValueError(f"Invalid response for {symbol}: {data}")

            ltp_data = data.get("data", {})
            ltp = float(ltp_data.get("ltp", 0))
            prev_close = float(ltp_data.get("prev_close", ltp))
            change_pct = ((ltp - prev_close) / prev_close * 100) if prev_close else 0

            return Quote(
                symbol=symbol,
                ltp=round(ltp, 2),
                open=round(float(ltp_data.get("open", ltp)), 2),
                high=round(float(ltp_data.get("high", ltp)), 2),
                low=round(float(ltp_data.get("low", ltp)), 2),
                close=round(float(ltp_data.get("close", ltp)), 2),
                volume=int(ltp_data.get("volume", 0)),
                change_pct=round(change_pct, 2),
            )

        except Exception as e:
            logger.error(f"Quote error for {symbol}: {e}")
            raise

    async def get_historical(
        self,
        symbol: str,
        period: str = "1d",
        interval: str = "5m",
    ) -> pd.DataFrame:
        """
        Fetch historical OHLCV data from Angel One.
        Note: Angel One provides only 90 days of data.
        For backtesting, use yfinance separately.
        """
        try:
            # Angel One endpoint for historical data
            # Note: Implementation depends on Angel One API version
            # For now, fall back to yfinance for historical data
            import yfinance as yf
            ticker = yf.Ticker(f"{symbol}.NS")
            hist = ticker.history(period=period, interval=interval)

            if hist.empty:
                raise ValueError(f"No data for {symbol}")

            # Standardize column names
            hist.columns = ['open', 'high', 'low', 'close', 'volume', 'dividends', 'stock_splits']
            hist = hist[['open', 'high', 'low', 'close', 'volume']]
            hist = hist.round(2)
            hist.index.name = 'time'

            return hist

        except Exception as e:
            logger.error(f"Historical data error for {symbol}: {e}")
            raise

    async def is_market_open(self) -> bool:
        """Check if NSE is open (9:15 AM - 3:30 PM IST, weekdays only)."""
        now = datetime.now(ZoneInfo("Asia/Kolkata"))
        
        # Markets closed on weekends
        if now.weekday() >= 5:
            return False
        
        # Market hours: 9:15 AM to 3:30 PM
        market_open = dtime(9, 15)
        market_close = dtime(15, 30)
        
        return market_open <= now.time() <= market_close

    def get_available_symbols(self) -> list[str]:
        """Return list of NSE symbols we support."""
        return [
            "RELIANCE", "TCS", "HDFCBANK", "INFY", "WIPRO",
            "ICICIBANK", "BAJFINANCE", "SBIN", "ITC", "KOTAKBANK",
            "HCLTECH", "AXISBANK", "LT", "MARUTI", "SUNPHARMA",
            "TITAN", "BAJAJFINSV", "TECHM", "ASIANPAINT", "ULTRACEMCO",
            "POWERGRID", "NTPC", "ONGC", "COALINDIA", "HINDALCO",
        ]
```

---

## TASK 3: Configure Angel One Credentials (1 hour)

### Step 3.1: Create Angel One Account
1. Go to https://www.angelone.in/
2. Click "Sign Up"
3. Enter email, phone, follow KYC
4. Verify account

### Step 3.2: Get API Key
1. Login to Angel One account
2. Go to https://smartapi.angelone.in/
3. Click "Create App"
4. Fill in app name, redirect URL, get API Key
5. Save your: **API Key**

### Step 3.3: Enable 2FA and Get TOTP Secret
1. In Angel One app settings, enable 2FA
2. Choose "Authenticator" option
3. Scan QR code with Google Authenticator or Authy
4. Save your: **TOTP Secret** (the long alphanumeric string)

### Step 3.4: Create .env File
**File:** `c:\Users\Z\Desktop\trading_project\aiz-trading1\.env`

Add or update these variables:
```env
# AngelOne Credentials
ANGEL_API_KEY=your_api_key_here
ANGEL_CLIENT_ID=your_client_id_here
ANGEL_PASSWORD=your_angel_password_here
ANGEL_TOTP_SECRET=your_totp_secret_here

# Market Data
DATA_PROVIDER=angelone

# Broker (keep as paper for now)
ACTIVE_BROKER=paper
TRADING_MODE=paper
```

### Step 3.5: Verify .env is in Docker
Ensure `docker-compose.dev.yml` loads `.env`:

```yaml
backend:
  env_file: .env  # ← This line should exist
```

---

## TASK 4: Update app/config.py (30 minutes)

**File:** `backend/app/config.py`

Add this setting after existing broker settings:

```python
    # =========================================================
    # Market Data Provider
    # =========================================================
    data_provider: str = "angelone"  # Can be: angelone, yfinance
```

Also ensure these exist:
```python
    @property
    def redis_url(self) -> str:
        password = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{password}{self.redis_host}:{self.redis_port}/0"

    @property
    def cors_origins(self) -> list[str]:
        return self.allowed_origins.split(",")

    @property
    def watchlist_symbols(self) -> list[str]:
        return ["RELIANCE", "TCS", "HDFCBANK", "INFY", "WIPRO"]
```

---

## TASK 5: Update PaperBroker to Use Market Data Service (1-2 hours)

**File:** `backend/app/services/broker/paper_trader.py`

Replace entire file with:

```python
"""
Paper Trading Broker — simulates orders without real money.
Uses real market data from MarketDataProvider.
"""
import uuid
from datetime import datetime
from typing import Literal
from loguru import logger

from app.services.broker.base import BrokerBase, OrderResult, Quote
from app.services.market_data import get_active_market_data
from app.config import settings


class PaperBroker(BrokerBase):
    """
    Paper trading broker.
    Gets real market prices from MarketDataProvider (Angel One).
    Simulates order execution without using capital.
    """

    def __init__(self):
        self.capital = settings.trading_capital
        self.positions: dict[str, dict] = {}
        self.order_history: list[dict] = []

    async def connect(self) -> bool:
        logger.info("🔵 Paper trading broker connected. No real money at risk.")
        return True

    async def get_quote(self, symbol: str) -> Quote:
        """Get quote from market data provider (Angel One)."""
        try:
            market_data = await get_active_market_data()
            return await market_data.get_quote(symbol)
        except Exception as e:
            logger.error(f"Failed to get quote for {symbol}: {e}")
            raise

    async def place_order(
        self,
        symbol: str,
        action: Literal["buy", "sell"],
        quantity: int,
        order_type: str = "MARKET",
        price: float | None = None,
    ) -> OrderResult:
        """Simulate order execution with real market prices."""
        
        quote = await self.get_quote(symbol)
        exec_price = price or quote.ltp
        order_id = str(uuid.uuid4())[:12].upper()
        cost = exec_price * quantity

        if action == "buy":
            if cost > self.capital:
                raise ValueError(
                    f"Insufficient capital: need ₹{cost:.0f}, have ₹{self.capital:.0f}"
                )

            self.capital -= cost
            self.positions[symbol] = {
                "quantity": quantity,
                "avg_price": exec_price,
                "opened_at": datetime.utcnow().isoformat(),
            }
            logger.info(
                f"📈 PAPER BUY: {quantity}x {symbol} @ ₹{exec_price:.2f} | "
                f"Order: {order_id} | Capital: ₹{self.capital:.0f}"
            )

        elif action == "sell":
            if symbol not in self.positions:
                raise ValueError(f"No position in {symbol} to sell")

            pos = self.positions[symbol]
            if pos["quantity"] != quantity:
                raise ValueError(
                    f"Quantity mismatch: have {pos['quantity']}, requested {quantity}"
                )

            entry = pos["avg_price"]
            profit = (exec_price - entry) * quantity
            self.capital += exec_price * quantity

            logger.info(
                f"📉 PAPER SELL: {quantity}x {symbol} @ ₹{exec_price:.2f} | "
                f"Profit: ₹{profit:.2f} | Capital: ₹{self.capital:.0f}"
            )

            del self.positions[symbol]

        self.order_history.append({
            "order_id": order_id,
            "symbol": symbol,
            "action": action,
            "quantity": quantity,
            "price": exec_price,
            "timestamp": datetime.utcnow().isoformat(),
        })

        return OrderResult(
            order_id=order_id,
            symbol=symbol,
            action=action,
            quantity=quantity,
            price=exec_price,
            status="executed",
            is_paper=True,
        )

    async def cancel_order(self, order_id: str) -> bool:
        logger.warning(f"Paper trading does not support cancellations: {order_id}")
        return False

    async def get_positions(self) -> list[dict]:
        """Get all open positions."""
        return [
            {
                "symbol": symbol,
                "quantity": pos["quantity"],
                "avg_price": pos["avg_price"],
            }
            for symbol, pos in self.positions.items()
        ]

    async def get_balance(self) -> float:
        """Get available capital."""
        return self.capital

    async def is_market_open(self) -> bool:
        """Check if market is open."""
        market_data = await get_active_market_data()
        return await market_data.is_market_open()
```

---

## TASK 6: Update Market Router (1-2 hours)

**File:** `backend/app/routers/market.py`

Replace the quotes and ohlcv endpoints:

```python
from fastapi import APIRouter, Depends
from app.services.market_data import get_active_market_data
from app.core.security import get_current_user
from app.models.user import User
from app.config import settings

router = APIRouter()


@router.get("/quotes")
async def get_quotes(current_user: User = Depends(get_current_user)):
    """Get live quotes for watchlist symbols."""
    market_data = await get_active_market_data()
    quotes = []
    
    for symbol in settings.watchlist_symbols:
        try:
            quote = await market_data.get_quote(symbol)
            quotes.append({
                "symbol": quote.symbol,
                "ltp": quote.ltp,
                "open": quote.open,
                "high": quote.high,
                "low": quote.low,
                "close": quote.close,
                "volume": quote.volume,
                "change_pct": quote.change_pct,
            })
        except Exception as e:
            # Log but continue
            pass
    
    return quotes


@router.get("/ohlcv/{symbol}")
async def get_ohlcv(
    symbol: str,
    period: str = "1d",
    interval: str = "5m",
    current_user: User = Depends(get_current_user),
):
    """Get historical OHLCV data for charting."""
    market_data = await get_active_market_data()
    hist = await market_data.get_historical(symbol, period, interval)
    
    candles = []
    for ts, row in hist.iterrows():
        candles.append({
            "time": int(ts.timestamp()),
            "open": round(float(row["open"]), 2),
            "high": round(float(row["high"]), 2),
            "low": round(float(row["low"]), 2),
            "close": round(float(row["close"]), 2),
            "volume": int(row["volume"]),
        })
    
    return {"symbol": symbol, "interval": interval, "candles": candles}
```

---

## TESTING CHECKLIST (Day 5)

After completing all tasks, run these tests:

### Test 1: Docker Build
```bash
docker compose -f docker-compose.dev.yml build backend
```
✅ Should complete without errors

### Test 2: Backend Startup
```bash
docker compose -f docker-compose.dev.yml up backend -d
docker compose -f docker-compose.dev.yml logs backend
```
✅ Should show "Uvicorn running on 0.0.0.0:8000"

### Test 3: SmartAPI Import
```bash
docker compose -f docker-compose.dev.yml exec backend python -c "from SmartApi import SmartConnect; print('✅ SmartAPI installed')"
```
✅ Should print "✅ SmartAPI installed"

### Test 4: Market Data Service
```bash
docker compose -f docker-compose.dev.yml exec backend python -c "
import asyncio
from app.services.market_data import get_active_market_data
async def test():
    md = await get_active_market_data()
    quote = await md.get_quote('HDFCBANK')
    print(f'HDFCBANK: ₹{quote.ltp}')
asyncio.run(test())
"
```
✅ Should print "HDFCBANK: ₹1950.25" (actual price)

### Test 5: API Endpoint
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/market/quotes
```
✅ Should return live prices

### Test 6: Paper Trading
```bash
docker compose -f docker-compose.dev.yml exec backend python -c "
import asyncio
from app.services.broker import get_active_broker
async def test():
    broker = await get_active_broker()
    result = await broker.place_order('HDFCBANK', 'buy', 1)
    print(f'✅ Order {result.order_id} executed at ₹{result.price}')
asyncio.run(test())
"
```
✅ Should show successful paper trade

---

## 🎯 Week 1 Completion Criteria

By end of Friday:

- [ ] SmartAPI installed and importable
- [ ] Market data service created and working
- [ ] Angel One credentials configured
- [ ] Paper broker updated to use market data service
- [ ] Market router endpoints returning live Angel One prices
- [ ] All 6 tests above passing
- [ ] Dashboard can fetch live quotes
- [ ] Paper trades execute with real market prices

**If all checks pass, you have completed Week 1 and are ready for Week 2!** ✅

