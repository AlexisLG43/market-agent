"""Backtesting engine — test strategy on historical data."""

from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd

from analysis.technical import analyze, candles_to_df
from data.models import MarketData, OHLCV, SignalType, Asset, AssetType
from data.fetcher import fetch_asset, detect_asset_type


@dataclass
class BacktestTrade:
    entry_date: str
    exit_date: str
    signal: str
    entry_price: float
    exit_price: float
    pnl_pct: float
    confidence: float


@dataclass
class BacktestResult:
    symbol: str
    period_days: int
    total_signals: int
    trades: list[BacktestTrade] = field(default_factory=list)
    total_pnl_pct: float = 0.0
    win_count: int = 0
    loss_count: int = 0
    avg_pnl_pct: float = 0.0
    best_pct: float = 0.0
    worst_pct: float = 0.0

    @property
    def win_rate(self) -> float:
        total = self.win_count + self.loss_count
        return self.win_count / total if total > 0 else 0.0


def backtest(symbol: str, days: int = 365, hold_days: int = 5, min_confidence: float = 0.15) -> BacktestResult:
    """Run backtest on historical data.

    Simulates the strategy by walking through history:
    - At each point, run technical analysis on the lookback window
    - If signal is BUY/SELL with sufficient confidence, enter a trade
    - Exit after hold_days and record P&L
    """
    md = fetch_asset(symbol, days=days)
    df = candles_to_df(md.candles)

    if len(df) < 60:
        return BacktestResult(symbol=symbol, period_days=days, total_signals=0)

    trades = []
    total_signals = 0
    lookback = 60  # Need at least 60 candles for indicators

    i = lookback
    while i < len(df) - hold_days:
        # Build MarketData from the lookback window
        window_df = df.iloc[i - lookback:i]
        window_candles = [
            OHLCV(
                timestamp=idx.to_pydatetime() if hasattr(idx, "to_pydatetime") else datetime.now(),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row["volume"]),
            )
            for idx, row in window_df.iterrows()
        ]

        asset_type = detect_asset_type(symbol)
        window_md = MarketData(
            asset=Asset(symbol=symbol, asset_type=asset_type, current_price=float(window_df["close"].iloc[-1])),
            candles=window_candles,
        )

        summary = analyze(window_md)
        confidence = abs(summary.overall_score)

        if summary.overall_signal != SignalType.HOLD and confidence >= min_confidence:
            total_signals += 1
            entry_price = float(df["close"].iloc[i])
            exit_price = float(df["close"].iloc[i + hold_days])

            if summary.overall_signal == SignalType.BUY:
                pnl_pct = ((exit_price - entry_price) / entry_price) * 100
            else:
                pnl_pct = ((entry_price - exit_price) / entry_price) * 100

            entry_date = str(df.index[i].date()) if hasattr(df.index[i], "date") else str(df.index[i])
            exit_date = str(df.index[i + hold_days].date()) if hasattr(df.index[i + hold_days], "date") else str(df.index[i + hold_days])

            trades.append(BacktestTrade(
                entry_date=entry_date,
                exit_date=exit_date,
                signal=summary.overall_signal.value,
                entry_price=entry_price,
                exit_price=exit_price,
                pnl_pct=round(pnl_pct, 2),
                confidence=round(confidence, 4),
            ))

            # Skip ahead past the hold period
            i += hold_days
        else:
            i += 1

    # Compute stats
    result = BacktestResult(symbol=symbol, period_days=days, total_signals=total_signals, trades=trades)
    if trades:
        pnls = [t.pnl_pct for t in trades]
        result.total_pnl_pct = round(sum(pnls), 2)
        result.win_count = sum(1 for p in pnls if p > 0)
        result.loss_count = sum(1 for p in pnls if p <= 0)
        result.avg_pnl_pct = round(result.total_pnl_pct / len(pnls), 2)
        result.best_pct = round(max(pnls), 2)
        result.worst_pct = round(min(pnls), 2)

    return result
