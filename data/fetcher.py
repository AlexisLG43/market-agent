"""Market data fetcher for stocks, crypto, and forex."""

from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf

from data.models import Asset, AssetType, MarketData, OHLCV
from config import settings


def detect_asset_type(symbol: str) -> AssetType:
    """Detect asset type from symbol format."""
    if "/" in symbol:
        return AssetType.CRYPTO
    if symbol.endswith("=X"):
        return AssetType.FOREX
    return AssetType.STOCK


def fetch_stock(symbol: str, days: int | None = None) -> MarketData:
    """Fetch stock data via yfinance."""
    days = days or settings.lookback_days
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period=f"{days}d")

    info = ticker.info
    name = info.get("shortName", info.get("longName", symbol))
    current_price = info.get("currentPrice") or info.get("regularMarketPrice", 0.0)

    # If no current price from info, use last close
    if not current_price and not hist.empty:
        current_price = float(hist["Close"].iloc[-1])

    asset = Asset(
        symbol=symbol,
        asset_type=AssetType.STOCK,
        name=name,
        current_price=current_price,
    )

    candles = _df_to_candles(hist)
    return MarketData(asset=asset, candles=candles)


def fetch_crypto(symbol: str, days: int | None = None) -> MarketData:
    """Fetch crypto data via ccxt (Binance)."""
    days = days or settings.lookback_days
    try:
        import ccxt

        exchange = ccxt.binance({"enableRateLimit": True})
        since = exchange.parse8601(
            (datetime.now() - timedelta(days=days)).isoformat()
        )
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe="1d", since=since, limit=days)

        ticker_data = exchange.fetch_ticker(symbol)
        current_price = ticker_data.get("last", 0.0)

        asset = Asset(
            symbol=symbol,
            asset_type=AssetType.CRYPTO,
            name=symbol,
            current_price=current_price,
        )

        candles = []
        for row in ohlcv:
            candles.append(
                OHLCV(
                    timestamp=datetime.fromtimestamp(row[0] / 1000),
                    open=row[1],
                    high=row[2],
                    low=row[3],
                    close=row[4],
                    volume=row[5],
                )
            )
        return MarketData(asset=asset, candles=candles)
    except Exception:
        # Fallback: use yfinance for crypto (e.g. BTC-USD)
        yf_symbol = symbol.replace("/", "-")
        return _fetch_via_yfinance(yf_symbol, AssetType.CRYPTO, days)


def fetch_forex(symbol: str, days: int | None = None) -> MarketData:
    """Fetch forex data via yfinance (e.g. EURUSD=X)."""
    days = days or settings.lookback_days
    return _fetch_via_yfinance(symbol, AssetType.FOREX, days)


def _fetch_via_yfinance(symbol: str, asset_type: AssetType, days: int) -> MarketData:
    """Generic yfinance fetch used as primary/fallback."""
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period=f"{days}d")

    current_price = 0.0
    if not hist.empty:
        current_price = float(hist["Close"].iloc[-1])

    asset = Asset(
        symbol=symbol,
        asset_type=asset_type,
        name=symbol,
        current_price=current_price,
    )
    candles = _df_to_candles(hist)
    return MarketData(asset=asset, candles=candles)


def fetch_asset(symbol: str, days: int | None = None) -> MarketData:
    """Fetch data for any asset, auto-detecting type."""
    asset_type = detect_asset_type(symbol)
    if asset_type == AssetType.CRYPTO:
        return fetch_crypto(symbol, days)
    elif asset_type == AssetType.FOREX:
        return fetch_forex(symbol, days)
    else:
        return fetch_stock(symbol, days)


def fetch_all_watchlist() -> list[MarketData]:
    """Fetch data for all assets in the watchlist."""
    results = []
    for symbol in settings.all_watchlist:
        try:
            data = fetch_asset(symbol)
            results.append(data)
        except Exception as e:
            print(f"  Warning: Failed to fetch {symbol}: {e}")
    return results


def _df_to_candles(df: pd.DataFrame) -> list[OHLCV]:
    """Convert a yfinance DataFrame to list of OHLCV."""
    candles = []
    for idx, row in df.iterrows():
        candles.append(
            OHLCV(
                timestamp=idx.to_pydatetime() if hasattr(idx, "to_pydatetime") else datetime.now(),
                open=float(row["Open"]),
                high=float(row["High"]),
                low=float(row["Low"]),
                close=float(row["Close"]),
                volume=float(row["Volume"]),
            )
        )
    return candles
