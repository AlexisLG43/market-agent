"""Portfolio management and paper trading engine."""

from datetime import datetime

from data.models import (
    AssetType, PortfolioState, Recommendation, SignalType, Trade, TradeStatus,
)
from data.fetcher import detect_asset_type
from storage.database import Database
from strategy.risk import risk_check


class Portfolio:
    """Paper trading portfolio manager."""

    def __init__(self, db: Database):
        self.db = db
        self.state = db.load_portfolio()

    def refresh(self):
        """Reload state from database."""
        self.state = self.db.load_portfolio()

    def execute_trade(self, rec: Recommendation) -> Trade | None:
        """Execute a trade from an approved recommendation."""
        # Risk check
        ok, reason = risk_check(self.state, rec.position_size)
        if not ok:
            print(f"  Risk check failed: {reason}")
            return None

        quantity = rec.position_size / rec.entry_price if rec.entry_price > 0 else 0

        trade = Trade(
            symbol=rec.asset.symbol,
            asset_type=rec.asset.asset_type,
            signal=rec.signal,
            entry_price=rec.entry_price,
            quantity=quantity,
            position_value=rec.position_size,
            stop_loss=rec.stop_loss,
            take_profit=rec.take_profit,
            status=TradeStatus.OPEN,
            confidence=rec.confidence,
            reasoning=rec.ai_reasoning,
        )

        # Update cash
        self.state.cash -= rec.position_size
        trade.id = self.db.save_trade(trade)
        self.state.total_trades += 1
        self._save_state()

        # Record recommendation
        self.db.save_recommendation(
            symbol=rec.asset.symbol,
            signal=rec.signal.value,
            confidence=rec.confidence,
            entry_price=rec.entry_price,
            reasoning=rec.ai_reasoning,
            approved=True,
        )

        return trade

    def close_trade(self, trade: Trade, exit_price: float) -> Trade:
        """Close an open trade at the given price."""
        if trade.signal == SignalType.BUY:
            trade.pnl = (exit_price - trade.entry_price) * trade.quantity
        else:
            trade.pnl = (trade.entry_price - exit_price) * trade.quantity

        trade.pnl_pct = (trade.pnl / trade.position_value) * 100 if trade.position_value else 0
        trade.exit_price = exit_price
        trade.status = TradeStatus.CLOSED
        trade.closed_at = datetime.now()

        # Return capital + P&L
        self.state.cash += trade.position_value + trade.pnl

        if trade.pnl >= 0:
            self.state.win_count += 1
        else:
            self.state.loss_count += 1

        self.db.update_trade(trade)
        self._recalculate()
        self._save_state()
        return trade

    def check_stops(self, prices: dict[str, float]) -> list[Trade]:
        """Check all open positions against stop-loss and take-profit levels."""
        closed = []
        for trade in list(self.state.positions):
            price = prices.get(trade.symbol)
            if price is None:
                continue

            should_close = False
            if trade.signal == SignalType.BUY:
                if trade.stop_loss > 0 and price <= trade.stop_loss:
                    should_close = True
                elif trade.take_profit > 0 and price >= trade.take_profit:
                    should_close = True
            else:  # SELL
                if trade.stop_loss > 0 and price >= trade.stop_loss:
                    should_close = True
                elif trade.take_profit > 0 and price <= trade.take_profit:
                    should_close = True

            if should_close:
                closed_trade = self.close_trade(trade, price)
                closed.append(closed_trade)

        return closed

    def update_positions_value(self, prices: dict[str, float]):
        """Update the market value of all open positions."""
        for trade in self.state.positions:
            price = prices.get(trade.symbol)
            if price:
                trade.position_value = trade.quantity * price
        self._recalculate()

    def _recalculate(self):
        """Recalculate total portfolio value and P&L."""
        self.refresh()
        positions_val = self.state.positions_value
        self.state.total_value = self.state.cash + positions_val
        initial = 100_000.0  # Could be stored but using default
        self.state.total_pnl = self.state.total_value - initial
        self.state.total_pnl_pct = (self.state.total_pnl / initial) * 100 if initial else 0

    def _save_state(self):
        """Persist current state."""
        self.db.save_portfolio(self.state)

    def reject_recommendation(self, rec: Recommendation):
        """Record a rejected recommendation."""
        self.db.save_recommendation(
            symbol=rec.asset.symbol,
            signal=rec.signal.value,
            confidence=rec.confidence,
            entry_price=rec.entry_price,
            reasoning=rec.ai_reasoning,
            approved=False,
        )
