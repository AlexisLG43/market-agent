# AI Market Agent

A semi-autonomous AI trading agent that monitors stocks, crypto, forex, commodities, and indices. It analyzes opportunities using 10 technical indicators with intensity-weighted scoring and optional Claude AI reasoning, presents recommendations for user approval, and tracks performance via paper trading.

## Features

- **Multi-market scanning** — Stocks, crypto, forex, commodities, indices — 27 assets across 5 markets
- **10 technical indicators** — RSI, MACD, Stochastic, Bollinger Bands, SMA crossover, EMA crossover, ADX, OBV, ATR, volume analysis
- **Intensity-weighted scoring** — Each indicator reports signal strength (0.0–1.0), weighted by category (trend, momentum, volume, volatility) with cross-category agreement bonuses
- **AI reasoning** — Optional Claude API integration for deeper market analysis (60/40 AI/technical weighting)
- **Paper trading** — $100K virtual portfolio with full P&L tracking
- **Risk management** — Confidence-scaled position sizing, stop-loss, take-profit, exposure limits
- **Rich CLI dashboard** — Color-coded tables, trend arrows, intensity bars, allocation charts
- **SQLite persistence** — All trades, portfolio state, and recommendation history saved

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the agent
python main.py
```

## Usage

The agent presents an interactive menu:

1. **Scan markets** — Fetch live data, run 10 indicators, get scored recommendations
2. **View portfolio** — Cash, total value, P&L, win rate, allocation bar
3. **View positions** — Open trades with live unrealized P&L (fetches current prices)
4. **View trade history** — Closed trades with performance stats (best/worst, avg win/loss, profit factor)
5. **Close a position** — Manually exit a trade at current market price
6. **Check stops** — Auto-close positions that hit stop-loss or take-profit
7. **Indicator detail** — Deep dive into all 10 indicators for any symbol with intensity bars, impact scores, and category summary
8. **Recommendation history** — Past recommendations with approved/rejected status and approval rate

Each recommendation shows the signal (BUY/SELL), confidence %, entry price, stop/target levels, position size, and indicator vote breakdown. You approve or reject each one before any trade is executed.

## Technical Indicators

| # | Indicator | Category | What it measures |
|---|---|---|---|
| 1 | RSI (14) | Momentum | Overbought/oversold with intensity scaling |
| 2 | MACD | Momentum | Trend momentum via signal line divergence |
| 3 | Stochastic | Momentum | Overbought/oversold + %K/%D crossovers |
| 4 | SMA Cross (20/50) | Trend | Golden cross / death cross detection |
| 5 | ADX + DI | Trend | Trend strength and direction |
| 6 | EMA Cross (12/26) | Trend | Fast trend signal with crossover detection |
| 7 | Volume | Volume | Volume spikes confirming price moves |
| 8 | OBV | Volume | Accumulation vs distribution flow |
| 9 | Bollinger Bands | Volatility | Price at extremes of volatility envelope |
| 10 | ATR | Volatility | Volatility expansion as breakout signal |

Confidence scoring uses weighted intensity (not simple vote counting): each indicator's impact = direction x intensity x weight. Cross-category agreement (e.g., trend + momentum + volume all bearish) boosts confidence up to 50%.

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

## Default Watchlist (27 assets)

- **Stocks** (9): AAPL, MSFT, TSLA, GOOGL, AMZN, NVDA, META, AMD, JPM
- **Crypto** (5): BTC/USDT, ETH/USDT, SOL/USDT, XRP/USDT, DOGE/USDT
- **Forex** (4): EUR/USD, GBP/USD, USD/JPY, AUD/USD
- **Commodities** (5): Gold (GC=F), Silver (SI=F), Crude Oil (CL=F), Natural Gas (NG=F), Copper (HG=F)
- **Indices** (4): S&P 500 (^GSPC), Dow Jones (^DJI), Nasdaq (^IXIC), Russell 2000 (^RUT)

## Project Structure

```
market_agent/
├── main.py                  # Entry point, CLI menu
├── config.py                # Settings and preferences
├── data/
│   ├── fetcher.py           # Market data fetching (5 market types)
│   └── models.py            # Data models (Asset, Trade, etc.)
├── analysis/
│   ├── technical.py         # 10 technical indicators + scoring engine
│   └── ai_analyst.py        # Claude API analysis
├── strategy/
│   ├── signals.py           # Signal generation (technical + AI)
│   └── risk.py              # Risk management, position sizing
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
