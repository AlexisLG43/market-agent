"""Technical analysis indicators."""

import pandas as pd
import ta

from data.models import (
    Asset, IndicatorResult, MarketData, OHLCV, SignalType, TechnicalSummary,
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


def calc_rsi(df: pd.DataFrame, period: int = 14) -> IndicatorResult:
    """Calculate RSI and generate signal."""
    rsi = ta.momentum.RSIIndicator(df["close"], window=period)
    value = rsi.rsi().iloc[-1]

    if pd.isna(value):
        return IndicatorResult(name="RSI", value=0, signal=SignalType.HOLD, description="Insufficient data")

    if value < 30:
        signal = SignalType.BUY
        desc = f"RSI {value:.1f} — oversold"
    elif value > 70:
        signal = SignalType.SELL
        desc = f"RSI {value:.1f} — overbought"
    else:
        signal = SignalType.HOLD
        desc = f"RSI {value:.1f} — neutral"

    return IndicatorResult(name="RSI", value=round(value, 2), signal=signal, description=desc)


def calc_macd(df: pd.DataFrame) -> IndicatorResult:
    """Calculate MACD and generate signal."""
    macd_ind = ta.trend.MACD(df["close"])
    macd_line = macd_ind.macd().iloc[-1]
    signal_line = macd_ind.macd_signal().iloc[-1]

    if pd.isna(macd_line) or pd.isna(signal_line):
        return IndicatorResult(name="MACD", value=0, signal=SignalType.HOLD, description="Insufficient data")

    diff = macd_line - signal_line

    if diff > 0:
        signal = SignalType.BUY
        desc = f"MACD above signal ({diff:+.4f}) — bullish"
    elif diff < 0:
        signal = SignalType.SELL
        desc = f"MACD below signal ({diff:+.4f}) — bearish"
    else:
        signal = SignalType.HOLD
        desc = "MACD at signal line — neutral"

    return IndicatorResult(name="MACD", value=round(diff, 4), signal=signal, description=desc)


def calc_bollinger(df: pd.DataFrame, period: int = 20) -> IndicatorResult:
    """Calculate Bollinger Bands position and generate signal."""
    bb = ta.volatility.BollingerBands(df["close"], window=period)
    upper = bb.bollinger_hband().iloc[-1]
    lower = bb.bollinger_lband().iloc[-1]
    price = df["close"].iloc[-1]

    if pd.isna(upper) or pd.isna(lower):
        return IndicatorResult(name="Bollinger", value=0, signal=SignalType.HOLD, description="Insufficient data")

    # Position within bands: 0 = at lower, 1 = at upper
    band_width = upper - lower
    if band_width == 0:
        position = 0.5
    else:
        position = (price - lower) / band_width

    if position < 0.1:
        signal = SignalType.BUY
        desc = f"Price near lower band ({position:.0%}) — oversold"
    elif position > 0.9:
        signal = SignalType.SELL
        desc = f"Price near upper band ({position:.0%}) — overbought"
    else:
        signal = SignalType.HOLD
        desc = f"Price at {position:.0%} of bands — neutral"

    return IndicatorResult(name="Bollinger", value=round(position, 4), signal=signal, description=desc)


def calc_moving_averages(df: pd.DataFrame) -> IndicatorResult:
    """Calculate SMA crossover signal (20/50)."""
    if len(df) < 50:
        return IndicatorResult(name="MA Cross", value=0, signal=SignalType.HOLD, description="Insufficient data")

    sma20 = df["close"].rolling(20).mean().iloc[-1]
    sma50 = df["close"].rolling(50).mean().iloc[-1]
    price = df["close"].iloc[-1]

    if pd.isna(sma20) or pd.isna(sma50):
        return IndicatorResult(name="MA Cross", value=0, signal=SignalType.HOLD, description="Insufficient data")

    # Score based on price relative to MAs
    above_20 = price > sma20
    above_50 = price > sma50
    golden = sma20 > sma50

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

    return IndicatorResult(name="MA Cross", value=value, signal=signal, description=desc)


def calc_volume_trend(df: pd.DataFrame, period: int = 20) -> IndicatorResult:
    """Analyze volume trend relative to average."""
    if len(df) < period:
        return IndicatorResult(name="Volume", value=0, signal=SignalType.HOLD, description="Insufficient data")

    avg_vol = df["volume"].rolling(period).mean().iloc[-1]
    current_vol = df["volume"].iloc[-1]

    if pd.isna(avg_vol) or avg_vol == 0:
        return IndicatorResult(name="Volume", value=0, signal=SignalType.HOLD, description="No volume data")

    ratio = current_vol / avg_vol
    price_change = (df["close"].iloc[-1] - df["close"].iloc[-2]) / df["close"].iloc[-2]

    # High volume + price up = bullish, high volume + price down = bearish
    if ratio > 1.5 and price_change > 0:
        signal = SignalType.BUY
        desc = f"Volume {ratio:.1f}x avg with price up — bullish momentum"
    elif ratio > 1.5 and price_change < 0:
        signal = SignalType.SELL
        desc = f"Volume {ratio:.1f}x avg with price down — bearish pressure"
    else:
        signal = SignalType.HOLD
        desc = f"Volume {ratio:.1f}x avg — normal"

    return IndicatorResult(name="Volume", value=round(ratio, 2), signal=signal, description=desc)


def calc_stochastic(df: pd.DataFrame, period: int = 14) -> IndicatorResult:
    """Stochastic Oscillator — momentum overbought/oversold (different timeframe than RSI)."""
    stoch = ta.momentum.StochasticOscillator(df["high"], df["low"], df["close"], window=period)
    k = stoch.stoch().iloc[-1]
    d = stoch.stoch_signal().iloc[-1]

    if pd.isna(k) or pd.isna(d):
        return IndicatorResult(name="Stochastic", value=0, signal=SignalType.HOLD, description="Insufficient data")

    if k < 20 and d < 20:
        signal = SignalType.BUY
        desc = f"Stoch %K={k:.1f} %D={d:.1f} — oversold"
    elif k > 80 and d > 80:
        signal = SignalType.SELL
        desc = f"Stoch %K={k:.1f} %D={d:.1f} — overbought"
    elif k > d and k < 50:
        signal = SignalType.BUY
        desc = f"Stoch %K={k:.1f} crossing above %D={d:.1f} — bullish crossover"
    elif k < d and k > 50:
        signal = SignalType.SELL
        desc = f"Stoch %K={k:.1f} crossing below %D={d:.1f} — bearish crossover"
    else:
        signal = SignalType.HOLD
        desc = f"Stoch %K={k:.1f} %D={d:.1f} — neutral"

    return IndicatorResult(name="Stochastic", value=round(k, 2), signal=signal, description=desc)


def calc_adx(df: pd.DataFrame, period: int = 14) -> IndicatorResult:
    """ADX — trend strength (not direction). Strong trend = trust other signals more."""
    adx = ta.trend.ADXIndicator(df["high"], df["low"], df["close"], window=period)
    adx_val = adx.adx().iloc[-1]
    plus_di = adx.adx_pos().iloc[-1]
    minus_di = adx.adx_neg().iloc[-1]

    if pd.isna(adx_val) or pd.isna(plus_di) or pd.isna(minus_di):
        return IndicatorResult(name="ADX", value=0, signal=SignalType.HOLD, description="Insufficient data")

    if adx_val > 25 and plus_di > minus_di:
        signal = SignalType.BUY
        desc = f"ADX {adx_val:.1f} +DI>{minus_di:.1f} — strong uptrend"
    elif adx_val > 25 and minus_di > plus_di:
        signal = SignalType.SELL
        desc = f"ADX {adx_val:.1f} -DI>{plus_di:.1f} — strong downtrend"
    else:
        signal = SignalType.HOLD
        desc = f"ADX {adx_val:.1f} — weak/no trend"

    return IndicatorResult(name="ADX", value=round(adx_val, 2), signal=signal, description=desc)


def calc_obv(df: pd.DataFrame) -> IndicatorResult:
    """On-Balance Volume — confirms price moves with volume flow."""
    obv = ta.volume.OnBalanceVolumeIndicator(df["close"], df["volume"])
    obv_series = obv.on_balance_volume()

    if len(obv_series) < 20 or obv_series.isna().all():
        return IndicatorResult(name="OBV", value=0, signal=SignalType.HOLD, description="Insufficient data")

    obv_sma = obv_series.rolling(20).mean()
    current_obv = obv_series.iloc[-1]
    current_sma = obv_sma.iloc[-1]

    if pd.isna(current_sma):
        return IndicatorResult(name="OBV", value=0, signal=SignalType.HOLD, description="Insufficient data")

    # OBV above its moving average = accumulation, below = distribution
    pct_diff = ((current_obv - current_sma) / abs(current_sma) * 100) if current_sma != 0 else 0

    if pct_diff > 10:
        signal = SignalType.BUY
        desc = f"OBV {pct_diff:+.1f}% above avg — accumulation"
    elif pct_diff < -10:
        signal = SignalType.SELL
        desc = f"OBV {pct_diff:+.1f}% below avg — distribution"
    else:
        signal = SignalType.HOLD
        desc = f"OBV {pct_diff:+.1f}% vs avg — neutral"

    return IndicatorResult(name="OBV", value=round(pct_diff, 2), signal=signal, description=desc)


def calc_atr_trend(df: pd.DataFrame, period: int = 14) -> IndicatorResult:
    """ATR — volatility expansion/contraction as a breakout signal."""
    atr_ind = ta.volatility.AverageTrueRange(df["high"], df["low"], df["close"], window=period)
    atr = atr_ind.average_true_range()

    if len(atr) < period * 2 or atr.isna().all():
        return IndicatorResult(name="ATR", value=0, signal=SignalType.HOLD, description="Insufficient data")

    current_atr = atr.iloc[-1]
    avg_atr = atr.rolling(period).mean().iloc[-1]

    if pd.isna(current_atr) or pd.isna(avg_atr) or avg_atr == 0:
        return IndicatorResult(name="ATR", value=0, signal=SignalType.HOLD, description="Insufficient data")

    ratio = current_atr / avg_atr
    price = df["close"].iloc[-1]
    atr_pct = (current_atr / price) * 100

    price_change = df["close"].iloc[-1] - df["close"].iloc[-5] if len(df) >= 5 else 0

    if ratio > 1.3 and price_change > 0:
        signal = SignalType.BUY
        desc = f"ATR expanding ({atr_pct:.1f}% of price) with upward move — bullish breakout"
    elif ratio > 1.3 and price_change < 0:
        signal = SignalType.SELL
        desc = f"ATR expanding ({atr_pct:.1f}% of price) with downward move — bearish breakout"
    else:
        signal = SignalType.HOLD
        desc = f"ATR {atr_pct:.1f}% of price, {ratio:.1f}x avg — normal volatility"

    return IndicatorResult(name="ATR", value=round(atr_pct, 2), signal=signal, description=desc)


def calc_ema_cross(df: pd.DataFrame) -> IndicatorResult:
    """EMA 12/26 crossover — faster trend signal than SMA 20/50."""
    if len(df) < 26:
        return IndicatorResult(name="EMA Cross", value=0, signal=SignalType.HOLD, description="Insufficient data")

    ema12 = df["close"].ewm(span=12).mean()
    ema26 = df["close"].ewm(span=26).mean()

    current_diff = ema12.iloc[-1] - ema26.iloc[-1]
    prev_diff = ema12.iloc[-2] - ema26.iloc[-2]

    if pd.isna(current_diff) or pd.isna(prev_diff):
        return IndicatorResult(name="EMA Cross", value=0, signal=SignalType.HOLD, description="Insufficient data")

    price = df["close"].iloc[-1]
    diff_pct = (current_diff / price) * 100

    # Detect crossovers (recent cross is stronger signal)
    if current_diff > 0 and prev_diff <= 0:
        signal = SignalType.BUY
        desc = f"EMA12 just crossed above EMA26 ({diff_pct:+.2f}%) — bullish crossover"
    elif current_diff < 0 and prev_diff >= 0:
        signal = SignalType.SELL
        desc = f"EMA12 just crossed below EMA26 ({diff_pct:+.2f}%) — bearish crossover"
    elif current_diff > 0:
        signal = SignalType.BUY
        desc = f"EMA12 above EMA26 ({diff_pct:+.2f}%) — bullish"
    elif current_diff < 0:
        signal = SignalType.SELL
        desc = f"EMA12 below EMA26 ({diff_pct:+.2f}%) — bearish"
    else:
        signal = SignalType.HOLD
        desc = "EMA12 = EMA26 — neutral"

    return IndicatorResult(name="EMA Cross", value=round(diff_pct, 4), signal=signal, description=desc)


def analyze(market_data: MarketData) -> TechnicalSummary:
    """Run all technical indicators on market data and produce a summary."""
    df = candles_to_df(market_data.candles)

    if df.empty or len(df) < 14:
        return TechnicalSummary(
            asset=market_data.asset,
            indicators=[],
            overall_signal=SignalType.HOLD,
            overall_score=0.0,
        )

    indicators = [
        calc_rsi(df),
        calc_macd(df),
        calc_bollinger(df),
        calc_moving_averages(df),
        calc_volume_trend(df),
        calc_stochastic(df),
        calc_adx(df),
        calc_obv(df),
        calc_atr_trend(df),
        calc_ema_cross(df),
    ]

    # Score: +1 for BUY, -1 for SELL, 0 for HOLD
    score_map = {SignalType.BUY: 1, SignalType.SELL: -1, SignalType.HOLD: 0}
    total = sum(score_map[ind.signal] for ind in indicators)
    max_score = len(indicators)
    normalized = total / max_score if max_score > 0 else 0

    if normalized > 0.3:
        overall = SignalType.BUY
    elif normalized < -0.3:
        overall = SignalType.SELL
    else:
        overall = SignalType.HOLD

    return TechnicalSummary(
        asset=market_data.asset,
        indicators=indicators,
        overall_signal=overall,
        overall_score=round(normalized, 4),
    )
