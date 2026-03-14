"""Configuration and settings for the market agent."""

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment or .env file."""

    # API Keys
    anthropic_api_key: str = ""
    forex_api_key: str = ""

    # Paper trading
    starting_capital: float = 100_000.0

    # Watchlist defaults
    stock_watchlist: list[str] = Field(
        default=["AAPL", "MSFT", "TSLA", "GOOGL", "AMZN", "NVDA", "META", "AMD", "JPM"]
    )
    crypto_watchlist: list[str] = Field(
        default=["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "DOGE/USDT"]
    )
    forex_watchlist: list[str] = Field(
        default=["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X"]
    )
    commodity_watchlist: list[str] = Field(
        default=["GC=F", "SI=F", "CL=F", "NG=F", "HG=F"]
    )
    index_watchlist: list[str] = Field(
        default=["^GSPC", "^DJI", "^IXIC", "^RUT"]
    )

    # Risk parameters
    max_position_pct: float = 0.10  # Max 10% of portfolio per position
    max_total_exposure_pct: float = 0.80  # Max 80% invested
    default_stop_loss_pct: float = 0.05  # 5% stop loss
    default_take_profit_pct: float = 0.15  # 15% take profit

    # Analysis
    scan_interval_seconds: int = 300  # 5 minutes
    lookback_days: int = 90
    min_confidence: float = 0.15  # Min confidence to recommend

    # Database
    db_path: str = "market_agent.db"

    model_config = {"env_prefix": "MARKET_AGENT_", "env_file": ".env"}

    @property
    def all_watchlist(self) -> list[str]:
        return (self.stock_watchlist + self.crypto_watchlist + self.forex_watchlist
                + self.commodity_watchlist + self.index_watchlist)

    @property
    def has_claude(self) -> bool:
        return bool(self.anthropic_api_key)


settings = Settings()
