"""AI Market Agent — entry point and main loop."""

import csv
import json
import sys
import time
from datetime import datetime
from pathlib import Path

# Add project root to path so imports work
sys.path.insert(0, str(Path(__file__).parent))

from analysis.technical import analyze as technical_analyze
from data.fetcher import fetch_all_watchlist, fetch_asset, detect_asset_type
from data.models import Asset, AssetType, MarketData, OHLCV
from storage.database import Database
from strategy.signals import scan_and_recommend
from trading.executor import Executor
from trading.portfolio import Portfolio
from ui.dashboard import (
    console,
    prompt_approval,
    show_alerts,
    show_asset_comparison,
    show_backtest_results,
    show_banner,
    show_closed_trades_for_selection,
    show_export_menu,
    show_indicator_detail,
    show_market_overview,
    show_menu,
    show_multi_timeframe,
    show_performance_stats,
    show_portfolio,
    show_positions,
    show_recommendation_history,
    show_recommendations,
    show_trade_history,
    show_triggered_alerts,
    show_watchlist,
    show_watchlist_manager,
)
from config import settings

# Path for custom watchlist persistence
CUSTOM_WATCHLIST_PATH = Path(__file__).parent / "custom_watchlist.json"


def _get_watchlist() -> list[str]:
    """Get current watchlist (custom if exists, otherwise default)."""
    if CUSTOM_WATCHLIST_PATH.exists():
        return json.loads(CUSTOM_WATCHLIST_PATH.read_text())
    return settings.all_watchlist


def _save_watchlist(symbols: list[str]):
    """Save custom watchlist."""
    CUSTOM_WATCHLIST_PATH.write_text(json.dumps(symbols, indent=2))


def _fetch_watchlist() -> list[MarketData]:
    """Fetch data for current watchlist."""
    results = []
    for symbol in _get_watchlist():
        try:
            data = fetch_asset(symbol)
            results.append(data)
        except Exception as e:
            console.print(f"  [dim]Warning: Failed to fetch {symbol}: {e}[/dim]")
    return results


# ---------------------------------------------------------------------------
# 1. Scan markets
# ---------------------------------------------------------------------------

def scan_markets(executor: Executor):
    console.print("[bold blue]Scanning markets...[/bold blue]")
    console.print()

    market_data = _fetch_watchlist()
    if not market_data:
        console.print("[red]Failed to fetch any market data.[/red]")
        return

    show_watchlist(market_data)
    console.print("[bold blue]Running analysis...[/bold blue]")
    console.print()

    recommendations = scan_and_recommend(market_data)
    show_recommendations(recommendations)

    if not recommendations:
        return

    for rec in recommendations:
        approved = prompt_approval(rec)
        if approved:
            trade = executor.execute(rec)
            if trade:
                console.print(f"  [green]Trade executed: {trade.signal.value} {trade.symbol} "
                            f"x{trade.quantity:.4f} @ ${trade.entry_price:,.2f}[/green]")
            else:
                console.print("  [red]Trade failed risk checks.[/red]")
        else:
            executor.portfolio.reject_recommendation(rec)
            console.print("  [dim]Skipped.[/dim]")
        console.print()


# ---------------------------------------------------------------------------
# 2-4. Portfolio, positions, history
# ---------------------------------------------------------------------------

def view_portfolio(portfolio: Portfolio):
    portfolio.refresh()
    show_portfolio(portfolio.state)


def view_positions_live(portfolio: Portfolio):
    portfolio.refresh()
    positions = portfolio.state.positions
    if not positions:
        console.print("[dim]No open positions.[/dim]")
        console.print()
        return

    console.print("[bold blue]Fetching live prices...[/bold blue]")
    live_prices = {}
    for trade in positions:
        try:
            md = fetch_asset(trade.symbol)
            live_prices[trade.symbol] = md.asset.current_price
        except Exception:
            pass
    show_positions(positions, live_prices)


def view_history(db: Database):
    trades = db.get_closed_trades()
    show_trade_history(trades)
    show_performance_stats(trades)


