# Trading Strategy Implementation Blueprint

**Based On:** AI Trading Model — Complete Strategy & Missing Requirements (51 points)  
**Status:** What needs to be built for a complete strategy  

---

## STRATEGY ENGINE ARCHITECTURE (To Be Built)

### Directory Structure
```
backend/app/services/strategy/
├── __init__.py
├── base.py                 # Abstract base classes
├── trend.py               # Trend analysis (EMA, SMA)
├── momentum.py            # Momentum (RSI, MACD, Stochastic)
├── volume.py              # Volume confirmation
├── market_regime.py       # Identify trending/range/volatile
├── support_resistance.py  # Key price levels
├── entry_validator.py     # Entry confirmation rules
├── signal_processor.py    # Convert ML output to actionable signal
└── strategy_config.py     # All configurable parameters

backend/app/services/risk/
├── __init__.py
├── atr_calculator.py      # ATR and volatility calculations
├── position_sizer.py      # Calculate quantity based on risk
├── risk_validator.py      # Validate risk/reward, capital limits
└── exit_manager.py        # Handle exits (stop/target/trailing)
```

---

## CRITICAL MISSING COMPONENTS (Prioritized)

### TIER 1: Must Have (Blocking Paper Trading)

#### 1. ATR Calculator
**File:** `backend/app/services/risk/atr_calculator.py`

**Implements:**
```python
class ATRCalculator:
    def calculate_atr(df, period=14) -> float
        # True Range = max of:
        #   High - Low
        #   |High - Prev Close|
        #   |Low - Prev Close|
        # ATR = SMA of TR
        
    def get_atr_stop(entry, atr, multiplier=1.5, side='buy')
        # Buy: entry - (atr * multiplier)
        # Sell: entry + (atr * multiplier)
        
    def get_atr_target(entry, atr, multiplier=3, side='buy')
        # Buy: entry + (atr * multiplier)
        # Sell: entry - (atr * multiplier)
        
    def get_atr_percentage(atr, price) -> float
        # (ATR / Price) * 100
        # For volatility normalization
```

**Usage:**
```python
atr_calc = ATRCalculator()
atr = atr_calc.calculate_atr(df, period=14)
stop_loss = atr_calc.get_atr_stop(entry_price, atr, multiplier=1.5)
target = atr_calc.get_atr_target(entry_price, atr, multiplier=3)
```

---

#### 2. Position Sizer
**File:** `backend/app/services/risk/position_sizer.py`

**Implements:**
```python
class PositionSizer:
    def calculate_quantity(
        capital: float,
        risk_percent: float,        # e.g., 1.0 (1%)
        entry_price: float,
        stop_loss_price: float,
        max_capital_allocation: float = 0.20  # 20% of capital
    ) -> int:
        """
        Formula:
        Risk Amount = Capital × Risk %
        Risk Per Share = Entry - Stop Loss
        Quantity = Risk Amount / Risk Per Share
        
        Also check: Quantity × Entry <= Capital × Max Allocation
        """
        risk_amount = capital * (risk_percent / 100)
        risk_per_share = abs(entry_price - stop_loss_price)
        
        if risk_per_share <= 0:
            return 0
            
        quantity_by_risk = int(risk_amount / risk_per_share)
        max_position_value = capital * (max_capital_allocation / 100)
        quantity_by_capital = int(max_position_value / entry_price)
        
        # Take the smaller of the two
        quantity = min(quantity_by_risk, quantity_by_capital)
        
        return max(quantity, 0)
```

**Usage:**
```python
sizer = PositionSizer()
qty = sizer.calculate_quantity(
    capital=100000,
    risk_percent=1.0,
    entry_price=1950,
    stop_loss_price=1905,
    max_capital_allocation=20
)  # Returns: 22 shares
```

---

#### 3. Trend Analyzer
**File:** `backend/app/services/strategy/trend.py`

