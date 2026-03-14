"""Technical analysis indicators with intensity-weighted scoring."""

import pandas as pd
import ta

from data.models import (
    IndicatorCategory, IndicatorResult, MarketData, OHLCV, SignalType,
    TechnicalSummary,
)


def candles_to_df(candles: list[OHLCV]) -> pd.DataFrame:
    """Convert OHLCV list to a pandas DataFrame."""
    if not candles:
        return pd.DataFrame()
    data = [
        {
            "timestamp": c.timestamp,
            "open": c.open,
            "high": c.high,
            "low": c.low,
            "close": c.close,
            "volume": c.volume,
        }
        for c in candles
    ]
    df = pd.DataFrame(data)
    df.set_index("timestamp", inplace=True)
    df.sort_index(inplace=True)
    return df


# ---------------------------------------------------------------------------
# Momentum indicators
# ---------------------------------------------------------------------------

def calc_rsi(df: pd.DataFrame, period: int = 14) -> IndicatorResult:
    """RSI — oversold/overbought momentum. Intensity scales with extremity."""
    rsi = ta.momentum.RSIIndicator(df["close"], window=period)
    value = rsi.rsi().iloc[-1]

    if pd.isna(value):
        return IndicatorResult(name="RSI", value=0, signal=SignalType.HOLD,
                               category=IndicatorCategory.MOMENTUM, weight=1.2,
                               description="Insufficient data")

    if value < 30:
        signal = SignalType.BUY
        # RSI 30 = 0.3 intensity, RSI 10 = 1.0
        intensity = min((30 - value) / 20, 1.0)
        desc = f"RSI {value:.1f} — oversold"
    elif value > 70:
        signal = SignalType.SELL
        intensity = min((value - 70) / 20, 1.0)
        desc = f"RSI {value:.1f} — overbought"
    else:
        signal = SignalType.HOLD
        intensity = 0.0
        desc = f"RSI {value:.1f} — neutral"

    return IndicatorResult(name="RSI", value=round(value, 2), signal=signal,
                           intensity=round(intensity, 3),
                           category=IndicatorCategory.MOMENTUM, weight=1.2,
                           description=desc)


def calc_macd(df: pd.DataFrame) -> IndicatorResult:
    """MACD — trend momentum. Intensity scales with histogram size relative to price."""
    macd_ind = ta.trend.MACD(df["close"])
    macd_line = macd_ind.macd().iloc[-1]
    signal_line = macd_ind.macd_signal().iloc[-1]

    if pd.isna(macd_line) or pd.isna(signal_line):
        return IndicatorResult(name="MACD", value=0, signal=SignalType.HOLD,
                               category=IndicatorCategory.MOMENTUM, weight=1.3,
                               description="Insufficient data")

    diff = macd_line - signal_line
    price = df["close"].iloc[-1]
    # Normalize diff as % of price for cross-asset comparison
    diff_pct = abs(diff / price) * 100 if price > 0 else 0

    if diff > 0:
        signal = SignalType.BUY
        desc = f"MACD above signal ({diff:+.4f}) — bullish"
    elif diff < 0:
        signal = SignalType.SELL
        desc = f"MACD below signal ({diff:+.4f}) — bearish"
    else:
        signal = SignalType.HOLD
        desc = "MACD at signal line — neutral"

    # Intensity: 0.5% of price = moderate (0.5), 2%+ = strong (1.0)
    intensity = min(diff_pct / 2.0, 1.0) if signal != SignalType.HOLD else 0.0

    return IndicatorResult(name="MACD", value=round(diff, 4), signal=signal,
                           intensity=round(intensity, 3),
                           category=IndicatorCategory.MOMENTUM, weight=1.3,
                           description=desc)


