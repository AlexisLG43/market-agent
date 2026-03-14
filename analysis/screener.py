"""Asset screener — filter watchlist by indicator conditions."""

from data.models import MarketData, SignalType, TechnicalSummary, IndicatorCategory


def screen(summaries: list[tuple[MarketData, TechnicalSummary]], filters: list[dict]) -> list[tuple[MarketData, TechnicalSummary]]:
    """Filter assets by indicator conditions.

    Each filter is a dict: {"indicator": "RSI", "condition": "<", "value": 30}
    or {"field": "signal", "value": "BUY"}
    or {"field": "confidence", "condition": ">", "value": 0.3}
    """
    results = []

    for md, summary in summaries:
        if _matches_all(summary, filters):
            results.append((md, summary))

    return results


def _matches_all(summary: TechnicalSummary, filters: list[dict]) -> bool:
    for f in filters:
        if not _matches_one(summary, f):
            return False
    return True


def _matches_one(summary: TechnicalSummary, f: dict) -> bool:
    field = f.get("field", "")
    indicator_name = f.get("indicator", "")
    condition = f.get("condition", "=")
    value = f.get("value")

    # Filter by overall signal
    if field == "signal":
        return summary.overall_signal.value == value

    # Filter by confidence
    if field == "confidence":
        conf = abs(summary.overall_score)
        return _compare(conf, condition, float(value))

    # Filter by indicator
    if indicator_name:
        for ind in summary.indicators:
            if ind.name.lower() == indicator_name.lower():
                # Filter by indicator value
                if f.get("by") == "signal":
                    return ind.signal.value == value
                return _compare(ind.value, condition, float(value))

    # Filter by category
    if field == "category":
        cat_name = f.get("category", "")
        direction = f.get("direction", "")
        for ind in summary.indicators:
            if ind.category.value == cat_name:
                if direction == "bullish" and ind.signal == SignalType.BUY:
                    return True
                if direction == "bearish" and ind.signal == SignalType.SELL:
                    return True
        return False

    return True


def _compare(a: float, op: str, b: float) -> bool:
    if op == "<":
        return a < b
    elif op == "<=":
        return a <= b
    elif op == ">":
        return a > b
    elif op == ">=":
        return a >= b
    elif op == "=":
        return abs(a - b) < 0.01
    return False


PRESET_SCREENS = {
    "oversold": [
        {"indicator": "RSI", "condition": "<", "value": 30},
    ],
    "overbought": [
        {"indicator": "RSI", "condition": ">", "value": 70},
    ],
    "strong_buy": [
        {"field": "signal", "value": "BUY"},
        {"field": "confidence", "condition": ">", "value": 0.3},
    ],
    "strong_sell": [
        {"field": "signal", "value": "SELL"},
        {"field": "confidence", "condition": ">", "value": 0.3},
    ],
    "trending": [
        {"indicator": "ADX", "condition": ">", "value": 25},
    ],
    "high_volume": [
        {"indicator": "Volume", "condition": ">", "value": 1.5},
    ],
}