**Implements:**
```python
class TrendAnalyzer:
    def get_trend(df) -> str:
        """
        Returns: STRONG_BULLISH, BULLISH, NEUTRAL, BEARISH, STRONG_BEARISH
        
        Rules:
        - Price > EMA20 > EMA50 > EMA200 → STRONG_BULLISH
        - Price > EMA20 > EMA50 → BULLISH
        - Price < EMA20 < EMA50 → BEARISH
        - Else → NEUTRAL
        """
        price = df['close'].iloc[-1]
        ema20 = df['ema20'].iloc[-1]
        ema50 = df['ema50'].iloc[-1]
        ema200 = df['ema200'].iloc[-1]
        
        if price > ema20 > ema50 > ema200:
            return "STRONG_BULLISH"
        elif price > ema20 > ema50:
            return "BULLISH"
        elif price < ema20 < ema50:
            return "BEARISH"
        else:
            return "NEUTRAL"
    
    def is_trend_aligned(trend: str, signal: str) -> bool:
        """
        BUY signals work better in uptrends
        SELL signals work better in downtrends
        HOLD signals okay in any trend
        """
        if signal == "BUY":
            return trend in ["BULLISH", "STRONG_BULLISH"]
        elif signal == "SELL":
            return trend in ["BEARISH", "STRONG_BEARISH"]
        else:
            return True
```

---

#### 4. Entry Validator
**File:** `backend/app/services/strategy/entry_validator.py`

**Implements:**
```python
class EntryValidator:
    def validate_buy_setup(df, config) -> dict:
        """
        BUY Entry Requirements:
        1. Trend: Price > EMA20 > EMA50
        2. Momentum: RSI 30-70 (not too weak, not overbought)
        3. MACD: Bullish (MACD > Signal)
        4. Volume: Current > Avg × 1.5
        5. Price Action: Higher low, higher high forming
        
        Returns: {
            valid: bool,
            score: 0-100,
            reasons: [list of checks]
        }
        """
        score = 0
        reasons = []
        
        # Check 1: Trend
        if df['close'].iloc[-1] > df['ema20'].iloc[-1] > df['ema50'].iloc[-1]:
            score += 25
            reasons.append("✓ Uptrend (price > EMA20 > EMA50)")
        else:
            reasons.append("✗ Not in uptrend")
        
        # Check 2: RSI
        rsi = df['rsi'].iloc[-1]
        if 35 <= rsi <= 65:
            score += 20
            reasons.append(f"✓ RSI {rsi} (good zone)")
        else:
            reasons.append(f"✗ RSI {rsi} (extreme)")
        
        # Check 3: MACD
        if df['macd'].iloc[-1] > df['macd_signal'].iloc[-1]:
            score += 20
            reasons.append("✓ MACD bullish")
        else:
            reasons.append("✗ MACD not bullish")
        
        # Check 4: Volume
        vol_ratio = df['volume'].iloc[-1] / df['volume'].iloc[-50:].mean()
        if vol_ratio >= 1.5:
            score += 20
            reasons.append(f"✓ Volume {vol_ratio:.1f}x average")
        else:
            reasons.append(f"✗ Volume only {vol_ratio:.1f}x")
        
        # Check 5: Price Action
        if df['close'].iloc[-1] > df['close'].iloc[-2]:
            score += 15
            reasons.append("✓ Price making higher lows")
        else:
            reasons.append("✗ Price not making higher lows")
        
        return {
            "valid": score >= 60,
            "score": score,
            "reasons": reasons
        }
    
    def validate_sell_setup(df, config) -> dict:
        """Similar logic for SELL setups"""
        pass
```

---

#### 5. Market Regime Detector
**File:** `backend/app/services/strategy/market_regime.py`