# ---------------------------------------------------------------------------
# 5-6. Close position, check stops
# ---------------------------------------------------------------------------

def close_position(executor: Executor):
    executor.portfolio.refresh()
    positions = executor.portfolio.state.positions
    trade_id = show_closed_trades_for_selection(positions)
    if trade_id is None:
        return

    trade = next((t for t in positions if t.id == trade_id), None)
    if trade is None:
        console.print("[red]Trade not found.[/red]")
        return

    try:
        md = fetch_asset(trade.symbol)
        current_price = md.asset.current_price
    except Exception:
        price_input = console.input(f"  Enter exit price for {trade.symbol}: $").strip()
        try:
            current_price = float(price_input)
        except ValueError:
            console.print("[red]Invalid price.[/red]")
            return

    closed = executor.close_position(trade, current_price)
    pnl_color = "green" if closed.pnl >= 0 else "red"
    console.print(
        f"  [{pnl_color}]Closed {trade.symbol}: P&L ${closed.pnl:+,.2f} ({closed.pnl_pct:+.2f}%)[/{pnl_color}]"
    )


def check_stops(executor: Executor):
    executor.portfolio.refresh()
    positions = executor.portfolio.state.positions
    if not positions:
        console.print("[dim]No open positions.[/dim]")
        return

    console.print("[bold blue]Checking stop-loss / take-profit levels...[/bold blue]")
    prices = {}
    for trade in positions:
        try:
            md = fetch_asset(trade.symbol)
            prices[trade.symbol] = md.asset.current_price
            console.print(f"  {trade.symbol}: ${md.asset.current_price:,.2f}")
        except Exception as e:
            console.print(f"  {trade.symbol}: [red]fetch failed ({e})[/red]")

    closed = executor.check_stops(prices)
    if closed:
        for t in closed:
            color = "green" if t.pnl >= 0 else "red"
            reason = "take-profit" if t.pnl >= 0 else "stop-loss"
            console.print(
                f"  [{color}]{reason.upper()} triggered: {t.symbol} "
                f"P&L ${t.pnl:+,.2f} ({t.pnl_pct:+.2f}%)[/{color}]"
            )
    else:
        console.print("  [dim]No stops triggered.[/dim]")
    console.print()


# ---------------------------------------------------------------------------
# 7. Indicator detail
# ---------------------------------------------------------------------------

def indicator_detail():
    symbol = console.input("[bold]Enter symbol (e.g. AAPL, BTC/USDT): [/bold]").strip()
    if not symbol:
        return
    console.print(f"[bold blue]Analyzing {symbol}...[/bold blue]")
    try:
        md = fetch_asset(symbol)
        summary = technical_analyze(md)
        show_indicator_detail(md, summary)
    except Exception as e:
        console.print(f"[red]Failed to analyze {symbol}: {e}[/red]")


# ---------------------------------------------------------------------------
# 8. Recommendation history
# ---------------------------------------------------------------------------

def view_recommendation_history(db: Database):
    history = db.get_recommendation_history(limit=30)
    show_recommendation_history(history)


# ---------------------------------------------------------------------------
# 9. Market overview
# ---------------------------------------------------------------------------

def market_overview():
    console.print("[bold blue]Scanning all markets for sentiment...[/bold blue]")
    console.print()

    market_data = _fetch_watchlist()
    summaries = []
    for md in market_data:
        s = technical_analyze(md)
        summaries.append((md.asset.symbol, md.asset.asset_type.value, s.overall_signal.value, s.overall_score))

    show_market_overview(summaries)


# ---------------------------------------------------------------------------
# 10. Watchlist manager
# ---------------------------------------------------------------------------