def calc_stochastic(df: pd.DataFrame, period: int = 14) -> IndicatorResult:
    """Stochastic Oscillator — momentum with crossover detection."""
    stoch = ta.momentum.StochasticOscillator(df["high"], df["low"], df["close"], window=period)
    k = stoch.stoch().iloc[-1]
    d = stoch.stoch_signal().iloc[-1]

    if pd.isna(k) or pd.isna(d):
        return IndicatorResult(name="Stochastic", value=0, signal=SignalType.HOLD,
                               category=IndicatorCategory.MOMENTUM, weight=1.0,
                               description="Insufficient data")

    if k < 20 and d < 20:
        signal = SignalType.BUY
        intensity = min((20 - min(k, d)) / 20, 1.0)
        desc = f"Stoch %K={k:.1f} %D={d:.1f} — oversold"
    elif k > 80 and d > 80:
        signal = SignalType.SELL
        intensity = min((max(k, d) - 80) / 20, 1.0)
        desc = f"Stoch %K={k:.1f} %D={d:.1f} — overbought"
    elif k > d and k < 50:
        signal = SignalType.BUY
        intensity = 0.4  # Crossover without extreme = moderate
        desc = f"Stoch %K={k:.1f} crossing above %D={d:.1f} — bullish crossover"
    elif k < d and k > 50:
        signal = SignalType.SELL
        intensity = 0.4
        desc = f"Stoch %K={k:.1f} crossing below %D={d:.1f} — bearish crossover"
    else:
        signal = SignalType.HOLD
        intensity = 0.0
        desc = f"Stoch %K={k:.1f} %D={d:.1f} — neutral"

    return IndicatorResult(name="Stochastic", value=round(k, 2), signal=signal,
                           intensity=round(intensity, 3),
                           category=IndicatorCategory.MOMENTUM, weight=1.0,
                           description=desc)


# ---------------------------------------------------------------------------
# Trend indicators
# ---------------------------------------------------------------------------

def calc_moving_averages(df: pd.DataFrame) -> IndicatorResult:
    """SMA 20/50 crossover — trend direction. Intensity based on price distance from MAs."""
    if len(df) < 50:
        return IndicatorResult(name="MA Cross", value=0, signal=SignalType.HOLD,
                               category=IndicatorCategory.TREND, weight=1.5,
                               description="Insufficient data")

    sma20 = df["close"].rolling(20).mean().iloc[-1]
    sma50 = df["close"].rolling(50).mean().iloc[-1]
    price = df["close"].iloc[-1]

    if pd.isna(sma20) or pd.isna(sma50):
        return IndicatorResult(name="MA Cross", value=0, signal=SignalType.HOLD,
                               category=IndicatorCategory.TREND, weight=1.5,
                               description="Insufficient data")

    above_20 = price > sma20
    above_50 = price > sma50
    golden = sma20 > sma50

    # Distance from SMA50 as % — measures how committed the trend is
    distance_pct = abs(price - sma50) / sma50 * 100

    if above_20 and above_50 and golden:
        signal = SignalType.BUY
        desc = "Price above SMA20 & SMA50, golden cross — bullish"
        value = 1.0
    elif not above_20 and not above_50 and not golden:
        signal = SignalType.SELL
        desc = "Price below SMA20 & SMA50, death cross — bearish"
        value = -1.0
    else:
        signal = SignalType.HOLD
        desc = "Mixed moving average signals — neutral"
        value = 0.0

    # Intensity: 2% away = moderate (0.5), 5%+ = strong (1.0)
    intensity = min(distance_pct / 5.0, 1.0) if signal != SignalType.HOLD else 0.0

    return IndicatorResult(name="MA Cross", value=value, signal=signal,
                           intensity=round(intensity, 3),
                           category=IndicatorCategory.TREND, weight=1.5,
                           description=desc)


def calc_adx(df: pd.DataFrame, period: int = 14) -> IndicatorResult:
    """ADX — trend strength with directional index. High weight: confirms other signals."""
    adx = ta.trend.ADXIndicator(df["high"], df["low"], df["close"], window=period)
    adx_val = adx.adx().iloc[-1]
    plus_di = adx.adx_pos().iloc[-1]
    minus_di = adx.adx_neg().iloc[-1]

    if pd.isna(adx_val) or pd.isna(plus_di) or pd.isna(minus_di):
        return IndicatorResult(name="ADX", value=0, signal=SignalType.HOLD,
                               category=IndicatorCategory.TREND, weight=1.5,
                               description="Insufficient data")

    if adx_val > 25 and plus_di > minus_di:
        signal = SignalType.BUY
        # ADX 25 = weak trend (0.3), ADX 50+ = very strong (1.0)
        intensity = min((adx_val - 20) / 30, 1.0)
        desc = f"ADX {adx_val:.1f} +DI>{minus_di:.1f} — strong uptrend"
    elif adx_val > 25 and minus_di > plus_di:
        signal = SignalType.SELL
        intensity = min((adx_val - 20) / 30, 1.0)
        desc = f"ADX {adx_val:.1f} -DI>{plus_di:.1f} — strong downtrend"
    else:
        signal = SignalType.HOLD
        intensity = 0.0
        desc = f"ADX {adx_val:.1f} — weak/no trend"

    return IndicatorResult(name="ADX", value=round(adx_val, 2), signal=signal,
                           intensity=round(intensity, 3),
                           category=IndicatorCategory.TREND, weight=1.5,
                           description=desc)


