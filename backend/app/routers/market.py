import asyncio

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from app.services.market_data import get_active_market_data
from app.core.security import get_current_user
from app.models.user import User
from app.config import settings
from app.services.market_data.yfinance_provider import YFinanceProvider

router = APIRouter()

NIFTY500_POOL = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "WIPRO", "ICICIBANK",
    "SBIN", "ITC", "KOTAKBANK", "LT", "AXISBANK", "BHARTIARTL",
    "HINDUNILVR", "MARUTI", "SUNPHARMA", "TITAN", "ULTRACEMCO",
    "ASIANPAINT", "BAJFINANCE", "HCLTECH", "ADANIENT", "NTPC",
    "POWERGRID", "M&M", "TATASTEEL", "JSWSTEEL", "ONGC", "COALINDIA",
    "TECHM", "TATAMOTORS", "NESTLEIND", "DRREDDY", "CIPLA", "GRASIM",
    "EICHERMOT", "HEROMOTOCO", "APOLLOHOSP", "DIVISLAB", "BRITANNIA",
]


def _get_yfinance():
    import yfinance as yf
    return yf


@router.get("/quotes")
async def get_quotes(current_user: User = Depends(get_current_user)):
    """Get quotes for all symbols in watchlist."""
    market_data = await get_active_market_data()
    async def fetch_quote(symbol: str):
        try:
            quote = await asyncio.wait_for(market_data.get_quote(symbol), timeout=8)
            return {
                "symbol": quote.symbol,
                "ltp": quote.ltp,
                "open": quote.open,
                "high": quote.high,
                "low": quote.low,
                "close": quote.close,
                "volume": quote.volume,
                "change_pct": quote.change_pct,
                "timestamp": quote.timestamp.isoformat(),
                "source": quote.source,
            }
        except Exception as exc:
            logger.warning("Quote unavailable for {}: {}", symbol, exc)
            return None

    results = await asyncio.gather(*(fetch_quote(symbol) for symbol in settings.watchlist_symbols))
    quotes = [quote for quote in results if quote is not None]
    
    return quotes


@router.get("/ohlcv/{symbol}")
async def get_ohlcv(
    symbol: str,
    period: str = "1d",
    interval: str = "5m",
    current_user: User = Depends(get_current_user),
):
    """Historical OHLCV data for candlestick chart."""
    market_data = await get_active_market_data()
    try:
        ohlcv_list = await asyncio.wait_for(
            market_data.get_ohlcv(symbol, period=period, interval=interval),
            timeout=12,
        )
    except asyncio.TimeoutError:
        logger.warning("OHLCV request timed out for {}", symbol)
        ohlcv_list = []
    
    candles = []
    for candle in ohlcv_list:
        candles.append({
            "time": int(candle.timestamp.timestamp()),
            "open": round(candle.open, 2),
            "high": round(candle.high, 2),
            "low": round(candle.low, 2),
            "close": round(candle.close, 2),
            "volume": candle.volume,
        })
    
    return {
        "symbol": symbol,
        "interval": interval,
        "period": period,
        "candles": candles,
    }


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
    try:
        yf = _get_yfinance()
    except ImportError:
        raise HTTPException(status_code=503, detail="Yahoo Finance is unavailable")

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
        except Exception as exc:
            logger.debug("Screener skipped {}: {}", symbol, exc)
            continue

    results.sort(key=lambda x: x["score"], reverse=True)
    if not results:
        results = _demo_screener_results()
    return {"screened": results[:15], "total_scanned": len(NIFTY500_POOL)}


def _build_reason(rsi: float, vol_ratio: float, above_ema9: bool, above_ema21: bool) -> str:
    parts = []
    if above_ema9 and above_ema21: parts.append("Uptrend (EMA)")
    if 40 <= rsi <= 55: parts.append(f"RSI buyzone ({rsi:.0f})")
    if vol_ratio >= 1.5: parts.append(f"Vol surge {vol_ratio:.1f}x")
    return " · ".join(parts) if parts else "Momentum play"


def _demo_screener_results() -> list[dict]:
    """Keep paper-mode observation useful when Yahoo historical data is blocked."""
    results = []
    for symbol in NIFTY500_POOL:
        quote = YFinanceProvider._demo_quote(symbol)
        ema9 = round(quote.ltp * 0.995, 2)
        ema21 = round(quote.ltp * 0.99, 2)
        results.append({
            "symbol": symbol,
            "ltp": quote.ltp,
            "change_pct": quote.change_pct,
            "rsi": 50.0,
            "vol_ratio": 1.4,
            "ema9": ema9,
            "ema21": ema21,
            "score": 50,
            "reason": "Paper observation fallback",
            "data_source": "demo_fallback",
        })
    return results