def watchlist_manager():
    while True:
        current = _get_watchlist()
        show_watchlist_manager(current)
        choice = console.input("[bold]> [/bold]").strip().lower()

        if choice == "a":
            symbol = console.input("  Enter symbol to add: ").strip().upper()
            if not symbol:
                continue
            if symbol in current:
                console.print(f"  [yellow]{symbol} already in watchlist.[/yellow]")
                continue
            console.print(f"  [dim]Testing {symbol}...[/dim]")
            try:
                md = fetch_asset(symbol)
                if md.asset.current_price > 0:
                    current.append(symbol)
                    _save_watchlist(current)
                    console.print(f"  [green]Added {symbol} (${md.asset.current_price:,.2f})[/green]")
                else:
                    console.print(f"  [red]No price data for {symbol}[/red]")
            except Exception as e:
                console.print(f"  [red]Failed: {e}[/red]")

        elif choice == "r":
            symbol = console.input("  Enter symbol to remove: ").strip().upper()
            if symbol in current:
                current.remove(symbol)
                _save_watchlist(current)
                console.print(f"  [green]Removed {symbol}[/green]")
            else:
                console.print(f"  [red]{symbol} not in watchlist.[/red]")

        elif choice == "l":
            for i, sym in enumerate(current, 1):
                atype = detect_asset_type(sym).value
                console.print(f"  {i:3}. {sym:12} ({atype})")
            console.print()

        elif choice == "c":
            break
        else:
            console.print("[red]Invalid choice.[/red]")
        console.print()


# ---------------------------------------------------------------------------
# 11. Price alerts
# ---------------------------------------------------------------------------

def price_alerts(db: Database):
    alerts = db.get_active_alerts()
    show_alerts(alerts)

    menu_text = "[a] Add alert  [d] Delete alert  [k] Check now  [c] Back"
    console.print(f"  [dim]{menu_text}[/dim]")
    choice = console.input("[bold]> [/bold]").strip().lower()

    if choice == "a":
        symbol = console.input("  Symbol: ").strip().upper()
        cond = console.input("  Condition (above/below): ").strip().lower()
        if cond not in ("above", "below"):
            console.print("[red]Must be 'above' or 'below'.[/red]")
            return
        try:
            price = float(console.input("  Target price: $").strip())
        except ValueError:
            console.print("[red]Invalid price.[/red]")
            return
        db.add_alert(symbol, cond, price)
        console.print(f"  [green]Alert set: {symbol} {cond} ${price:,.2f}[/green]")

    elif choice == "d":
        if not alerts:
            return
        try:
            idx = int(console.input("  Alert # to delete: ").strip()) - 1
            if 0 <= idx < len(alerts):
                db.delete_alert(alerts[idx]["id"])
                console.print("  [green]Alert deleted.[/green]")
        except (ValueError, IndexError):
            console.print("[red]Invalid selection.[/red]")

    elif choice == "k":
        _check_alerts(db)

    console.print()


def _check_alerts(db: Database):
    """Check all active alerts against current prices."""
    alerts = db.get_active_alerts()
    if not alerts:
        console.print("  [dim]No active alerts.[/dim]")
        return

    triggered = []
    for alert in alerts:
        try:
            md = fetch_asset(alert["symbol"])
            price = md.asset.current_price
            hit = (alert["condition"] == "above" and price >= alert["target_price"]) or \
                  (alert["condition"] == "below" and price <= alert["target_price"])
            if hit:
                db.trigger_alert(alert["id"])
                triggered.append((alert, price))
        except Exception:
            pass

    if triggered:
        show_triggered_alerts(triggered)
    else:
        console.print("  [dim]No alerts triggered.[/dim]")


# ---------------------------------------------------------------------------
# 12. Compare two assets
# ---------------------------------------------------------------------------

def compare_assets():
    sym1 = console.input("[bold]First symbol: [/bold]").strip().upper()
    sym2 = console.input("[bold]Second symbol: [/bold]").strip().upper()
    if not sym1 or not sym2:
        return

    console.print(f"[bold blue]Comparing {sym1} vs {sym2}...[/bold blue]")
    try:
        md1 = fetch_asset(sym1)
        md2 = fetch_asset(sym2)
        s1 = technical_analyze(md1)
        s2 = technical_analyze(md2)
        show_asset_comparison(md1, s1, md2, s2)
    except Exception as e:
        console.print(f"[red]Failed: {e}[/red]")


# ---------------------------------------------------------------------------
# 13. Multi-timeframe analysis
# ---------------------------------------------------------------------------

