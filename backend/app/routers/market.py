from fastapi import APIRouter, Depends
from app.services.broker import get_active_broker
from app.core.security import get_current_user
from app.models.user import User
from app.config import settings
import yfinance as yf

router = APIRouter()


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
    """Historical OHLCV data for candlestick chart."""
    ticker = yf.Ticker(f"{symbol}.NS")
    hist = ticker.history(period=period, interval=interval)

    candles = []
    for ts, row in hist.iterrows():
        candles.append({
            "time": int(ts.timestamp()),
            "open": round(float(row["Open"]), 2),
            "high": round(float(row["High"]), 2),
            "low": round(float(row["Low"]), 2),
            "close": round(float(row["Close"]), 2),
            "volume": int(row["Volume"]),
        })
    return {"symbol": symbol, "interval": interval, "candles": candles}
