"""Risk management and position sizing."""

from data.models import PortfolioState, SignalType
from config import settings


def calculate_position_size(
    price: float,
    confidence: float,
    portfolio: PortfolioState | None = None,
) -> float:
    """Calculate position size in dollars based on confidence and risk limits.

    Higher confidence = larger position, capped by max_position_pct.
    """
    if portfolio is None:
        total_value = settings.starting_capital
        cash = settings.starting_capital
    else:
        total_value = portfolio.total_value
        cash = portfolio.cash

    # Max position size based on portfolio
    max_position = total_value * settings.max_position_pct

    # Scale by confidence: at 50% confidence use 50% of max, at 100% use 100%
    scaled = max_position * confidence

    # Don't exceed available cash
    position = min(scaled, cash * 0.95)  # Keep 5% cash buffer

    return round(position, 2)


def calculate_stop_take(
    entry_price: float,
    signal: SignalType,
    stop_pct: float | None = None,
    take_pct: float | None = None,
) -> tuple[float, float]:
    """Calculate stop-loss and take-profit levels."""
    stop_pct = stop_pct or settings.default_stop_loss_pct
    take_pct = take_pct or settings.default_take_profit_pct

    if signal == SignalType.BUY:
        stop_loss = entry_price * (1 - stop_pct)
        take_profit = entry_price * (1 + take_pct)
    elif signal == SignalType.SELL:
        # For short positions (conceptually)
        stop_loss = entry_price * (1 + stop_pct)
        take_profit = entry_price * (1 - take_pct)
    else:
        stop_loss = entry_price
        take_profit = entry_price

    return round(stop_loss, 4), round(take_profit, 4)


def check_exposure(portfolio: PortfolioState) -> bool:
    """Check if we're within maximum exposure limits."""
    if portfolio.total_value == 0:
        return False
    exposure = portfolio.positions_value / portfolio.total_value
    return exposure < settings.max_total_exposure_pct


def risk_check(
    portfolio: PortfolioState, position_size: float
) -> tuple[bool, str]:
    """Run risk checks before a trade. Returns (ok, reason)."""
    if position_size <= 0:
        return False, "Position size must be positive"

    if position_size > portfolio.cash:
        return False, f"Insufficient cash: ${portfolio.cash:.2f} available, ${position_size:.2f} needed"

    if not check_exposure(portfolio):
        return False, f"Maximum exposure limit ({settings.max_total_exposure_pct:.0%}) reached"

    max_pos = portfolio.total_value * settings.max_position_pct
    if position_size > max_pos:
        return False, f"Position exceeds max size: ${max_pos:.2f} (${position_size:.2f} requested)"

    return True, "OK"
