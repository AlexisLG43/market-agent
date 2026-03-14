# AI Market Agent

A semi-autonomous AI trading agent that monitors stocks, crypto, and forex markets. It analyzes opportunities using technical indicators and optional Claude AI reasoning, presents recommendations for user approval, and tracks performance via paper trading.

## Features

- **Multi-market scanning** — Stocks (yfinance), crypto (ccxt), forex
- **Technical analysis** — RSI, MACD, Bollinger Bands, MA crossover, volume analysis
- **AI reasoning** — Optional Claude API integration for deeper market analysis
- **Paper trading** — $100K virtual portfolio with full P&L tracking
- **Risk management** — Position sizing, stop-loss, take-profit, exposure limits
- **Trade history** — SQLite persistence for all trades and recommendations

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the agent
python main.py
```

## Usage

The agent presents an interactive menu:

1. **Scan markets** — Fetch live data, run analysis, get recommendations
2. **View portfolio** — Cash, total value, P&L, win rate
3. **View positions** — All open trades with entry/stop/target levels
4. **View history** — Closed trades with P&L breakdown
5. **Close a position** — Manually exit a trade at current price
6. **Check stops** — Auto-close positions that hit stop-loss or take-profit

Each recommendation shows the signal (BUY/SELL), confidence score, entry price, and reasoning. You approve or reject each one before any trade is executed.

## Configuration

Settings are loaded from environment variables (prefix `MARKET_AGENT_`) or a `.env` file:

| Variable | Default | Description |
|---|---|---|
| `MARKET_AGENT_ANTHROPIC_API_KEY` | — | Enables Claude AI analysis |
| `MARKET_AGENT_STARTING_CAPITAL` | 100000 | Paper trading starting balance |
| `MARKET_AGENT_MAX_POSITION_PCT` | 0.10 | Max 10% of portfolio per trade |
| `MARKET_AGENT_DEFAULT_STOP_LOSS_PCT` | 0.05 | 5% stop-loss |
| `MARKET_AGENT_DEFAULT_TAKE_PROFIT_PCT` | 0.15 | 15% take-profit |
| `MARKET_AGENT_MIN_CONFIDENCE` | 0.15 | Minimum confidence to recommend |

## Default Watchlist

- **Stocks**: AAPL, MSFT, TSLA
- **Crypto**: BTC/USDT, ETH/USDT
- **Forex**: EUR/USD, GBP/USD

## Project Structure

```
market_agent/
├── main.py                  # Entry point, CLI menu
├── config.py                # Settings and preferences
├── data/
│   ├── fetcher.py           # Market data fetching
│   └── models.py            # Data models (Asset, Trade, etc.)
├── analysis/
│   ├── technical.py         # Technical indicators
│   └── ai_analyst.py        # Claude API analysis
├── strategy/
│   ├── signals.py           # Signal generation
│   └── risk.py              # Risk management
├── trading/
│   ├── portfolio.py         # Paper trading engine
│   └── executor.py          # Trade execution
├── storage/
│   └── database.py          # SQLite persistence
└── ui/
    └── dashboard.py         # Rich CLI dashboard
```

## Disclaimer

This is a paper trading tool for educational purposes. It does not execute real trades or provide financial advice.
