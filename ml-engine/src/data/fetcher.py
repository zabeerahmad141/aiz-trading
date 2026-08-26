"""
AI Z — ML Engine Data Fetcher
Fetches historical OHLCV data from yfinance (free, no API key needed).
Used for model training and live prediction.
"""
import pandas as pd
import yfinance as yf
from loguru import logger
from datetime import datetime, timedelta
import os


LOOKBACK_YEARS = int(os.getenv("TRAINING_LOOKBACK_YEARS", "3"))


def fetch_historical(symbol: str, years: int = LOOKBACK_YEARS) -> pd.DataFrame:
    """
    Downloads historical daily OHLCV data from Yahoo Finance.
    NSE symbols are suffixed with .NS automatically.
    """
    ticker = f"{symbol}.NS"
    end = datetime.today()
    start = end - timedelta(days=years * 365)

    logger.info(f"Fetching {years}Y historical data for {ticker}...")
    df = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)

    if df.empty:
        raise ValueError(f"No data returned for {symbol}")

    df = df.rename(columns=str.lower)
    df.index = pd.to_datetime(df.index)
    df = df.dropna()
    logger.info(f"Fetched {len(df)} rows for {symbol}")
    return df


def fetch_intraday(symbol: str, interval: str = "5m") -> pd.DataFrame:
    """
    Fetches intraday data for live feature computation.
    interval: 1m, 5m, 15m, 30m, 60m
    """
    ticker = yf.Ticker(f"{symbol}.NS")
    df = ticker.history(period="1d", interval=interval)
    df = df.rename(columns=str.lower)
    df = df.dropna()
    return df


def fetch_multiple(symbols: list[str], years: int = LOOKBACK_YEARS) -> dict[str, pd.DataFrame]:
    result = {}
    for symbol in symbols:
        try:
            result[symbol] = fetch_historical(symbol, years)
        except Exception as e:
            logger.warning(f"Skipping {symbol}: {e}")
    return result
