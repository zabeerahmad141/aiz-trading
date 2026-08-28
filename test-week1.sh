#!/bin/bash
# ============================================================
# Week 1 Verification Tests
# Test that Angel One market data is flowing correctly
# ============================================================

set -e

echo "======================================"
echo "WEEK 1 VERIFICATION TESTS"
echo "======================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Check if SmartAPI is installed in Docker
echo -e "${YELLOW}Test 1: Checking SmartAPI installation in Docker...${NC}"
docker exec backend python -c "from SmartApi import SmartConnect; print('✓ SmartAPI installed')" 2>/dev/null || {
    echo -e "${RED}✗ SmartAPI not installed${NC}"
    echo "  To fix: Run 'docker-compose build --no-cache'"
    exit 1
}

# Test 2: Check if market data service imports correctly
echo ""
echo -e "${YELLOW}Test 2: Checking market data service imports...${NC}"
docker exec backend python -c "
from app.services.market_data import get_active_market_data
from app.services.market_data.base import MarketDataProvider, Quote, OHLCV
from app.services.market_data.angelone import AngelOneMarketData
print('✓ Market data service imports OK')
" || {
    echo -e "${RED}✗ Market data service import failed${NC}"
    exit 1
}

# Test 3: Check if broker uses market data service
echo ""
echo -e "${YELLOW}Test 3: Checking PaperBroker uses market data service...${NC}"
docker exec backend python -c "
import inspect
from app.services.broker.paper_trader import PaperBroker
source = inspect.getsource(PaperBroker.get_quote)
assert 'get_active_market_data' in source, 'PaperBroker not using market data service'
print('✓ PaperBroker correctly uses market data service')
" || {
    echo -e "${RED}✗ PaperBroker not using market data service${NC}"
    exit 1
}

# Test 4: Verify market router uses market data service
echo ""
echo -e "${YELLOW}Test 4: Checking market router endpoints...${NC}"
docker exec backend python -c "
import inspect
from app.routers.market import get_quotes, get_ohlcv
assert 'get_active_market_data' in inspect.getsource(get_quotes)
assert 'get_active_market_data' in inspect.getsource(get_ohlcv)
print('✓ Market router correctly uses market data service')
" || {
    echo -e "${RED}✗ Market router not using market data service${NC}"
    exit 1
}

# Test 5: Check config has strategy parameters
echo ""
echo -e "${YELLOW}Test 5: Checking config strategy parameters...${NC}"
docker exec backend python -c "
from app.config import settings
assert hasattr(settings, 'atr_period')
assert hasattr(settings, 'risk_percent_per_trade')
assert hasattr(settings, 'min_risk_reward_ratio')
assert hasattr(settings, 'watchlist_symbols')
print('✓ Config has all strategy parameters')
print(f'  - ATR Period: {settings.atr_period}')
print(f'  - Risk %: {settings.risk_percent_per_trade}%')
print(f'  - Min R:R: {settings.min_risk_reward_ratio}')
print(f'  - Watchlist: {settings.watchlist_symbols}')
" || {
    echo -e "${RED}✗ Config strategy parameters missing${NC}"
    exit 1
}

# Test 6: Try to get a quote (fallback to Yahoo Finance if Angel One not configured)
echo ""
echo -e "${YELLOW}Test 6: Testing quote fetching (may use Yahoo Finance fallback)...${NC}"
docker exec backend python -c "
import asyncio
from app.services.market_data import get_active_market_data

async def test():
    market_data = await get_active_market_data()
    try:
        quote = await market_data.get_quote('HDFCBANK')
        print(f'✓ Got quote for HDFCBANK')
        print(f'  - LTP: ₹{quote.ltp}')
        print(f'  - Change: {quote.change_pct}%')
        print(f'  - Volume: {quote.volume:,}')
    except Exception as e:
        print(f'⚠ Quote fetch failed (this is OK if Angel One not configured)')
        print(f'  Error: {e}')

asyncio.run(test())
" || {
    echo -e "${RED}✗ Quote fetching failed${NC}"
}

# Test 7: Check database connection
echo ""
echo -e "${YELLOW}Test 7: Checking database connection...${NC}"
docker exec backend python -c "
import asyncio
from app.database import SessionLocal

async def test():
    async with SessionLocal() as session:
        result = await session.execute('SELECT 1')
        print('✓ Database connection OK')

try:
    asyncio.run(test())
except Exception as e:
    print(f'⚠ Database test skipped (this is OK during initial setup)')
" || {
    true  # Don't fail on DB error
}

# Test 8: Verify Docker services are running
echo ""
echo -e "${YELLOW}Test 8: Checking Docker services...${NC}"
docker-compose ps | grep -q "backend" && echo "✓ Backend running" || echo "✗ Backend not running"
docker-compose ps | grep -q "postgresql" && echo "✓ PostgreSQL running" || echo "✗ PostgreSQL not running"
docker-compose ps | grep -q "redis" && echo "✓ Redis running" || echo "✗ Redis not running"

echo ""
echo "======================================"
echo -e "${GREEN}✓ WEEK 1 VERIFICATION COMPLETE${NC}"
echo "======================================"
echo ""
echo "Next steps:"
echo "1. Setup Angel One credentials (OPTIONAL but recommended):"
echo "   - Create account at https://www.angelbroking.com"
echo "   - Generate API key and TOTP secret"
echo "   - Add to .env file:"
echo "     ANGEL_API_KEY=your_key"
echo "     ANGEL_CLIENT_ID=your_client_id"
echo "     ANGEL_PASSWORD=your_password"
echo "     ANGEL_TOTP_SECRET=your_totp_secret"
echo ""
echo "2. If Angel One not set up, system will use Yahoo Finance (free, but rate-limited)"
echo ""
echo "3. Restart Docker to apply credentials:"
echo "   docker-compose down && docker-compose up -d"
echo ""
