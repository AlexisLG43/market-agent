"""ASCII price charts for terminal display."""

from data.models import OHLCV


def ascii_chart(candles: list[OHLCV], width: int = 60, height: int = 15) -> list[str]:
    """Generate an ASCII price chart from OHLCV candles.

    Returns a list of strings (lines) representing the chart.
    """
    if not candles:
        return ["No data"]

    closes = [c.close for c in candles]

    # Sample down if too many candles
    if len(closes) > width:
        step = len(closes) / width
        sampled = [closes[int(i * step)] for i in range(width)]
    else:
        sampled = closes

    mn = min(sampled)
    mx = max(sampled)
    rng = mx - mn if mx != mn else 1.0

    # Build the chart grid
    lines = []

    for row in range(height):
        price_level = mx - (row / (height - 1)) * rng
        line = f"${price_level:>10,.2f} |"

        for col, val in enumerate(sampled):
            normalized = (val - mn) / rng
            chart_row = int((1 - normalized) * (height - 1))

            if chart_row == row:
                # Determine color hint
                if col > 0 and val >= sampled[col - 1]:
                    line += "^"  # up
                elif col > 0:
                    line += "v"  # down
                else:
                    line += "*"
            elif chart_row < row and row == height - 1:
                line += "_"
            else:
                line += " "

        lines.append(line)

    # X-axis
    axis = " " * 12 + "+" + "-" * len(sampled)
    lines.append(axis)

    # Date labels
    if candles:
        first = candles[0].timestamp.strftime("%m/%d")
        mid_idx = len(candles) // 2
        mid = candles[mid_idx].timestamp.strftime("%m/%d")
        last = candles[-1].timestamp.strftime("%m/%d")
        padding = len(sampled) - len(first) - len(mid) - len(last)
        left_pad = padding // 2
        right_pad = padding - left_pad
        date_line = " " * 12 + " " + first + " " * max(left_pad, 1) + mid + " " * max(right_pad, 1) + last
        lines.append(date_line)

    return lines


def mini_sparkline(candles: list[OHLCV], width: int = 20) -> str:
    """Generate a compact sparkline string from candles."""
    if not candles:
        return ""

    closes = [c.close for c in candles]

    # Sample down
    if len(closes) > width:
        step = len(closes) / width
        sampled = [closes[int(i * step)] for i in range(width)]
    else:
        sampled = closes

    mn = min(sampled)
    rng = max(sampled) - mn if max(sampled) != mn else 1.0

    blocks = " _.-:=!#@"
    result = ""
    for val in sampled:
        normalized = (val - mn) / rng
        idx = int(normalized * (len(blocks) - 1))
        result += blocks[idx]

    return result
