"""
Feature Engineering — converts raw OHLCV into ML-ready features.

Technical Indicators computed:
  RSI (14), MACD, Bollinger Bands, EMA 9/21/50,
  ATR, Stochastic, Volume SMA, Momentum, ROC
  
These are the same indicators used by professional traders.
The AI learns which combinations predict price movements.
"""
import pandas as pd
import numpy as np
import ta


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Takes raw OHLCV dataframe, returns feature-rich dataframe.
    All NaN rows are dropped automatically.
    """
    df = df.copy()

    # ── Trend indicators ──────────────────────────────────────
    df['ema_9']  = ta.trend.ema_indicator(df['close'], window=9)
    df['ema_21'] = ta.trend.ema_indicator(df['close'], window=21)
    df['ema_50'] = ta.trend.ema_indicator(df['close'], window=50)
    df['sma_20'] = ta.trend.sma_indicator(df['close'], window=20)

    macd = ta.trend.MACD(df['close'])
    df['macd']        = macd.macd()
    df['macd_signal'] = macd.macd_signal()
    df['macd_diff']   = macd.macd_diff()

    # ── Momentum indicators ───────────────────────────────────
    df['rsi'] = ta.momentum.rsi(df['close'], window=14)

    stoch = ta.momentum.StochasticOscillator(df['high'], df['low'], df['close'])
    df['stoch_k'] = stoch.stoch()
    df['stoch_d'] = stoch.stoch_signal()

    df['roc']      = ta.momentum.roc(df['close'], window=10)
    df['momentum'] = df['close'].pct_change(10)

    # ── Volatility indicators ─────────────────────────────────
    bb = ta.volatility.BollingerBands(df['close'])
    df['bb_upper'] = bb.bollinger_hband()
    df['bb_lower'] = bb.bollinger_lband()
    df['bb_mid']   = bb.bollinger_mavg()
    df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_mid']
    df['bb_pct']   = bb.bollinger_pband()

    df['atr'] = ta.volatility.average_true_range(df['high'], df['low'], df['close'])

    # ── Volume indicators ─────────────────────────────────────
    df['volume_sma'] = ta.trend.sma_indicator(df['volume'].astype(float), window=20)
    df['volume_ratio'] = df['volume'] / df['volume_sma']
    df['obv'] = ta.volume.on_balance_volume(df['close'], df['volume'])

    # ── Price-derived features ────────────────────────────────
    df['hl_pct']     = (df['high'] - df['low']) / df['close']
    df['co_pct']     = (df['close'] - df['open']) / df['open']
    df['gap_pct']    = (df['open'] - df['close'].shift(1)) / df['close'].shift(1)
    df['ema_cross']  = (df['ema_9'] > df['ema_21']).astype(int)
    df['price_ema50_ratio'] = df['close'] / df['ema_50']

    # ── Target variable ───────────────────────────────────────
    # 1 = price went up > 0.5% in next N bars, 0 = otherwise
    df['target'] = (df['close'].shift(-1) > df['close'] * 1.005).astype(int)

    df = df.dropna()
    return df


FEATURE_COLUMNS = [
    'ema_9', 'ema_21', 'ema_50', 'sma_20',
    'macd', 'macd_signal', 'macd_diff',
    'rsi', 'stoch_k', 'stoch_d',
    'roc', 'momentum',
    'bb_upper', 'bb_lower', 'bb_width', 'bb_pct',
    'atr', 'volume_ratio', 'obv',
    'hl_pct', 'co_pct', 'gap_pct', 'ema_cross', 'price_ema50_ratio',
]
