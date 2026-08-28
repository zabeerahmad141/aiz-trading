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

### Implemented

- Week 1 market-data provider abstraction, Angel One adapter, and Yahoo Finance fallback.
- Week 2 ATR, position sizing, trend, regime, entry, support/resistance, and signal processing.
- Week 3 historical backtest loader and simulator with returns, win rate, drawdown, and expectancy.
- Week 4 exit decisions for stop loss, targets, trailing stops, and square-off time.
- API-backed Dashboard, ticker, portfolio sessions, Reports, Alerts, and ML Models pages.
- Honest animated closed-market states; no fabricated market prices or trades.

### Validation

```powershell
docker compose -f docker-compose.dev.yml build frontend backend ml-engine
docker compose -f docker-compose.dev.yml exec -T backend python -m compileall -q /app/app
docker compose -f docker-compose.dev.yml ps
```

Synthetic Week 2, Week 3, and Week 4 checks are run inside the relevant containers. Live Angel One quotes, intraday candles, and order execution require NSE market hours and credentials; keep `TRADING_MODE=paper` during testing.

### Historical/off-hours behavior

The Dashboard reads stored trades and exposes `/api/portfolio/sessions` for previous completed sessions. A new account with no trades receives an onboarding state. Full intraday equity history still requires a future portfolio-snapshot table and scheduled collector.

### Next continuation

1. Pull the latest branch and run the Compose commands above.
2. Test Dashboard, Markets, Trade History, AI Engine, Screener, Settings, Users, ML Models, Reports, and Alerts.
3. Add the backtest HTTP endpoint and report UI.
4. Add portfolio snapshots and model-metrics persistence.
5. When NSE opens, configure Angel One if desired and verify live quotes, candles, paper orders, and exits.

Latest checkpoints:

- `7a7f250` - Week 3 backtesting and live Dashboard states
- `23ccaa1` - Historical portfolio sessions
