# AI Z Trading Platform — Market Readiness and Development Handoff

## 1. Product Purpose

AI Z is a Docker-based trading platform for paper trading, market observation, strategy validation, and eventual live execution with strict safety gates.

The project currently supports:
- backend FastAPI application
- Postgres persistence
- Redis for runtime support
- frontend dashboard UI
- ML engine for strategy/AI processing
- paper trading as the default mode
- market-data abstraction with Yahoo Finance fallback and Angel One-ready integration path

This project is intended to evolve through the following stages:
1. safe local development
2. market observation
3. paper-trading validation
4. live broker sandbox validation
5. live money only after strict approval gates

---

## 2. Current Status

### Current state: SAFE FOR PAPER TESTING AND OBSERVATION

The product is not ready for live-money execution.

It is ready for:
- deployment in Docker
- backend health checks
- user authentication flow testing
- market-data observation in paper mode
- paper order lifecycle testing
- UI verification
- strategy/ML startup and observation checks

It is not ready for:
- real-money live trading
- unguarded live broker execution
- production deployment without further validation

---

## 3. Verified Runtime Evidence

The following verification steps were executed successfully during the current session:

### Deployment
```bash
docker compose -f docker-compose.dev.yml up -d --build
```

### Service check
```bash
docker compose -f docker-compose.dev.yml ps
```

Observed service states:
- backend: Healthy
- frontend: Up
- ml-engine: Healthy
- postgresql: Healthy
- redis: Healthy

### Backend health
```bash
curl http://localhost:8000/health
```

### Backend status
```bash
curl http://localhost:8000/api/status
```

### Compile check
```bash
docker compose -f docker-compose.dev.yml exec -T backend python -m compileall -q /app/app
```

### Windows smoke check
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\offline-smoke.ps1
```

These checks confirm the stack is functioning and the app is alive in its current safe mode.

---

## 4. Current Configuration and Safety Model

The active configuration is intentionally conservative.

Key defaults in [backend/app/config.py](../backend/app/config.py):
- `ACTIVE_BROKER = "paper"`
- `TRADING_MODE = "paper"`
- `DATA_PROVIDER = "yfinance"`
- Angel One credentials are blank by default

Broker selection logic in [backend/app/services/broker/__init__.py](../backend/app/services/broker/__init__.py):
- if `TRADING_MODE != "live"`, the app resolves to the paper broker
- live broker activation requires explicit live-mode conditions

This means the system is currently refusing to run live execution unless intentionally changed.

---

## 5. What Can Be Tested Right Now

### A. Service startup and health
Test these actions:
1. rebuild and start stack
2. verify backend health endpoint
3. verify status endpoint
4. check postgres and redis health
5. confirm UI loads on port 3000

Files involved:
- [docker-compose.dev.yml](../docker-compose.dev.yml)
- [backend/app/main.py](../backend/app/main.py)
- [backend/app/config.py](../backend/app/config.py)

### B. Authentication flow
Test:
- admin login to backend
- JWT issuance
- JWT use in protected routes

Files involved:
- [backend/app/routers/auth.py](../backend/app/routers/auth.py)
- [backend/app/core/startup.py](../backend/app/core/startup.py)

### C. Market data observation
Test:
- quote fetch for multiple symbols
- OHLCV data fetch
- provider fallback behavior
- watchlist data consumption

Files involved:
- [backend/app/routers/market.py](../backend/app/routers/market.py)
- [backend/app/services/market_data/__init__.py](../backend/app/services/market_data/__init__.py)
- [backend/app/services/market_data/yfinance_provider.py](../backend/app/services/market_data/yfinance_provider.py)

### D. Paper trading lifecycle
Test:
- paper buy order
- trade persistence
- position creation
- position view
- paper sell order
- trade history and status change

Files involved:
- [backend/app/routers/trading.py](../backend/app/routers/trading.py)
- [backend/app/services/broker/paper_trader.py](../backend/app/services/broker/paper_trader.py)

### E. Frontend rendering and dashboard state
Test:
- app loads
- market screen renders
- dashboard displays connected state
- portfolio/trade pages are reachable

Files involved:
- [frontend/src/App.tsx](../frontend/src/App.tsx)
- [frontend/src/pages/Dashboard.tsx](../frontend/src/pages/Dashboard.tsx)

### F. ML / strategy startup observation
Test:
- ML engine starts without crash
- backend remains in healthy state
- strategy modules remain available

Files involved:
- [ml-engine/src/main.py](../ml-engine/src/main.py)

---

## 6. How to Test the Product Properly

### Phase 1: Local smoke validation
Run:
```bash
docker compose -f docker-compose.dev.yml up -d --build
powershell -ExecutionPolicy Bypass -File .\scripts\offline-smoke.ps1
```

This checks:
- compose config integrity
- all required services are running
- backend is healthy
- API status endpoint is correct
- frontend is reachable
- code compiles

### Phase 2: Backend auth validation
Use a real login request and protected API flow.

Example:
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"aiz_pass"}'
```

Then use the returned access token on protected endpoints.

### Phase 3: Market-data validation
Call the market endpoints for a known symbol like HDFCBANK.

Check:
- quote returns a valid number
- timestamp is present
- volume is populated
- OHLCV response contains candles

### Phase 4: Paper-trade validation
Create a paper order and verify:
- status is accepted/executed
- symbol is recorded
- quantity and price are stored
- position is created
- trade history is persisted
- sell exits the trade and updates status

### Phase 5: Risk and exit validation
Validate:
- stop loss integration
- target price logic
- duplicate restriction logic
- max positions logic
- market timing block logic

