from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    app_name: str = "AI Z Trading Engine"
    app_env: str = "production"
    secret_key: str
    allowed_origins: str = "http://localhost:3000"

    # Database
    postgres_host: str = "postgresql"
    postgres_port: int = 5432
    postgres_db: str = "aiz_trading"
    postgres_user: str = "aiz_user"
    postgres_password: str

    # Redis
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_password: str = ""

    # Broker
    active_broker: str = "paper"
    trading_mode: str = "paper"

    # AngelOne
    angel_api_key: str = ""
    angel_client_id: str = ""
    angel_password: str = ""
    angel_totp_secret: str = ""

    # Zerodha
    zerodha_api_key: str = ""
    zerodha_api_secret: str = ""
    zerodha_access_token: str = ""

    # Trading params
    trading_capital: float = 100000.0
    max_positions: int = 5
    max_risk_per_trade: float = 2.0
    stop_loss_pct: float = 1.5
    target_pct: float = 3.0
    trailing_stop: bool = True
    market_open: str = "09:15"
    market_close: str = "15:30"
    watchlist: str = "RELIANCE,TCS,HDFCBANK,INFY,WIPRO,ICICIBANK,BAJFINANCE,SBIN,ITC,KOTAKBANK"

    # ML
    ml_model: str = "xgboost"
    min_confidence: float = 65.0

    # MLflow
    mlflow_tracking_uri: str = "http://mlflow:5000"

    # JWT
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    # Admin (first boot)
    admin_username: str = "admin"
    admin_password: str
    admin_email: str = "admin@aiz-trade.local"

    # Notifications
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # Monitoring
    grafana_admin_password: str = "admin"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/0"
        return f"redis://{self.redis_host}:{self.redis_port}/0"

    @property
    def watchlist_symbols(self) -> list[str]:
        return [s.strip() for s in self.watchlist.split(",") if s.strip()]

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
