"""Trade execution engine (paper trading mode)."""

from data.models import Recommendation, Trade
from trading.portfolio import Portfolio


class Executor:
    """Handles trade execution. Currently paper-trading only."""

    def __init__(self, portfolio: Portfolio):
        self.portfolio = portfolio

    def execute(self, rec: Recommendation) -> Trade | None:
        """Execute an approved recommendation as a paper trade."""
        trade = self.portfolio.execute_trade(rec)
        return trade

    def close_position(self, trade: Trade, exit_price: float) -> Trade:
        """Close an existing position."""
        return self.portfolio.close_trade(trade, exit_price)

    def check_stops(self, prices: dict[str, float]) -> list[Trade]:
        """Check all open positions against stop/take-profit levels."""
        return self.portfolio.check_stops(prices)
