# AI Z Trading Platform - Future Live Development Plan

## Purpose

This document is the authoritative development handoff for AI Z. Every future implementation must support the eventual live-market architecture. Local paper trading is a validation mode, not the product destination.

No future task may enable real-money execution, weaken a risk gate, or treat synthetic data as market evidence without an explicit review.

## Current Decision

Current stage: **paper trading and market-observation readiness**.

Safe runtime configuration:

```env
ACTIVE_BROKER=paper
TRADING_MODE=paper
LIVE_TRADING_ENABLED=false
PAPER_AUTO_TRADING_ENABLED=true
```

The application is not certified for real-money execution.

## Completed Foundation

- Docker Compose stack for backend, frontend, ML engine, PostgreSQL, and Redis.
- FastAPI backend with JWT authentication and protected routes.
- React/Vite dashboard with markets, portfolio, reports, settings, and trade views.
- Broker abstraction with PaperBroker and Angel One adapter structure.
- Explicit live execution gate requiring live mode, non-paper broker, and explicit enablement.
- Internal ML-to-backend authentication using `INTERNAL_API_KEY`.
- Quote freshness validation before paper execution.
- Paper order, position, trade history, P&L, and persistent paper state.
- ATR-based position sizing, stop loss, and target calculations.
- Ten-candle signal confirmation: 10 candles inspected, at least 6 confirmations required, ATR values must be valid.
- Watchlist-wide signal evaluation and confidence ranking.
- Automatic paper-trading opt-in with `PAPER_AUTO_TRADING_ENABLED`.
- Market-session status, previous/next session commentary, and off-hours display behavior.
- Interactive chart views: Candles, Line, and Area, with EMA and volume in the detailed Candles view.
- Quote/candle retention in the frontend for off-hours review.
- Local historical dataset storage with CSV validation and JSON manifests.
- Angel One reconnect foundation: serialized login, non-blocking calls, bounded retry, and session invalidation.
- Secret validation and redacted startup configuration logging.
- Docker smoke test and focused regression suite.

## Development-Only Components

These are allowed only for UI, infrastructure, and deterministic engineering tests:

- Synthetic quote fallback values.
- Synthetic OHLCV candles.
- Synthetic screener candidates.
- `create_demo_dataset.py` fixtures.
- Controlled paper BUY/SELL lifecycle tests.

Every synthetic response must remain visibly marked as demo/fallback and must never be used as evidence of profitability or real-market strategy quality. Replace or bypass synthetic data for any strategy-performance decision.

## Required Development Phases

### Phase 1 - Reliable data foundation

1. Add Angel One credentials only to local secret storage.
2. Keep `DATA_PROVIDER=angelone` separate from broker execution.
3. Verify real quote timestamp, LTP, OHLC, volume, and instrument token.
4. Verify reconnect after session expiry, API timeout, malformed response, and provider outage.
5. Do not silently mix live, Yahoo, and synthetic data. Return and display a source label.
6. Download real historical datasets while available and store them locally with manifests.
7. Validate dataset symbol, timezone, interval, gaps, duplicates, OHLC ranges, and missing volume.

Exit gate: real and historical data source is known for every analysis result; fallback data is never mistaken for real data.

### Phase 2 - Backtesting and research

1. Use chronological train/validation/test splits.
2. Prevent look-ahead leakage.
3. Include brokerage, taxes, slippage, spread, and realistic execution assumptions.
4. Compare against buy-and-hold and simple baselines.
5. Report return, drawdown, Sharpe, expectancy, win rate, loss streak, exposure, turnover, and trade duration.
6. Test bull, bear, sideways, high-volatility, low-volatility, gap, and missing-data periods.
7. Keep an untouched out-of-sample dataset.
8. Record model version, feature version, dataset manifest, and configuration with every result.

Exit gate: strategy results are reproducible and remain acceptable on unseen data after costs.

### Phase 3 - Strategy and risk controls