def multi_timeframe():
    symbol = console.input("[bold]Enter symbol: [/bold]").strip().upper()
    if not symbol:
        return

    console.print(f"[bold blue]Fetching daily + weekly data for {symbol}...[/bold blue]")
    try:
        # Daily: 90 days
        md_daily = fetch_asset(symbol, days=90)
        summary_daily = technical_analyze(md_daily)

        # Weekly: simulate by resampling daily data to weekly candles
        md_long = fetch_asset(symbol, days=365)
        if len(md_long.candles) >= 60:
            import pandas as pd
            from analysis.technical import candles_to_df

            df = candles_to_df(md_long.candles)
            weekly = df.resample("W").agg({
                "open": "first", "high": "max", "low": "min",
                "close": "last", "volume": "sum",
            }).dropna()

            weekly_candles = [
                OHLCV(
                    timestamp=idx.to_pydatetime() if hasattr(idx, "to_pydatetime") else datetime.now(),
                    open=float(row["open"]), high=float(row["high"]),
                    low=float(row["low"]), close=float(row["close"]),
                    volume=float(row["volume"]),
                )
                for idx, row in weekly.iterrows()
            ]
            weekly_md = MarketData(asset=md_long.asset, candles=weekly_candles)
            summary_weekly = technical_analyze(weekly_md)
            show_multi_timeframe(symbol, summary_daily, summary_weekly)
        else:
            console.print("[red]Not enough data for weekly analysis.[/red]")
    except Exception as e:
        console.print(f"[red]Failed: {e}[/red]")


# ---------------------------------------------------------------------------
# 14. Backtest
# ---------------------------------------------------------------------------

def run_backtest():
    symbol = console.input("[bold]Symbol to backtest: [/bold]").strip().upper()
    if not symbol:
        return

    days_input = console.input("[bold]Period in days [365]: [/bold]").strip()
    days = int(days_input) if days_input else 365

    hold_input = console.input("[bold]Hold period in days [5]: [/bold]").strip()
    hold = int(hold_input) if hold_input else 5

    console.print(f"[bold blue]Running {days}-day backtest on {symbol} (hold={hold}d)...[/bold blue]")
    console.print("[dim]This may take a moment...[/dim]")

    try:
        from analysis.backtest import backtest
        result = backtest(symbol, days=days, hold_days=hold)
        show_backtest_results(result)
    except Exception as e:
        console.print(f"[red]Backtest failed: {e}[/red]")


# ---------------------------------------------------------------------------
# 15. Export to CSV
# ---------------------------------------------------------------------------

def export_data(db: Database):
    show_export_menu()
    choice = console.input("[bold]> [/bold]").strip().lower()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if choice in ("a", "t"):
        trades = db.get_all_trades()
        if trades:
            path = f"trades_{timestamp}.csv"
            with open(path, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["id", "symbol", "type", "signal", "entry", "exit", "qty",
                           "value", "stop", "target", "status", "pnl", "pnl_pct",
                           "confidence", "opened", "closed"])
                for t in trades:
                    w.writerow([t.id, t.symbol, t.asset_type.value, t.signal.value,
                               t.entry_price, t.exit_price, t.quantity, t.position_value,
                               t.stop_loss, t.take_profit, t.status.value, t.pnl,
                               t.pnl_pct, t.confidence, t.opened_at, t.closed_at])
            console.print(f"  [green]Trades exported to {path}[/green]")

    if choice in ("a", "r"):
        recs = db.get_recommendation_history(limit=500)
        if recs:
            path = f"recommendations_{timestamp}.csv"
            with open(path, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["symbol", "signal", "confidence", "price", "approved", "reasoning", "time"])
                for r in recs:
                    w.writerow([r["symbol"], r["signal"], r["confidence"],
                               r["entry_price"], r["approved"], r["reasoning"],
                               r["created_at"]])
            console.print(f"  [green]Recommendations exported to {path}[/green]")

    if choice == "a":
        state = db.load_portfolio()
        path = f"portfolio_{timestamp}.csv"
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["cash", "total_value", "total_pnl", "total_pnl_pct",
                        "win_count", "loss_count", "total_trades"])
            w.writerow([state.cash, state.total_value, state.total_pnl,
                       state.total_pnl_pct, state.win_count, state.loss_count,
                       state.total_trades])
        console.print(f"  [green]Portfolio exported to {path}[/green]")

    if choice == "c":
        return

    console.print()


