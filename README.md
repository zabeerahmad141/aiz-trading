# aiz-trading

## Current Status

The repository is a Docker Compose development stack for an NSE paper-trading platform.
It is safe to develop and test while the market is closed.

### Start locally

```powershell
docker compose -f docker-compose.dev.yml up -d --build
```

- Frontend: http://localhost:3000
- Backend health: http://localhost:8000/health
- Backend API docs: available in development mode at http://localhost:8000/api/docs

### Implemented foundation

- Week 1 market-data provider abstraction, Angel One adapter, and Yahoo Finance fallback.
- ATR, position sizing, trend, regime, entry, support/resistance, signal processing, and exit-decision modules.
- Historical backtest loader and simulator, currently available as ML-engine modules rather than an HTTP/UI workflow.
- API-backed Dashboard, ticker, portfolio sessions, Reports, Alerts, and ML Models pages.
- Paper trading remains the default. Live broker selection requires both `ACTIVE_BROKER` and `TRADING_MODE=live`.
- AI Engine signals are sourced from the ML engine; unavailable model metrics are shown as `N/A`.

### Validation and market-open readiness

```powershell
docker compose -f docker-compose.dev.yml build frontend backend ml-engine
docker compose -f docker-compose.dev.yml exec -T backend python -m compileall -q /app/app
docker compose -f docker-compose.dev.yml ps
```

For a market-independent verification pass on Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\offline-smoke.ps1
```

Synthetic Week 2, Week 3, and Week 4 checks are run inside the relevant containers. Live Angel One quotes, intraday candles, and order execution require NSE market hours and credentials; keep `TRADING_MODE=paper` during testing.

Before testing live data, verify:

1. Docker Compose is healthy: `docker compose -f docker-compose.dev.yml ps`.
2. `/health` and `/api/status` report the expected provider and trading mode.
3. Angel One credentials are configured only when live quotes are required.
4. `TRADING_MODE=paper` is used for the first order and restart/reconciliation checks.
5. No order is considered successful unless it has a positive execution price and a persisted trade record.

### Historical/off-hours behavior

The Dashboard reads stored trades and exposes `/api/portfolio/sessions` for previous completed sessions. A new account with no trades receives an onboarding state. Full intraday equity history still requires a future portfolio-snapshot table and scheduled collector.

### Known pending product work

1. Add durable broker state, position reconciliation, and live quote refresh scheduling.
2. Connect exit management to the trading loop and persist signal history/model metrics.
3. Expand backtest inputs with uploaded historical files and production-strategy parity.
4. Add authentication hardening, order idempotency, migrations, and automated tests.
5. When NSE opens, verify live quotes, candles, paper orders, and exits before considering live-money testing.

Latest checkpoints:

- `7a7f250` - Week 3 backtesting and live Dashboard states
- `23ccaa1` - Historical portfolio sessions