def calc_ema_cross(df: pd.DataFrame) -> IndicatorResult:
    """EMA 12/26 crossover — faster trend signal. Fresh crossovers get high intensity."""
    if len(df) < 26:
        return IndicatorResult(name="EMA Cross", value=0, signal=SignalType.HOLD,
                               category=IndicatorCategory.TREND, weight=1.3,
                               description="Insufficient data")

    ema12 = df["close"].ewm(span=12).mean()
    ema26 = df["close"].ewm(span=26).mean()

    current_diff = ema12.iloc[-1] - ema26.iloc[-1]
    prev_diff = ema12.iloc[-2] - ema26.iloc[-2]

    if pd.isna(current_diff) or pd.isna(prev_diff):
        return IndicatorResult(name="EMA Cross", value=0, signal=SignalType.HOLD,
                               category=IndicatorCategory.TREND, weight=1.3,
                               description="Insufficient data")

    price = df["close"].iloc[-1]
    diff_pct = (current_diff / price) * 100
    just_crossed = (current_diff > 0 and prev_diff <= 0) or (current_diff < 0 and prev_diff >= 0)

    if current_diff > 0 and prev_diff <= 0:
        signal = SignalType.BUY
        intensity = 0.9  # Fresh crossover = very strong
        desc = f"EMA12 just crossed above EMA26 ({diff_pct:+.2f}%) — bullish crossover"
    elif current_diff < 0 and prev_diff >= 0:
        signal = SignalType.SELL
        intensity = 0.9
        desc = f"EMA12 just crossed below EMA26 ({diff_pct:+.2f}%) — bearish crossover"
    elif current_diff > 0:
        signal = SignalType.BUY
        intensity = min(abs(diff_pct) / 2.0, 0.7)  # Cap at 0.7 for ongoing trend
        desc = f"EMA12 above EMA26 ({diff_pct:+.2f}%) — bullish"
    elif current_diff < 0:
        signal = SignalType.SELL
        intensity = min(abs(diff_pct) / 2.0, 0.7)
        desc = f"EMA12 below EMA26 ({diff_pct:+.2f}%) — bearish"
    else:
        signal = SignalType.HOLD
        intensity = 0.0
        desc = "EMA12 = EMA26 — neutral"

    return IndicatorResult(name="EMA Cross", value=round(diff_pct, 4), signal=signal,
                           intensity=round(intensity, 3),
                           category=IndicatorCategory.TREND, weight=1.3,
                           description=desc)


# ---------------------------------------------------------------------------
# Volume indicators
# ---------------------------------------------------------------------------

def calc_volume_trend(df: pd.DataFrame, period: int = 20) -> IndicatorResult:
    """Volume spike analysis — confirms price moves."""
    if len(df) < period:
        return IndicatorResult(name="Volume", value=0, signal=SignalType.HOLD,
                               category=IndicatorCategory.VOLUME, weight=1.0,
                               description="Insufficient data")

    avg_vol = df["volume"].rolling(period).mean().iloc[-1]
    current_vol = df["volume"].iloc[-1]

    if pd.isna(avg_vol) or avg_vol == 0:
        return IndicatorResult(name="Volume", value=0, signal=SignalType.HOLD,
                               category=IndicatorCategory.VOLUME, weight=1.0,
                               description="No volume data")

    ratio = current_vol / avg_vol
    price_change = (df["close"].iloc[-1] - df["close"].iloc[-2]) / df["close"].iloc[-2]

    if ratio > 1.5 and price_change > 0:
        signal = SignalType.BUY
        intensity = min((ratio - 1.0) / 2.0, 1.0)  # 3x vol = 1.0
        desc = f"Volume {ratio:.1f}x avg with price up — bullish momentum"
    elif ratio > 1.5 and price_change < 0:
        signal = SignalType.SELL
        intensity = min((ratio - 1.0) / 2.0, 1.0)
        desc = f"Volume {ratio:.1f}x avg with price down — bearish pressure"
    else:
        signal = SignalType.HOLD
        intensity = 0.0
        desc = f"Volume {ratio:.1f}x avg — normal"

    return IndicatorResult(name="Volume", value=round(ratio, 2), signal=signal,
                           intensity=round(intensity, 3),
                           category=IndicatorCategory.VOLUME, weight=1.0,
                           description=desc)


