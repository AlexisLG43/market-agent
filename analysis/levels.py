"""Support and resistance level detection."""

from dataclasses import dataclass

from data.models import OHLCV


@dataclass
class PriceLevel:
    price: float
    level_type: str  # "support" or "resistance"
    strength: int  # Number of times tested
    description: str = ""


def detect_levels(candles: list[OHLCV], tolerance_pct: float = 1.5) -> list[PriceLevel]:
    """Detect support and resistance levels from price history.

    Uses local min/max detection and groups nearby levels.
    """
    if len(candles) < 10:
        return []

    closes = [c.close for c in candles]
    highs = [c.high for c in candles]
    lows = [c.low for c in candles]
    current_price = closes[-1]

    # Find local minima (support) and maxima (resistance)
    local_mins = []
    local_maxs = []
    window = 5

    for i in range(window, len(candles) - window):
        # Local minimum
        if lows[i] == min(lows[i - window:i + window + 1]):
            local_mins.append(lows[i])
        # Local maximum
        if highs[i] == max(highs[i - window:i + window + 1]):
            local_maxs.append(highs[i])

    # Group nearby levels
    support_levels = _group_levels(local_mins, tolerance_pct)
    resistance_levels = _group_levels(local_maxs, tolerance_pct)

    levels = []

    for price, count in support_levels:
        if price < current_price:
            dist = ((current_price - price) / current_price) * 100
            levels.append(PriceLevel(
                price=round(price, 4),
                level_type="support",
                strength=count,
                description=f"{dist:.1f}% below current price",
            ))

    for price, count in resistance_levels:
        if price > current_price:
            dist = ((price - current_price) / current_price) * 100
            levels.append(PriceLevel(
                price=round(price, 4),
                level_type="resistance",
                strength=count,
                description=f"{dist:.1f}% above current price",
            ))

    # Sort: support descending (nearest first), resistance ascending
    supports = sorted([l for l in levels if l.level_type == "support"], key=lambda l: -l.price)
    resistances = sorted([l for l in levels if l.level_type == "resistance"], key=lambda l: l.price)

    # Return top 3 of each
    return supports[:3] + resistances[:3]


def _group_levels(prices: list[float], tolerance_pct: float) -> list[tuple[float, int]]:
    """Group nearby prices into levels. Returns (avg_price, count) pairs."""
    if not prices:
        return []

    sorted_prices = sorted(prices)
    groups: list[list[float]] = [[sorted_prices[0]]]

    for price in sorted_prices[1:]:
        if abs(price - groups[-1][-1]) / groups[-1][-1] * 100 < tolerance_pct:
            groups[-1].append(price)
        else:
            groups.append([price])

    result = []
    for group in groups:
        if len(group) >= 2:  # Only include levels tested at least twice
            avg = sum(group) / len(group)
            result.append((avg, len(group)))

    result.sort(key=lambda x: -x[1])  # Sort by strength
    return result


def calc_pivot_points(candles: list[OHLCV]) -> dict[str, float]:
    """Calculate classic pivot points from the most recent candle."""
    if not candles:
        return {}

    last = candles[-1]
    pivot = (last.high + last.low + last.close) / 3
    r1 = 2 * pivot - last.low
    s1 = 2 * pivot - last.high
    r2 = pivot + (last.high - last.low)
    s2 = pivot - (last.high - last.low)

    return {
        "S2": round(s2, 4),
        "S1": round(s1, 4),
        "Pivot": round(pivot, 4),
        "R1": round(r1, 4),
        "R2": round(r2, 4),
    }
