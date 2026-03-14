"""Data models for the market agent."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class AssetType(str, Enum):
    STOCK = "stock"
    CRYPTO = "crypto"
    FOREX = "forex"


class SignalType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class TradeStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"


class Asset(BaseModel):
    """A tradeable asset."""
    symbol: str
    asset_type: AssetType
    name: str = ""
    current_price: float = 0.0
    last_updated: datetime = Field(default_factory=datetime.now)


class OHLCV(BaseModel):
    """A single OHLCV candle."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class MarketData(BaseModel):
    """Market data for an asset: current price + historical candles."""
    asset: Asset
    candles: list[OHLCV] = []
    fetch_time: datetime = Field(default_factory=datetime.now)


class IndicatorResult(BaseModel):
    """Result of a single technical indicator."""
    name: str
    value: float
    signal: SignalType
    description: str = ""


class TechnicalSummary(BaseModel):
    """Summary of all technical indicators for an asset."""
    asset: Asset
    indicators: list[IndicatorResult] = []
    overall_signal: SignalType = SignalType.HOLD
    overall_score: float = 0.0  # -1 (strong sell) to +1 (strong buy)

    @property
    def buy_count(self) -> int:
        return sum(1 for i in self.indicators if i.signal == SignalType.BUY)

    @property
    def sell_count(self) -> int:
        return sum(1 for i in self.indicators if i.signal == SignalType.SELL)


class Recommendation(BaseModel):
    """A trade recommendation for user approval."""
    id: str = Field(default_factory=lambda: datetime.now().strftime("%Y%m%d%H%M%S"))
    asset: Asset
    signal: SignalType
    confidence: float  # 0.0 to 1.0
    entry_price: float
    stop_loss: float = 0.0
    take_profit: float = 0.0
    position_size: float = 0.0  # Dollar amount
    technical_summary: TechnicalSummary | None = None
    ai_reasoning: str = ""
    created_at: datetime = Field(default_factory=datetime.now)

    @property
    def confidence_pct(self) -> str:
        return f"{self.confidence * 100:.0f}%"


class Trade(BaseModel):
    """A recorded trade (paper or real)."""
    id: int = 0
    symbol: str
    asset_type: AssetType
    signal: SignalType
    entry_price: float
    exit_price: float | None = None
    quantity: float = 0.0
    position_value: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    status: TradeStatus = TradeStatus.OPEN
    pnl: float = 0.0
    pnl_pct: float = 0.0
    confidence: float = 0.0
    reasoning: str = ""
    opened_at: datetime = Field(default_factory=datetime.now)
    closed_at: datetime | None = None

    @property
    def is_open(self) -> bool:
        return self.status == TradeStatus.OPEN


class PortfolioState(BaseModel):
    """Current state of the paper trading portfolio."""
    cash: float = 100_000.0
    total_value: float = 100_000.0
    positions: list[Trade] = []
    total_pnl: float = 0.0
    total_pnl_pct: float = 0.0
    win_count: int = 0
    loss_count: int = 0
    total_trades: int = 0

    @property
    def win_rate(self) -> float:
        if self.total_trades == 0:
            return 0.0
        return self.win_count / self.total_trades

    @property
    def positions_value(self) -> float:
        return sum(t.position_value for t in self.positions if t.is_open)