1. Keep the full-symbol scan and confidence ranking.
2. Require multi-candle confirmation and valid ATR.
3. Reject stale, missing, zero, or inconsistent quotes.
4. Enforce maximum positions, maximum allocation, daily loss limit, weekly loss limit, and consecutive-loss circuit breaker.
5. Add maximum holding period and overnight-gap handling for positional mode.
6. Decide explicitly whether the production strategy is intraday or positional. Broker product must match that decision.
7. Implement stop-loss, target, trailing stop, and pre-close rules as durable state transitions.
8. Never assume an AI confidence score guarantees profit.

Exit gate: every order has an explainable signal, risk decision, quote timestamp, strategy version, and rejection reason when not executed.

### Phase 4 - Durable execution and reconciliation

1. Persist order intents before broker submission.
2. Add idempotency keys to prevent duplicate orders after retries.
3. Persist broker order IDs, statuses, timestamps, fills, average price, fees, and rejection reasons.
4. Reconcile database positions with broker positions after startup and on a schedule.
5. Handle partial fills, rejected orders, cancelled orders, unknown status, network timeout, and restart recovery.
6. Make position and P&L calculations derive from durable trade records.
7. Add an operator repair workflow for mismatches.
8. Keep PaperBroker behavior compatible with the same lifecycle contract.

Exit gate: a restart or network failure cannot create a duplicate position or lose an order state.

### Phase 5 - Automated monitoring and exits

1. Run quote refresh only during configured market sessions, with bounded timeouts.
2. Persist the latest quote and its age.
3. Evaluate exits on every fresh quote for open positions.
4. Enforce no new entry after the configured latest-entry time.
5. Enforce pre-close exit only if the chosen strategy is intraday.
6. Handle market holidays, weekends, exchange pauses, and timezone conversion in IST.
7. Alert on stale data, provider disconnect, rejected exit, reconciliation mismatch, and risk circuit-breaker activation.
8. Ensure the dashboard remains useful after close with last-known data and session summaries.

Exit gate: open positions and failed exits are visible and actionable at all times.

### Phase 6 - Real-data paper observation

1. Use real Angel One market data with PaperBroker.
2. Run for multiple weeks and different market regimes.
3. Compare signals with subsequent price movement without changing thresholds mid-test.
4. Track paper returns after realistic costs and slippage.
5. Review every automatic trade and rejection.
6. Test provider reconnect, backend restart, ML restart, and database recovery.
7. Keep live execution disabled throughout.

Exit gate: stable operation, accurate records, acceptable risk, and no unresolved data or reconciliation defects.

### Phase 7 - Broker sandbox or controlled canary

Only begin after Phases 1-6 pass.

1. Confirm whether Angel One provides a sandbox; do not assume an empty account is a sandbox.
2. Use a dedicated broker API application and minimum permissions available.
3. Start with read-only verification where possible.
4. Test instrument lookup, quote retrieval, order intent, rejection, cancellation, and status polling.
5. Use the smallest permitted position and strict daily kill switch.
6. Require manual approval for every canary order.
7. Immediately disable live mode after the test window.

Exit gate: broker lifecycle and recovery behavior are proven with audit records.

### Phase 8 - Live-money review

This is an approval stage, not an automatic deployment step.

Required before any live enablement:

- Real-data validation complete.
- Backtest and out-of-sample reports reviewed.
- Paper observation completed over multiple weeks.
- Reconciliation and idempotency tested.
- Exit management tested.
- Kill switch tested.
- Secrets rotated and stored securely.
- Logs contain no credentials or tokens.
- Broker product matches intraday or positional strategy.
- Manual approval and rollback procedure documented.
- Trading capital and daily loss budget explicitly approved by the owner.

No agent should change `TRADING_MODE=live` or `LIVE_TRADING_ENABLED=true` without explicit user approval in the same task.

## Strategy Specification To Preserve

Current intended strategy:

