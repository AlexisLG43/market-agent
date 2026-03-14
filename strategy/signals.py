"""Signal generation: combine technical indicators and AI analysis."""

from data.models import MarketData, Recommendation, SignalType, TechnicalSummary
from analysis.technical import analyze as technical_analyze
from analysis.ai_analyst import analyze_with_ai
from strategy.risk import calculate_position_size, calculate_stop_take
from config import settings


def generate_recommendation(market_data: MarketData) -> Recommendation | None:
    """Analyze an asset and generate a recommendation if confidence is sufficient."""
    # Step 1: Technical analysis
    tech_summary = technical_analyze(market_data)

    # Step 2: AI analysis (or fallback to technical-only)
    ai_signal, ai_confidence, ai_reasoning = analyze_with_ai(market_data, tech_summary)

    # Step 3: Combine signals
    signal, confidence = _combine_signals(tech_summary, ai_signal, ai_confidence)

    # Skip if below minimum confidence threshold
    if confidence < settings.min_confidence:
        return None

    # Skip HOLD signals
    if signal == SignalType.HOLD:
        return None

    # Step 4: Calculate risk parameters
    price = market_data.asset.current_price
    stop_loss, take_profit = calculate_stop_take(price, signal)
    position_size = calculate_position_size(price, confidence)

    return Recommendation(
        asset=market_data.asset,
        signal=signal,
        confidence=confidence,
        entry_price=price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        position_size=position_size,
        technical_summary=tech_summary,
        ai_reasoning=ai_reasoning,
    )


def _combine_signals(
    tech: TechnicalSummary, ai_signal: SignalType, ai_confidence: float
) -> tuple[SignalType, float]:
    """Combine technical and AI signals into a final signal + confidence.

    Weighting: 40% technical, 60% AI (when available).
    Falls back to 100% technical if AI is not configured.
    """
    score_map = {SignalType.BUY: 1.0, SignalType.SELL: -1.0, SignalType.HOLD: 0.0}

    tech_score = tech.overall_score  # Already -1 to +1
    ai_score = score_map[ai_signal] * ai_confidence

    if settings.has_claude:
        combined = 0.4 * tech_score + 0.6 * ai_score
    else:
        combined = tech_score

    # Convert combined score to signal + confidence
    if combined >= 0.2:
        signal = SignalType.BUY
    elif combined <= -0.2:
        signal = SignalType.SELL
    else:
        signal = SignalType.HOLD

    confidence = min(abs(combined), 1.0)

    return signal, round(confidence, 4)


def scan_and_recommend(all_market_data: list[MarketData]) -> list[Recommendation]:
    """Scan all market data and generate recommendations."""
    recommendations = []
    for md in all_market_data:
        rec = generate_recommendation(md)
        if rec is not None:
            recommendations.append(rec)

    # Sort by confidence descending
    recommendations.sort(key=lambda r: r.confidence, reverse=True)
    return recommendations
