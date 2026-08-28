# WEEK 1 QUICK CHECKLIST
**Ready to Execute** | Aug 28 - Sep 3, 2026

---

## ✅ PRE-WORK (What I Already Did)

- [x] Created market data service abstraction
  - [x] `backend/app/services/market_data/__init__.py`
  - [x] `backend/app/services/market_data/base.py`
  - [x] `backend/app/services/market_data/angelone.py`
  - [x] `backend/app/services/market_data/yfinance_provider.py`

- [x] Updated PaperBroker to use market data service
  - [x] `backend/app/services/broker/paper_trader.py`

- [x] Updated market router endpoints
  - [x] `backend/app/routers/market.py`

- [x] Enhanced configuration
  - [x] Added 50+ strategy parameters to `backend/app/config.py`
  - [x] Added `data_provider` configuration
  - [x] Added `watchlist_symbols` property

- [x] Updated dependencies
  - [x] Uncommented `smartapi-python==1.3.4` in `backend/requirements.txt`

- [x] Created test & setup docs
  - [x] `test-week1.sh` - Verification script
  - [x] `WEEK1_IMPLEMENTATION_GUIDE.md` - Full setup guide

---

## YOUR TASKS (Do This)

### TASK 1: Docker Rebuild (15 min)
**Status:** ⬜ Not Started

```bash
cd c:\Users\Z\Desktop\trading_project\aiz-trading1
docker-compose build --no-cache
```

**Verify:**
- [ ] Docker build completes without errors
- [ ] SmartAPI package installed
- [ ] No port conflicts

**Expected Time:** 10-15 minutes (computer time)
**Your Active Time:** 2-3 minutes (monitoring)

---

### TASK 2: Update .env (Optional - 5 min)
**Status:** ⬜ Not Started

If you want to setup Angel One (REAL NSE data):

```
ANGEL_API_KEY=your_api_key
ANGEL_CLIENT_ID=your_client_id
ANGEL_PASSWORD=your_password
ANGEL_TOTP_SECRET=your_totp_secret
DATA_PROVIDER=angelone
```

**Alternative:** Leave blank to use Yahoo Finance (automatic fallback)

**If setting up Angel One:**
1. [ ] Create account: https://www.angelbroking.com
2. [ ] Generate API key from Angel One app
3. [ ] Copy TOTP secret from settings
4. [ ] Update .env file
5. [ ] Restart Docker: `docker-compose down && docker-compose up -d`

**Expected Time:** 30 min (if doing Angel One setup)
**Expected Time:** 0 min (if skipping, will use Yahoo Finance)

---

### TASK 3: Run Verification Tests (30 min)
**Status:** ⬜ Not Started

```bash
# Linux/Mac
bash test-week1.sh

# Windows PowerShell
wsl bash test-week1.sh
```

**Checklist:**
- [ ] Test 1: SmartAPI installed ✓
- [ ] Test 2: Market data service imports ✓
- [ ] Test 3: PaperBroker uses market data ✓
- [ ] Test 4: Market router uses market data ✓
- [ ] Test 5: Config has strategy parameters ✓
- [ ] Test 6: Quote fetching works ✓
- [ ] Test 7: Database connection OK ✓
- [ ] Test 8: Docker services running ✓

**If any test fails:**
- [ ] Read error message carefully
- [ ] Check Docker logs: `docker logs backend`
- [ ] Review WEEK1_IMPLEMENTATION_GUIDE.md troubleshooting section

**Expected Time:** 20 min
**Your Active Time:** 10-15 min (waiting for tests, then fixing)

---

### TASK 4: Manual Testing (15 min)
**Status:** ⬜ Not Started

Test getting real quotes:

```bash
# Connect to backend
docker exec -it aiz-trading1-backend-1 bash

# Inside container, test quote fetching
python -c "
import asyncio
from app.services.market_data import get_active_market_data

async def test():
    md = await get_active_market_data()
    quote = await md.get_quote('HDFCBANK')
    print(f'✓ Got HDFCBANK quote: ₹{quote.ltp}')

asyncio.run(test())
"
```

**Expected output:**
```
✓ Got HDFCBANK quote: ₹1950.25
```

**If works:**
- [ ] Real prices are flowing ✓
- [ ] Market data service is active ✓
- [ ] Move to next step

**Expected Time:** 10 min

---

### TASK 5: Git Commit (10 min)
**Status:** ⬜ Not Started

```bash
# Review changes
git status

# Stage all changes
git add -A

# Commit with message
git commit -m "feat(infrastructure): Angel One market data integration

- Market data provider abstraction (base.py)
- Angel One SmartAPI implementation (angelone.py)
- Yahoo Finance fallback provider (yfinance_provider.py)
- Updated PaperBroker to use market data service
- Updated market router endpoints
- Added 50+ strategy configuration parameters
- SmartAPI SDK installed in Docker
- All verification tests passing"

# Create tag for checkpoint
git tag checkpoint-week1

# Push to repository
git push origin main
git push origin checkpoint-week1
```

**Verify:**
- [ ] All changes staged (`git status` is clean)
- [ ] Commit message is descriptive
- [ ] Tag created
- [ ] Push successful

**Expected Time:** 5-10 min

---

## 📊 TIMELINE (REALISTIC ESTIMATE)

| Task | Time | Status |
|------|------|--------|
| 1. Docker Rebuild | 15 min | ⬜ |
| 2. Setup Angel One (optional) | 0-30 min | ⬜ |
| 3. Run Tests | 30 min | ⬜ |
| 4. Manual Testing | 15 min | ⬜ |
| 5. Git Commit | 10 min | ⬜ |
| **TOTAL** | **70-100 min** | |

**Real Time:** 1.5-2 hours (with breaks)
**Your Active Time:** 45-60 min (rest is waiting)

---

## 🎯 SUCCESS CRITERIA

By Friday (Aug 30), you should have:

- ✓ Real NSE prices flowing through system
- ✓ Paper trading uses real market prices
- ✓ All tests passing
- ✓ Angel One configured (optional but recommended)
- ✓ Git checkpoint created
- ✓ Ready for Week 2 (strategy engine)

---

## 🆘 IF SOMETHING BREAKS

1. **Check Docker:** `docker-compose ps`
2. **View logs:** `docker logs backend`
3. **Restart:** `docker-compose down && docker-compose up -d`
4. **Rebuild:** `docker-compose build --no-cache`
5. **Read guide:** Check WEEK1_IMPLEMENTATION_GUIDE.md troubleshooting

---

## 📝 NOTES

- **Angel One is optional**: System works with Yahoo Finance fallback
- **SmartAPI must install**: Uncommented in requirements.txt, rebuild needed
- **No DB migration needed**: Uses existing schema
- **Paper trading still works**: Just gets real prices now
- **Week 2 starts immediately after**: Strategy engine generation

---

## 🚀 READY?

1. Start Task 1 (Docker Rebuild)
2. Follow checklist
3. Run tests
4. Create git commit
5. Report back: "Week 1 complete, real prices flowing!" ✅

**Estimated completion: Friday, Aug 30, 2026** 🎯