1. Scan the configured universe.
2. Fetch sufficient OHLCV history.
3. Engineer EMA, RSI, MACD, Bollinger, volume, and ATR features.
4. Predict the latest direction with the ML model.
5. Check the last 10 feature candles.
6. Require at least 6 matching directional confirmations.
7. Require valid positive ATR across the confirmation window.
8. Require minimum confidence of 65%.
9. Apply position, capital, duplicate, loss-limit, and quote-freshness checks.
10. Rank approved signals: exits first, then highest confidence entries.
11. Execute only through the configured broker abstraction.
12. Record the decision, data source, quote age, model version, ATR, stop, target, and outcome.

This process improves discipline but cannot guarantee profitable trades.

## Test Matrix

### Automated tests

- Configuration defaults and live-mode gate.
- Secret validation and missing-secret behavior.
- Quote freshness and timezone handling.
- Angel One login success, failed login, timeout, reconnect, and bounded retry.
- Instrument-token lookup and malformed broker responses.
- Quote and OHLCV schema validation.
- ATR calculation and invalid ATR rejection.
- Ten-candle confirmation pass/fail.
- Confidence threshold pass/fail.
- Position sizing and maximum allocation.
- Duplicate position and maximum-position rejection.
- Daily/weekly/consecutive loss circuit breakers.
- Paper BUY, SELL, persistence, restart, and P&L.
- Idempotent order intent and reconciliation.
- Stop-loss, target, trailing stop, and pre-close exit.
- Backtest costs, drawdown, and end-of-data close.
- API authentication and authorization.

### Runtime tests

```bash
docker compose -f docker-compose.dev.yml up -d --build

docker compose -f docker-compose.dev.yml ps

docker compose -f docker-compose.dev.yml exec -T backend python -m compileall -q /app/app
docker compose -f docker-compose.dev.yml exec -T ml-engine python -m compileall -q /app/src

docker compose -f docker-compose.dev.yml exec -T -w /app -e PYTHONPATH=/app backend pytest -q

powershell -ExecutionPolicy Bypass -File .\scripts\offline-smoke.ps1
```

For Git Bash, use `MSYS_NO_PATHCONV=1` for commands containing container paths.

### Manual acceptance tests

- Login and logout.
- Dashboard and Markets data source labels.
- Chart symbol, interval, Candles, Line, and Area views.
- Current, previous, and next market-session commentary.
- Paper automatic signal/rejection history.
- Paper BUY, position, portfolio, matching SELL, and P&L.
- Restart services and confirm records remain.
- Stop provider or network and verify reconnect/unavailable behavior.
- Review logs for secrets and unexpected live broker calls.

## Security Rules

- Never paste broker credentials into chat.
- Never commit `.env` or secrets.
- Rotate any credential exposed in logs, screenshots, Git, or conversation history.
- Use separate API applications for development and live operation when supported.
- Keep `ACTIVE_BROKER=paper` and `TRADING_MODE=paper` during development.
- Never use an empty broker account as a safety control.
- Do not log passwords, TOTP secrets, JWTs, API keys, or full broker responses.
- Use least privilege, local file permissions, encrypted backups, and key rotation.
- Treat fallback data as non-trading data.
- Require explicit human approval before any live-mode change.

## Agent Operating Contract

For every future task, the agent must:

1. State whether the change supports live architecture, paper validation, or development-only simulation.
2. Prefer the live-compatible abstraction and shared data contracts.
3. Avoid local-only shortcuts unless clearly labeled and isolated.
4. Add focused tests for every behavior change.
5. Run the narrowest executable validation immediately after editing.
6. Never enable live execution implicitly.
7. Report blockers and unverified broker behavior honestly.
8. Keep this document updated when a phase or gate changes.

## Current Next Actions

1. Create an Angel One account and SmartAPI application through official channels.
2. Rotate the previously exposed internal API key.
3. Add Angel One credentials only to local `.env` when ready.
4. Set `DATA_PROVIDER=angelone` while keeping the broker in paper mode.
5. Verify real quotes and candles with source labels.
6. Build real historical dataset archives and manifests.
7. Implement durable order reconciliation and idempotency.
8. Integrate automated exits and maximum holding-period behavior.
9. Expand API and broker mock tests.
10. Run multi-week real-data paper observation before any live review.