**Implements:**
```python
class MarketRegimeDetector:
    def detect_regime(df) -> str:
        """
        Returns: TRENDING_UP, TRENDING_DOWN, SIDEWAYS, VOLATILE
        
        Logic:
        - TRENDING_UP: EMA20 > EMA50, price > both, steady higher highs
        - TRENDING_DOWN: EMA20 < EMA50, price < both, steady lower lows
        - SIDEWAYS: Price oscillating between support/resistance
        - VOLATILE: ATR% > 3%, price swinging heavily
        """
        atr_pct = (df['atr'].iloc[-1] / df['close'].iloc[-1]) * 100
        
        if atr_pct > 3:
            return "VOLATILE"
        
        # Check trend direction
        if df['ema20'].iloc[-1] > df['ema50'].iloc[-1]:
            return "TRENDING_UP"
        elif df['ema20'].iloc[-1] < df['ema50'].iloc[-1]:
            return "TRENDING_DOWN"
        else:
            return "SIDEWAYS"
    
    def get_strategy_adjustment(regime: str) -> dict:
        """
        Adjust strategy based on regime
        """
        adjustments = {
            "TRENDING_UP": {
                "allow_buy": True,
                "allow_sell": False,
                "position_size_multiplier": 1.0,
                "take_profit_multiple": 3.0
            },
            "TRENDING_DOWN": {
                "allow_buy": False,
                "allow_sell": True,
                "position_size_multiplier": 0.8,
                "take_profit_multiple": 2.0
            },
            "SIDEWAYS": {
                "allow_buy": False,
                "allow_sell": False,
                "position_size_multiplier": 0.5,
                "take_profit_multiple": 1.5
            },
            "VOLATILE": {
                "allow_buy": False,
                "allow_sell": False,
                "position_size_multiplier": 0.3,
                "take_profit_multiple": 1.0
            }
        }
        return adjustments.get(regime, adjustments["SIDEWAYS"])
```

---

### TIER 2: Important (Improves Strategy Quality)

#### 6. Support/Resistance Calculator
**File:** `backend/app/services/strategy/support_resistance.py`

**Detects:**
- Swing high/low (last N candles)
- Previous day high/low
- Major support levels (recent bounce points)
- Major resistance levels (recent rejection points)

---

#### 7. Risk/Reward Validator
**File:** `backend/app/services/risk/risk_validator.py`

**Checks:**
```python
# Before ANY trade:
reward = abs(target - entry)
risk = abs(entry - stop_loss)
ratio = reward / risk

if ratio < MIN_R_R_RATIO:  # e.g., 1.5
    REJECT  # R:R too poor
```

---

#### 8. Exit Manager
**File:** `backend/app/services/risk/exit_manager.py`

**Handles:**
- Stop loss execution
- Target execution
- Trailing stops (ATR-based)
- Time-based exits
- End-of-day forced exit

---

### TIER 3: Nice-to-Have (For Later)

- Partial exit support
- Multiple stop levels
- Advanced trailing stop logic
- Market-level confirmation (NIFTY trend)
- Multi-timeframe analysis

---

## CONFIGURATION REQUIREMENTS

### New Config File: `backend/app/config.py` (Add These)