# ---------------------------------------------------------------------------
# 16. Auto-scan mode
# ---------------------------------------------------------------------------

def auto_scan(executor: Executor, db: Database):
    interval_input = console.input("[bold]Scan interval in minutes [5]: [/bold]").strip()
    interval = int(interval_input) * 60 if interval_input else 300

    console.print(f"[bold blue]Auto-scan started (every {interval // 60}m). Press Ctrl+C to stop.[/bold blue]")
    console.print()

    try:
        while True:
            console.print(f"[dim]--- Scan at {datetime.now().strftime('%H:%M:%S')} ---[/dim]")

            # Fetch and analyze
            market_data = _fetch_watchlist()
            if market_data:
                show_watchlist(market_data)

                recommendations = scan_and_recommend(market_data)
                show_recommendations(recommendations)

                # Check price alerts
                _check_alerts(db)

                # Check stops on open positions
                executor.portfolio.refresh()
                if executor.portfolio.state.positions:
                    prices = {md.asset.symbol: md.asset.current_price for md in market_data}
                    closed = executor.check_stops(prices)
                    for t in closed:
                        color = "green" if t.pnl >= 0 else "red"
                        console.print(
                            f"  [{color}]AUTO: Stop triggered on {t.symbol} "
                            f"P&L ${t.pnl:+,.2f}[/{color}]"
                        )

                # Present recommendations for approval
                for rec in recommendations:
                    approved = prompt_approval(rec)
                    if approved:
                        trade = executor.execute(rec)
                        if trade:
                            console.print(f"  [green]Trade executed: {trade.signal.value} {trade.symbol} "
                                        f"x{trade.quantity:.4f} @ ${trade.entry_price:,.2f}[/green]")
                    else:
                        executor.portfolio.reject_recommendation(rec)
                        console.print("  [dim]Skipped.[/dim]")
                    console.print()

            console.print(f"[dim]Next scan in {interval // 60} minutes...[/dim]")
            console.print()
            time.sleep(interval)
    except KeyboardInterrupt:
        console.print("\n[yellow]Auto-scan stopped.[/yellow]")
        console.print()


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def main():
    db = Database()
    portfolio = Portfolio(db)
    executor = Executor(portfolio)

    show_banner()

    if settings.has_claude:
        console.print("[green]Claude AI analysis: ENABLED[/green]")
    else:
        console.print("[yellow]Claude AI analysis: DISABLED (set MARKET_AGENT_ANTHROPIC_API_KEY to enable)[/yellow]")
    console.print()

    try:
        while True:
            show_menu()
            choice = console.input("[bold]> [/bold]").strip().lower()

            if choice == "1":
                scan_markets(executor)
            elif choice == "2":
                view_portfolio(portfolio)
            elif choice == "3":
                view_positions_live(portfolio)
            elif choice == "4":
                view_history(db)
            elif choice == "5":
                close_position(executor)
            elif choice == "6":
                check_stops(executor)
            elif choice == "7":
                indicator_detail()
            elif choice == "8":
                view_recommendation_history(db)
            elif choice == "9":
                market_overview()
            elif choice == "10":
                watchlist_manager()
            elif choice == "11":
                price_alerts(db)
            elif choice == "12":
                compare_assets()
            elif choice == "13":
                multi_timeframe()
            elif choice == "14":
                run_backtest()
            elif choice == "15":
                export_data(db)
            elif choice == "16":
                auto_scan(executor, db)
            elif choice in ("q", "quit", "exit"):
                console.print("[dim]Goodbye.[/dim]")
                break
            else:
                console.print("[red]Invalid choice.[/red]")
                console.print()
    except KeyboardInterrupt:
        console.print("\n[dim]Interrupted. Goodbye.[/dim]")
    finally:
        db.close()


if __name__ == "__main__":
    main()
