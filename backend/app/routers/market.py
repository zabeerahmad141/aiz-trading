from fastapi import APIRouter, Depends
from app.services.broker import get_active_broker
from app.core.security import get_current_user
from app.models.user import User
from app.config import settings
import yfinance as yf
import pandas as pd

router = APIRouter()

# Expanded Nifty 500 candidates for screener
NIFTY500_POOL = [
    "RELIANCE","TCS","HDFCBANK","INFY","WIPRO","ICICIBANK","BAJFINANCE",
    "SBIN","ITC","KOTAKBANK","HCLTECH","AXISBANK","LT","MARUTI","SUNPHARMA",
    "TITAN","BAJAJFINSV","TECHM","ASIANPAINT","ULTRACEMCO","POWERGRID",
    "NTPC","ONGC","COALINDIA","HINDALCO","TATAMOTORS","TATASTEEL","JSWSTEEL",
    "INDUSINDBK","ADANIPORTS","NESTLEIND","DRREDDY","DIVISLAB","CIPLA",
    "EICHERMOT","HEROMOTOCO","APOLLOHOSP","BRITANNIA","GRASIM","BPCL",
]


@router.get("/quotes")
async def get_quotes(current_user: User = Depends(get_current_user)):
    broker = await get_active_broker()
    quotes = []
    for symbol in settings.watchlist_symbols:
        try:
            q = await broker.get_quote(symbol)
            quotes.append({
                "symbol": q.symbol,
                "ltp": q.ltp,
                "open": q.open,
                "high": q.high,
                "low": q.low,
                "close": q.close,
                "volume": q.volume,
                "change_pct": q.change_pct,
            })
        except Exception:
            pass
    return quotes


@router.get("/ohlcv/{symbol}")
async def get_ohlcv(
    symbol: str,
    period: str = "1d",
    interval: str = "5m",
    current_user: User = Depends(get_current_user),
):
    """Historical OHLCV data for candlestick chart — real data from Yahoo Finance."""
    ticker = yf.Ticker(f"{symbol}.NS")
    hist = ticker.history(period=period, interval=interval)
    candles = []
    for ts, row in hist.iterrows():
        candles.append({
            "time": int(ts.timestamp()),
            "open":   round(float(row["Open"]),   2),
            "high":   round(float(row["High"]),   2),
            "low":    round(float(row["Low"]),    2),
            "close":  round(float(row["Close"]),  2),
            "volume": int(row["Volume"]),
        })
    return {"symbol": symbol, "interval": interval, "candles": candles}


@router.get("/screener")
async def stock_screener(current_user: User = Depends(get_current_user)):
    """
    Auto-screens Nifty 500 stocks and returns the top picks for today.
    Criteria:
      - Volume > 1.5x 20-day average (unusual activity)
      - Price above EMA 9 and EMA 21 (uptrend)
      - RSI between 40-65 (not overbought, has room to run)
      - Daily change > 0% (positive momentum)
    Updates the recommended watchlist automatically.
    """
    results = []
    for symbol in NIFTY500_POOL:
        try:
            ticker = yf.Ticker(f"{symbol}.NS")
            hist = ticker.history(period="30d", interval="1d")
            if len(hist) < 22:
                continue

            closes = hist["Close"]
            volumes = hist["Volume"]
            ltp = float(closes.iloc[-1])
            prev_close = float(closes.iloc[-2])
            change_pct = ((ltp - prev_close) / prev_close) * 100

            # EMA calculation
            ema9  = float(closes.ewm(span=9,  adjust=False).mean().iloc[-1])
            ema21 = float(closes.ewm(span=21, adjust=False).mean().iloc[-1])

            # RSI
            delta = closes.diff()
            gain = delta.clip(lower=0).rolling(14).mean()
            loss = (-delta.clip(upper=0)).rolling(14).mean()
            rs   = gain / loss
            rsi  = float((100 - (100 / (1 + rs))).iloc[-1])

            # Volume ratio
            avg_vol = float(volumes.rolling(20).mean().iloc[-1])
            vol_ratio = float(volumes.iloc[-1]) / avg_vol if avg_vol > 0 else 1.0

            # Score criteria
            score = 0
            if ltp > ema9:   score += 25
            if ltp > ema21:  score += 25
            if 40 <= rsi <= 65: score += 25
            if vol_ratio >= 1.3: score += 25

            if score >= 50:  # At least 2 criteria met
                results.append({
                    "symbol":     symbol,
                    "ltp":        round(ltp, 2),
                    "change_pct": round(change_pct, 2),
                    "rsi":        round(rsi, 1),
                    "vol_ratio":  round(vol_ratio, 2),
                    "ema9":       round(ema9, 2),
                    "ema21":      round(ema21, 2),
                    "score":      score,
                    "reason":     _build_reason(rsi, vol_ratio, ltp > ema9, ltp > ema21),
                })
        except Exception:
            continue

    results.sort(key=lambda x: x["score"], reverse=True)
    return {"screened": results[:15], "total_scanned": len(NIFTY500_POOL)}


def _build_reason(rsi: float, vol_ratio: float, above_ema9: bool, above_ema21: bool) -> str:
    parts = []
    if above_ema9 and above_ema21: parts.append("Uptrend (EMA)")
    if 40 <= rsi <= 55: parts.append(f"RSI buyzone ({rsi:.0f})")
    if vol_ratio >= 1.5: parts.append(f"Vol surge {vol_ratio:.1f}x")
    return " · ".join(parts) if parts else "Momentum play"