### Phase 6: Observation-only market testing
This is the pre-live stage where the system is used to observe real quotes and strategy behavior without trading funds.

During this stage:
- keep `TRADING_MODE=paper`
- do not enable live execution
- verify quote freshness and flow
- verify signal generation
- verify trade logs and PnL logic

---

## 7. What Development Is Pending

The project is close to a useful market-observation platform, but several items still need implementation before it is robust enough for live-money deployment.

### 7.1 Test suite coverage
Required:
- API tests for auth, market, portfolio, trading
- broker integration tests
- paper-trading tests
- error-path tests for invalid orders and stale quotes
- offline tests for live mode safety

Implementation approach:
- add pytest suite under `backend/tests/`
- use FastAPI `TestClient`
- verify actual behavior, not mock-only elements
- keep tests real and deterministic

### 7.2 Durable broker state and reconciliation
Required:
- persistent active orders
- reconciliation after app restarts
- traceability for partial fills and stale statuses
- prevention of duplicate positions

Implementation approach:
- persist order state in Postgres
- rehydrate state on startup
- reconcile open positions against actual broker or paper state
- mark stale states and expose a repair workflow

### 7.3 Quote refresh scheduling
Required:
- refresh prices during market hours
- maintain quote freshness thresholds
- detect stale quote windows
- avoid stale executions

Implementation approach:
- use background scheduler or Redis-backed periodic task
- refresh market data at a safe interval
- store quote age metadata
- block orders when timestamps exceed allowed thresholds

### 7.4 Exit management integration
Required:
- stop-loss execution
- target execution
- trailing stop logic
- pre-close exit logic

Implementation approach:
- integrate exit manager with quote refresh loop
- evaluate exits after each refresh
- persist exit decisions and final execution records
- ensure exit can run in both paper and live modes

### 7.5 Position and PnL correctness
Required:
- realized and unrealized PnL
- session summaries
- exposure groupings
- trade-level accounting

Implementation approach:
- compute PnL from persisted trades and positions
- maintain session snapshots
- expose summary endpoints for analytics and front-end display

### 7.6 Live-money guardrails
Required:
- explicit live-mode enablement
- kill switch
- admin override process
- default safe mode remains paper

Implementation approach:
- require manual approval before live mode is enabled
- enforce environment checks before execution
- log every live action with immutable metadata
- block execution unless all validation checks pass

### 7.7 Observable market monitoring
Required:
- market open/close checks in IST
- stale data detection
- anomaly detection for quote gaps
- alerting and logging

Implementation approach:
- add service to identify session status actively
- surface a clear health signal to dashboard
- alert if quote provider fails or stalls

---

## 8. Development Roadmap to Reach Live-Money Readiness

### Stage 1: Production-stable paper environment
Goals:
- stable backend startup
- working auth flow
- working market-data access
- paper trading lifecycle validated
- dashboard state consistent

Deliverables:
- end-to-end paper trade flow
- persistent trade records
- working PnL / position state

### Stage 2: Observation and strategy validation
Goals:
- live market observation with no actual money risk
- strategy signal validation against real quote data
- price, volume, and chart reliability checks

Deliverables:
- observation dashboard
- alerts when data stale or missing
- market-hour logic and session detection

### Stage 3: Broker sandbox validation
Goals:
- use a sandbox or demo broker environment
- verify order lifecycle under realistic conditions
- test order status, fills, and reconciliation

Deliverables:
- broker sandbox orders and audit logs
- reconciliation and error handling
- safe live-mode validation path

### Stage 4: Strict live-mode readiness gate
Goals:
- final risk review
- all guardrails enabled
- no migrations left incomplete
- all order paths tested and logged

Deliverables:
- admin approval record
- emergency-stop mechanism
- live execution audit trail

### Stage 5: Live money only after approval
This is the final step and should only happen after all prior stages pass.

---

## 9. Required Implementation Order

The most efficient path is:

1. stabilize the paper flow
2. verify market-data observations
3. implement automated tests
4. add reconciliation and durable state
5. integrate exit management
6. add refresh scheduling and stale-data checks
7. validate broker sandbox mode
8. then enable live-money only under explicit controls

This order reduces risk and keeps the project safe.

---

## 10. What the System Is Already Good At

The project already has a solid foundation in:
- Dockerized deployment
- FastAPI backend architecture
- Postgres + Redis integration
- safe default paper trading mode
- market-data abstraction
- frontend shell and dashboard structure
- ML engine integration path
- market observation capability in a protected mode

This is a meaningful engineering base, and it is enough to continue building safely.

---

## 11. Final Recommendation

The correct recommendation is:

- continue using the product in paper mode for market observation and order validation
- do not switch to live execution yet
- complete the pending reliability and reconciliation work
- validate strategy behavior with real market data
- only consider live money after sandbox validation and full control checks pass

This product is currently in the correct stage for disciplined observation and controlled paper testing, not for live-money execution.

---

## 12. Direct Next Actions

These are the immediate tasks most important for progressing to full readiness:

1. Add API test coverage for authentication, market quotes, and paper orders
2. Validate full trading lifecycle in paper mode with real quote data
3. Implement durable position/order reconciliation
4. Implement background quote refresh and stale-data detection
5. Integrate stop-loss / target / exit manager into the live flow
6. Validate sandbox broker execution flow
7. Add explicit live-money guardrails

---

## 13. Summary in One Sentence

The platform is operational, healthy, and safe for market observation and paper-trading validation, but it still requires additional reliability, reconciliation, and guardrail work before it is ready for live-money trading.