def calc_obv(df: pd.DataFrame) -> IndicatorResult:
    """On-Balance Volume — accumulation vs distribution."""
    obv = ta.volume.OnBalanceVolumeIndicator(df["close"], df["volume"])
    obv_series = obv.on_balance_volume()

    if len(obv_series) < 20 or obv_series.isna().all():
        return IndicatorResult(name="OBV", value=0, signal=SignalType.HOLD,
                               category=IndicatorCategory.VOLUME, weight=1.1,
                               description="Insufficient data")

    obv_sma = obv_series.rolling(20).mean()
    current_obv = obv_series.iloc[-1]
    current_sma = obv_sma.iloc[-1]

    if pd.isna(current_sma):
        return IndicatorResult(name="OBV", value=0, signal=SignalType.HOLD,
                               category=IndicatorCategory.VOLUME, weight=1.1,
                               description="Insufficient data")

    pct_diff = ((current_obv - current_sma) / abs(current_sma) * 100) if current_sma != 0 else 0

    if pct_diff > 10:
        signal = SignalType.BUY
        intensity = min(abs(pct_diff) / 50, 1.0)  # 50% divergence = max
        desc = f"OBV {pct_diff:+.1f}% above avg — accumulation"
    elif pct_diff < -10:
        signal = SignalType.SELL
        intensity = min(abs(pct_diff) / 50, 1.0)
        desc = f"OBV {pct_diff:+.1f}% below avg — distribution"
    else:
        signal = SignalType.HOLD
        intensity = 0.0
        desc = f"OBV {pct_diff:+.1f}% vs avg — neutral"

    return IndicatorResult(name="OBV", value=round(pct_diff, 2), signal=signal,
                           intensity=round(intensity, 3),
                           category=IndicatorCategory.VOLUME, weight=1.1,
                           description=desc)


# ---------------------------------------------------------------------------
# Volatility indicators
# ---------------------------------------------------------------------------

def calc_bollinger(df: pd.DataFrame, period: int = 20) -> IndicatorResult:
    """Bollinger Bands — price at extremes of volatility envelope."""
    bb = ta.volatility.BollingerBands(df["close"], window=period)
    upper = bb.bollinger_hband().iloc[-1]
    lower = bb.bollinger_lband().iloc[-1]
    price = df["close"].iloc[-1]

    if pd.isna(upper) or pd.isna(lower):
        return IndicatorResult(name="Bollinger", value=0, signal=SignalType.HOLD,
                               category=IndicatorCategory.VOLATILITY, weight=1.0,
                               description="Insufficient data")

    band_width = upper - lower
    if band_width == 0:
        position = 0.5
    else:
        position = (price - lower) / band_width

    if position < 0.1:
        signal = SignalType.BUY
        intensity = min((0.1 - position) / 0.1, 1.0)  # Below bands = max
        desc = f"Price near lower band ({position:.0%}) — oversold"
    elif position > 0.9:
        signal = SignalType.SELL
        intensity = min((position - 0.9) / 0.1, 1.0)
        desc = f"Price near upper band ({position:.0%}) — overbought"
    else:
        signal = SignalType.HOLD
        intensity = 0.0
        desc = f"Price at {position:.0%} of bands — neutral"

    return IndicatorResult(name="Bollinger", value=round(position, 4), signal=signal,
                           intensity=round(intensity, 3),
                           category=IndicatorCategory.VOLATILITY, weight=1.0,
                           description=desc)