```python
# =========================================================
# Trading Strategy Configuration
# =========================================================

# Timeframe (1m, 5m, 15m, 30m, 1h, 1d)
TRADING_TIMEFRAME: str = "5m"

# ATR Period
ATR_PERIOD: int = 14

# ATR Stop Multiplier (1.5x ATR)
ATR_STOP_MULTIPLIER: float = 1.5

# ATR Target Multiplier (3x ATR)
ATR_TARGET_MULTIPLIER: float = 3.0

# Position Sizing
RISK_PERCENT_PER_TRADE: float = 1.0  # 1%
MAX_CAPITAL_ALLOCATION_PCT: float = 20.0  # 20%

# Risk Limits
MAX_DAILY_LOSS_PCT: float = 3.0  # 3%
MAX_OPEN_POSITIONS: int = 5
MIN_RISK_REWARD_RATIO: float = 1.5

# Entry Validation
TREND_ALIGNMENT_REQUIRED: bool = True
MIN_ENTRY_SCORE: int = 60  # Out of 100
VOLUME_RATIO_THRESHOLD: float = 1.5

# Exit Rules
INTRADAY_ONLY: bool = True
SQUARE_OFF_TIME: str = "15:20"  # Force close at this time
TRAILING_STOP_ENABLED: bool = True
TRAILING_STOP_MULTIPLIER: float = 2.0  # 2x ATR

# Market Conditions
ALLOW_TRADING_IN_VOLATILE: bool = False
MAX_ATR_PCT: float = 3.0

# Stock Universe
ALLOWED_SYMBOLS: list = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "WIPRO",
    "ICICIBANK", "BAJFINANCE", "SBIN", "ITC", "KOTAKBANK",
]

# Transaction Costs (for realistic P&L)
BROKERAGE_PCT: float = 0.03  # 0.03%
STT_PCT: float = 0.025  # 0.025%
SLIPPAGE_PER_TRADE: float = 2.0  # ₹2
```

---

## INTEGRATION WITH EXISTING CODE

### Current Flow (Paper Trader)
```
ML Model → Signal (BUY/SELL/HOLD)
   ↓
PaperBroker.place_order()
   ↓
Execute immediately
```

### New Flow (With Strategy)
```
ML Model → Structured Signal
   ↓
Strategy Engine
├─ Trend check ✓
├─ Entry validation ✓
├─ Market regime ✓
├─ ATR calculation ✓
└─ Output: {entry, sl, target, qty}
   ↓
Risk Engine
├─ Position sizing ✓
├─ R:R validation ✓
├─ Capital check ✓
└─ Output: Approved/Rejected
   ↓
Order Execution
├─ If approved → PaperBroker.place_order()
├─ With {qty, entry, sl, target}
└─ Track monitoring
```

---

## IMPLEMENTATION CHECKLIST

### Week 2-3: Strategy Engine Build

- [ ] ATR Calculator (4 hours)
- [ ] Position Sizer (4 hours)
- [ ] Trend Analyzer (4 hours)
- [ ] Entry Validator (6 hours)
- [ ] Market Regime Detector (4 hours)
- [ ] Support/Resistance (4 hours)
- [ ] Risk/Reward Validator (3 hours)
- [ ] Integration testing (4 hours)

**Total: ~33 hours**

### Week 4: Risk Engine Completion

- [ ] Complete Risk Validator (3 hours)
- [ ] Exit Manager (6 hours)
- [ ] Trailing stops (4 hours)
- [ ] Daily loss tracking (2 hours)
- [ ] Integration testing (3 hours)

**Total: ~18 hours**

### Week 5: Backtesting Framework

- [ ] Historical data loader (3 hours)
- [ ] Backtest engine (6 hours)
- [ ] Performance calculator (4 hours)
- [ ] Parameter optimizer (5 hours)
- [ ] Results visualizer (3 hours)

**Total: ~21 hours**

---

## SUCCESS CRITERIA

By end of strategy implementation:

✅ ALL 51 points from the model document are addressed
✅ ATR-based stops and targets working
✅ Position sizing based on risk percentage
✅ Entry validation with multi-confirmation
✅ Market regime detection functional
✅ Risk/Reward validation enforced
✅ Backtesting shows positive expectancy
✅ Paper trading produces realistic P&L
✅ All configuration parameters adjustable
✅ End-to-end paper trading workflow verified

---

## FINAL TIMELINE

```
WEEK 1: Infrastructure fixes
WEEK 2-3: Strategy Engine (33 hrs)
WEEK 4: Risk Engine (18 hrs)
WEEK 5: Backtesting (21 hrs)
WEEK 6-7: Testing & optimization
WEEK 8: Production deployment

Total: 8 weeks
Total hours: 100-120 hours
Cost: $0
Result: Production-ready, validated trading system
```

This is the proper way to build a trading system.

