from datetime import datetime, timedelta, timezone

from app.services.market_data import quote_is_fresh
from app.services.market_data.base import Quote
from app.services.market_data.yfinance_provider import YFinanceProvider
from app.routers.market import _demo_screener_results


def test_quote_freshness_accepts_recent_data():
    quote = Quote(
        symbol="RELIANCE",
        ltp=2500.0,
        open=2490.0,
        high=2510.0,
        low=2488.0,
        close=2500.0,
        volume=1000,
        change_pct=1.5,
        timestamp=datetime.now(timezone.utc),
    )

    assert quote_is_fresh(quote, max_age_seconds=30) is True


def test_quote_freshness_rejects_stale_data():
    quote = Quote(
        symbol="TCS",
        ltp=3400.0,
        open=3390.0,
        high=3415.0,
        low=3385.0,
        close=3400.0,
        volume=900,
        change_pct=-0.2,
        timestamp=datetime.now(timezone.utc) - timedelta(seconds=90),
    )

    assert quote_is_fresh(quote, max_age_seconds=30) is False


def test_yfinance_provider_uses_demo_fallback_when_live_data_is_empty(monkeypatch):
    class EmptyHistory:
        empty = True

    class FakeTicker:
        def __init__(self, symbol):
            self.symbol = symbol

        def history(self, *args, **kwargs):
            return EmptyHistory()

    class FakeYFinance:
        @staticmethod
        def Ticker(symbol):
            return FakeTicker(symbol)

    monkeypatch.setitem(__import__('sys').modules, 'yfinance', FakeYFinance())

    quote = YFinanceProvider._fetch_quote('RELIANCE')

    assert quote.ltp > 0
    assert quote.symbol == 'RELIANCE'
    assert quote.volume >= 0
    assert quote.source == 'demo'


def test_yfinance_provider_uses_demo_candles_when_history_is_empty(monkeypatch):
    class EmptyHistory:
        empty = True

    class FakeTicker:
        def history(self, *args, **kwargs):
            return EmptyHistory()

    class FakeYFinance:
        @staticmethod
        def Ticker(symbol):
            return FakeTicker()

    monkeypatch.setitem(__import__('sys').modules, 'yfinance', FakeYFinance())

    candles = YFinanceProvider._fetch_ohlcv('RELIANCE', '1d', '5m')

    assert len(candles) == 60
    assert candles[-1].close > 0


def test_demo_screener_results_are_explicitly_non_live():
    results = _demo_screener_results()

    assert results
    assert all(item['data_source'] == 'demo_fallback' for item in results)
    assert all(item['ltp'] > 0 for item in results)


def test_angelone_uses_public_instrument_master_for_symbol_lookup():
    from app.services.market_data.angelone import AngelOneMarketData

    assert AngelOneMarketData._instrument_master_url().endswith("OpenAPIScripMaster.json")
    assert AngelOneMarketData._angel_interval("5m") == "FIVE_MINUTE"
    assert AngelOneMarketData._angel_tradingsymbol("RELIANCE") == "RELIANCE-EQ"


def test_angelone_parses_legacy_fetched_quote_shape():
    payload = {"data": {"fetched": [{"ltp": "2500.5"}]}}
    fetched = payload["data"]["fetched"][0]
    assert float(fetched["ltp"]) == 2500.5


def test_market_data_singleton_creation_is_guarded():
    import app.services.market_data as market_data

    assert hasattr(market_data, "_market_data_lock")
    assert market_data._market_data_lock is not None


def test_angelone_uses_smartapi_candle_datetime_bounds():
    from app.services.market_data.angelone import AngelOneMarketData

    provider = AngelOneMarketData()
    assert provider._calculate_from_date("1d").endswith(" 09:15")


def test_angelone_normalizes_instrument_lookup_symbols():
    from app.services.market_data.angelone import AngelOneMarketData

    provider = AngelOneMarketData()
    provider.instrument_tokens["RELIANCE"] = "2885"

    import asyncio

    assert asyncio.run(provider._get_instrument_token("reliance-eq")) == "2885"