def calc_atr_trend(df: pd.DataFrame, period: int = 14) -> IndicatorResult:
    """ATR — volatility expansion as breakout confirmation."""
    atr_ind = ta.volatility.AverageTrueRange(df["high"], df["low"], df["close"], window=period)
    atr = atr_ind.average_true_range()

    if len(atr) < period * 2 or atr.isna().all():
        return IndicatorResult(name="ATR", value=0, signal=SignalType.HOLD,
                               category=IndicatorCategory.VOLATILITY, weight=0.8,
                               description="Insufficient data")

    current_atr = atr.iloc[-1]
    avg_atr = atr.rolling(period).mean().iloc[-1]

    if pd.isna(current_atr) or pd.isna(avg_atr) or avg_atr == 0:
        return IndicatorResult(name="ATR", value=0, signal=SignalType.HOLD,
                               category=IndicatorCategory.VOLATILITY, weight=0.8,
                               description="Insufficient data")

    ratio = current_atr / avg_atr
    price = df["close"].iloc[-1]
    atr_pct = (current_atr / price) * 100
    price_change = df["close"].iloc[-1] - df["close"].iloc[-5] if len(df) >= 5 else 0

    if ratio > 1.3 and price_change > 0:
        signal = SignalType.BUY
        intensity = min((ratio - 1.0) / 1.0, 1.0)  # 2x expansion = max
        desc = f"ATR expanding ({atr_pct:.1f}% of price) with upward move — bullish breakout"
    elif ratio > 1.3 and price_change < 0:
        signal = SignalType.SELL
        intensity = min((ratio - 1.0) / 1.0, 1.0)
        desc = f"ATR expanding ({atr_pct:.1f}% of price) with downward move — bearish breakout"
    else:
        signal = SignalType.HOLD
        intensity = 0.0
        desc = f"ATR {atr_pct:.1f}% of price, {ratio:.1f}x avg — normal volatility"

    return IndicatorResult(name="ATR", value=round(atr_pct, 2), signal=signal,
                           intensity=round(intensity, 3),
                           category=IndicatorCategory.VOLATILITY, weight=0.8,
                           description=desc)


# ---------------------------------------------------------------------------
# Weighted scoring engine
# ---------------------------------------------------------------------------

def analyze(market_data: MarketData) -> TechnicalSummary:
    """Run all indicators and compute a weighted, intensity-aware confidence score."""
    df = candles_to_df(market_data.candles)

    if df.empty or len(df) < 14:
        return TechnicalSummary(
            asset=market_data.asset,
            indicators=[],
            overall_signal=SignalType.HOLD,
            overall_score=0.0,
        )

    indicators = [
        # Momentum (3)
        calc_rsi(df),
        calc_macd(df),
        calc_stochastic(df),
        # Trend (3)
        calc_moving_averages(df),
        calc_adx(df),
        calc_ema_cross(df),
        # Volume (2)
        calc_volume_trend(df),
        calc_obv(df),
        # Volatility (2)
        calc_bollinger(df),
        calc_atr_trend(df),
    ]

    # --- Weighted intensity scoring ---
    # Each indicator contributes: direction * intensity * weight
    # direction: +1 (BUY), -1 (SELL), 0 (HOLD)
    direction_map = {SignalType.BUY: 1.0, SignalType.SELL: -1.0, SignalType.HOLD: 0.0}

    weighted_sum = 0.0
    total_weight = 0.0
    for ind in indicators:
        direction = direction_map[ind.signal]
        weighted_sum += direction * ind.intensity * ind.weight
        total_weight += ind.weight

    # Base score: weighted average in [-1, +1]
    base_score = weighted_sum / total_weight if total_weight > 0 else 0.0

    # --- Category agreement bonus ---
    # When multiple categories agree on direction, boost confidence
    category_signals: dict[IndicatorCategory, list[float]] = {}
    for ind in indicators:
        if ind.signal != SignalType.HOLD:
            direction = direction_map[ind.signal]
            category_signals.setdefault(ind.category, []).append(direction * ind.intensity)

    # Count how many categories lean the same way as base_score
    if base_score != 0:
        base_direction = 1.0 if base_score > 0 else -1.0
        agreeing_categories = 0
        total_categories = len(category_signals)
        for cat, scores in category_signals.items():
            cat_avg = sum(scores) / len(scores)
            if (cat_avg > 0 and base_direction > 0) or (cat_avg < 0 and base_direction < 0):
                agreeing_categories += 1

        # Bonus: if 3/4 categories agree = +30%, all 4 = +50%
        if total_categories >= 2:
            agreement_ratio = agreeing_categories / total_categories
            bonus = agreement_ratio * 0.5  # max 50% bonus
            boosted = abs(base_score) * (1.0 + bonus)
            final_score = min(boosted, 1.0) * base_direction
        else:
            final_score = base_score
    else:
        final_score = 0.0

    # --- Determine signal ---
    if final_score >= 0.15:
        overall = SignalType.BUY
    elif final_score <= -0.15:
        overall = SignalType.SELL
    else:
        overall = SignalType.HOLD

    return TechnicalSummary(
        asset=market_data.asset,
        indicators=indicators,
        overall_signal=overall,
        overall_score=round(final_score, 4),
    )
