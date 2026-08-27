"""
AI Z — ML Engine Data Fetcher

Fetches NSE OHLCV data directly from Yahoo Finance Chart API.
This avoids yfinance parsing/rate-limit issues in the container.

Used for:
- model training
- live prediction
- intraday feature computation
"""

import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

import pandas as pd
from loguru import logger


LOOKBACK_YEARS = int(os.getenv("TRAINING_LOOKBACK_YEARS", "3"))

YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


def _download_yahoo(
    ticker: str,
    period: str | None = None,
    interval: str = "1d",
    start: datetime | None = None,
    end: datetime | None = None,
) -> pd.DataFrame:
    """
    Download OHLCV data directly from Yahoo Finance Chart API.
    """

    params = {
        "interval": interval,
        "events": "history",
        "includeAdjustedClose": "true",
    }

    if period:
        params["range"] = period
    else:
        params["period1"] = str(int(start.timestamp()))
        params["period2"] = str(int(end.timestamp()))

    url = f"{YAHOO_CHART_URL}/{ticker}?{urllib.parse.urlencode(params)}"

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        },
    )

    logger.debug(f"Yahoo request: {ticker}, interval={interval}")

    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))

    chart = payload.get("chart", {})
    result = chart.get("result")

    if not result:
        error = chart.get("error")
        raise ValueError(f"Yahoo returned no result for {ticker}: {error}")

    data = result[0]

    timestamps = data.get("timestamp", [])
    indicators = data.get("indicators", {})
    quote_list = indicators.get("quote", [])

    if not timestamps or not quote_list:
        raise ValueError(f"No OHLCV data returned for {ticker}")

    quote = quote_list[0]

    df = pd.DataFrame(
        {
            "open": quote.get("open", []),
            "high": quote.get("high", []),
            "low": quote.get("low", []),
            "close": quote.get("close", []),
            "volume": quote.get("volume", []),
        },
        index=pd.to_datetime(timestamps, unit="s", utc=True),
    )

    # Convert to timezone-naive datetime.
    df.index = df.index.tz_convert(None)

    # Remove incomplete/invalid rows.
    df = df.dropna(subset=["open", "high", "low", "close"])

    if df.empty:
        raise ValueError(f"No valid OHLC data returned for {ticker}")

    return df


def fetch_historical(symbol: str, years: int = LOOKBACK_YEARS) -> pd.DataFrame:
    """
    Downloads historical daily OHLCV data from Yahoo Finance.

    NSE symbols are suffixed with .NS automatically.
    """

    ticker = f"{symbol}.NS"

    end = datetime.utcnow()
    start = end - timedelta(days=years * 365)

    logger.info(
        f"Fetching {years}Y historical data for {ticker}..."
    )

    df = _download_yahoo(
        ticker=ticker,
        interval="1d",
        start=start,
        end=end,
    )

    logger.info(
        f"Fetched {len(df)} rows for {symbol}"
    )

    return df


def fetch_intraday(
    symbol: str,
    interval: str = "5m",
) -> pd.DataFrame:
    """
    Fetches intraday data for live feature computation.

    Supported intervals include:
    1m, 2m, 5m, 15m, 30m, 60m
    """

    ticker = f"{symbol}.NS"

    logger.info(
        f"Fetching intraday data for {ticker}, interval={interval}..."
    )

    df = _download_yahoo(
        ticker=ticker,
        period="1d",
        interval=interval,
    )

    return df


def fetch_multiple(
    symbols: list[str],
    years: int = LOOKBACK_YEARS,
) -> dict[str, pd.DataFrame]:
    """
    Fetch historical data for multiple symbols.

    Failed symbols are skipped so one Yahoo failure
    does not stop the entire training process.
    """

    result = {}

    for symbol in symbols:
        try:
            result[symbol] = fetch_historical(symbol, years)

        except Exception as e:
            logger.warning(
                f"Skipping {symbol}: {e}"
            )

    return result
