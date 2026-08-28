from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # =========================================================
    # App
    # =========================================================
    app_name: str = "AI Z Trading Engine"
    app_env: str = "production"
    secret_key: str
    allowed_origins: str = "http://localhost:3000"

    # =========================================================
    # Internal service authentication
    #
    # Used by ML Engine -> Backend communication.
    # =========================================================
    internal_api_key: str = ""

    # User ID used for automated AI trades.
    #
    # We will verify this user exists before allowing
    # automated trading.
    ai_trading_user_id: int = 1

    # =========================================================
    # Database
    # =========================================================
    postgres_host: str = "postgresql"
    postgres_port: int = 5432
    postgres_db: str = "aiz_trading"
    postgres_user: str = "aiz_user"
    postgres_password: str

    # =========================================================
    # Redis
    # =========================================================
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_password: str = ""

    # =========================================================
    # Broker
    # =========================================================
    active_broker: str = "paper"
    trading_mode: str = "paper"

    # =========================================================
    # Market Data Provider
    # =========================================================
    # Options: "angelone" (FREE NSE real data), "yfinance" (FREE but rate-limited)
    # Default is yfinance until Angel One credentials are configured.
    data_provider: str = "yfinance"

    # =========================================================
    # AngelOne
    # =========================================================
    angel_api_key: str = ""
    angel_client_id: str = ""
    angel_password: str = ""
    angel_totp_secret: str = ""

    # =========================================================
    # Zerodha
    # =========================================================
    zerodha_api_key: str = ""
    zerodha_api_secret: str = ""
    zerodha_access_token: str = ""

    # =========================================================
    # Trading parameters
    # =========================================================
    trading_capital: float = 100000.0

    max_positions: int = 5

    max_risk_per_trade: float = 2.0

    stop_loss_pct: float = 1.5

    target_pct: float = 3.0

    trailing_stop: bool = True

    market_open: str = "09:15"

    market_close: str = "15:30"

    watchlist: str = (
        "RELIANCE,TCS,HDFCBANK,INFY,"
        "WIPRO,ICICIBANK,BAJFINANCE,"
        "SBIN,ITC,KOTAKBANK"
    )

    # =========================================================
    # Strategy Engine Parameters
    # =========================================================
    
    # ATR Configuration
    atr_period: int = 14  # ATR lookback period in bars
    atr_stop_multiplier: float = 1.5  # SL distance = Entry - (1.5 × ATR)
    atr_target_multiplier: float = 3.0  # Target = Entry + (3.0 × ATR)
    
    # Position Sizing
    risk_percent_per_trade: float = 2.0  # Risk % of capital per trade
    min_position_size: int = 1  # Minimum shares to trade
    max_position_size: int = 1000  # Maximum shares per trade
    
    # Entry Validation
    min_risk_reward_ratio: float = 1.5  # Minimum R:R to take trade
    rsi_oversold: float = 30.0  # RSI below this = oversold
    rsi_overbought: float = 70.0  # RSI above this = overbought
    rsi_entry_range: tuple = (40.0, 60.0)  # RSI range for confirmation
    
    # Trend Detection
    trend_ema_fast: int = 9  # Fast EMA for trend
    trend_ema_slow: int = 21  # Slow EMA for trend
    trend_ma_long: int = 50  # Long-term trend filter
    
    # Volume Confirmation
    min_volume_ratio: float = 1.5  # Volume > 1.5x average = confirmation
    volume_lookback: int = 20  # Days for volume average
    
    # Market Regime Detection
    volatility_period: int = 20  # ATR period for volatility
    min_volatility_pct: float = 0.5  # Min volatility to trade (% of price)
    max_volatility_pct: float = 5.0  # Max volatility to trade
    
    # Risk Management
    daily_loss_limit: float = 5000.0  # Stop trading if lost this much today
    weekly_loss_limit: float = 10000.0  # Stop trading if lost this much week
    max_consecutive_losses: int = 3  # Stop trading after N consecutive losses
    
    # Trade Timing
    earliest_entry_time: str = "09:20"  # Earliest time to enter trade
    latest_entry_time: str = "15:00"  # Latest time to enter trade
    exit_before_close: bool = True  # Exit all positions before market close
    
    # Backtesting
    backtest_start_date: str = "2023-01-01"  # Historical data start
    backtest_end_date: str = "2024-01-01"  # Historical data end
    backtest_commission: float = 0.001  # 0.1% commission per trade

    # =========================================================
    # ML
    # =========================================================
    ml_model: str = "xgboost"

    min_confidence: float = 65.0

    # =========================================================
    # MLflow
    # =========================================================
    mlflow_tracking_uri: str = (
        "http://mlflow:5000"
    )

    # =========================================================
    # JWT
    # =========================================================
    jwt_secret: str

    jwt_algorithm: str = "HS256"

    access_token_expire_minutes: int = 60

    refresh_token_expire_days: int = 7

    # =========================================================
    # Admin
    # =========================================================
    admin_username: str = "admin"

    admin_password: str

    admin_email: str = (
        "admin@aiz-trade.local"
    )

    # =========================================================
    # Notifications
    # =========================================================
    telegram_bot_token: str = ""

    telegram_chat_id: str = ""

    # =========================================================
    # Monitoring
    # =========================================================
    grafana_admin_password: str = "admin"

    # =========================================================
    # Database URL
    # =========================================================
    @property
    def database_url(self) -> str:
        return (
            "postgresql+asyncpg://"
            f"{self.postgres_user}:"
            f"{self.postgres_password}"
            f"@{self.postgres_host}:"
            f"{self.postgres_port}/"
            f"{self.postgres_db}"
        )

    # =========================================================
    # Redis URL
    # =========================================================
    @property
    def redis_url(self) -> str:

        if self.redis_password:

            return (
                "redis://:"
                f"{self.redis_password}"
                "@"
                f"{self.redis_host}:"
                f"{self.redis_port}/0"
            )

        return f"redis://{self.redis_host}:{self.redis_port}/0"

    # =========================================================
    # Parsed Watchlist
    # =========================================================
    @property
    def watchlist_symbols(self) -> list[str]:
        """Parse comma-separated watchlist into list of symbols."""
        return [s.strip() for s in self.watchlist.split(",") if s.strip()]

    # =========================================================
    # CORS
    # =========================================================
    @property
    def cors_origins(self) -> list[str]:

        return [
            o.strip()
            for o in self.allowed_origins.split(",")
            if o.strip()
        ]

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
