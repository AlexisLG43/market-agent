"""AI analysis using Claude API for market reasoning."""

from data.models import MarketData, SignalType, TechnicalSummary
from config import settings


def build_prompt(market_data: MarketData, tech_summary: TechnicalSummary) -> str:
    """Build a prompt for Claude to analyze market data."""
    indicators_text = "\n".join(
        f"  - {ind.name}: {ind.value} → {ind.signal.value} ({ind.description})"
        for ind in tech_summary.indicators
    )

    # Recent price action
    recent = market_data.candles[-5:] if len(market_data.candles) >= 5 else market_data.candles
    price_text = "\n".join(
        f"  {c.timestamp.strftime('%Y-%m-%d')}: O={c.open:.2f} H={c.high:.2f} L={c.low:.2f} C={c.close:.2f} V={c.volume:.0f}"
        for c in recent
    )

    return f"""Analyze this market data and provide a trading recommendation.

Asset: {market_data.asset.symbol} ({market_data.asset.asset_type.value})
Current Price: ${market_data.asset.current_price:.2f}

Technical Indicators:
{indicators_text}

Overall Technical Score: {tech_summary.overall_score:+.2f} ({tech_summary.overall_signal.value})

Recent Price Action (last 5 days):
{price_text}

Provide your analysis in this exact format:
SIGNAL: BUY or SELL or HOLD
CONFIDENCE: 0.0 to 1.0
REASONING: 2-3 sentence explanation of your analysis

Consider:
1. Do the technical indicators agree or conflict?
2. Is there a clear trend or reversal pattern?
3. What's the risk/reward ratio at current levels?
"""


def parse_response(text: str) -> tuple[SignalType, float, str]:
    """Parse Claude's response into structured data."""
    signal = SignalType.HOLD
    confidence = 0.5
    reasoning = ""

    for line in text.strip().split("\n"):
        line = line.strip()
        if line.startswith("SIGNAL:"):
            val = line.split(":", 1)[1].strip().upper()
            if val in ("BUY", "SELL", "HOLD"):
                signal = SignalType(val)
        elif line.startswith("CONFIDENCE:"):
            try:
                confidence = float(line.split(":", 1)[1].strip())
                confidence = max(0.0, min(1.0, confidence))
            except ValueError:
                pass
        elif line.startswith("REASONING:"):
            reasoning = line.split(":", 1)[1].strip()

    return signal, confidence, reasoning


def analyze_with_ai(
    market_data: MarketData, tech_summary: TechnicalSummary
) -> tuple[SignalType, float, str]:
    """Send market data to Claude for AI analysis. Returns (signal, confidence, reasoning)."""
    if not settings.has_claude:
        return (
            tech_summary.overall_signal,
            abs(tech_summary.overall_score),
            "AI analysis unavailable — using technical signals only. "
            "Set MARKET_AGENT_ANTHROPIC_API_KEY to enable.",
        )

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        prompt = build_prompt(market_data, tech_summary)

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )

        response_text = message.content[0].text
        return parse_response(response_text)
    except Exception as e:
        return (
            tech_summary.overall_signal,
            abs(tech_summary.overall_score),
            f"AI analysis error: {e}. Falling back to technical signals.",
        )
