"""AI Market Agent — entry point and main loop."""

import sys
from pathlib import Path

# Add project root to path so imports work
sys.path.insert(0, str(Path(__file__).parent))

from data.fetcher import fetch_all_watchlist, fetch_asset
from storage.database import Database
from strategy.signals import scan_and_recommend
from trading.executor import Executor
from trading.portfolio import Portfolio
from ui.dashboard import (
    console,
    prompt_approval,
    show_banner,
    show_closed_trades_for_selection,
    show_menu,
    show_portfolio,
    show_positions,
    show_recommendations,
    show_trade_history,
    show_watchlist,
)
from config import settings


def scan_markets(executor: Executor):
    """Scan all watchlist assets and present recommendations."""
    console.print("[bold blue]Scanning markets...[/bold blue]")
    console.print()

    market_data = fetch_all_watchlist()
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

    # Present each recommendation for approval
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


def view_portfolio(portfolio: Portfolio):
    """Show portfolio summary."""
    portfolio.refresh()
    show_portfolio(portfolio.state)


def view_positions(portfolio: Portfolio):
    """Show open positions."""
    portfolio.refresh()
    show_positions(portfolio.state.positions)


def view_history(db: Database):
    """Show closed trade history."""
    trades = db.get_closed_trades()
    show_trade_history(trades)


def close_position(executor: Executor):
    """Let user close an open position."""
    executor.portfolio.refresh()
    positions = executor.portfolio.state.positions

    trade_id = show_closed_trades_for_selection(positions)
    if trade_id is None:
        return

    trade = next((t for t in positions if t.id == trade_id), None)
    if trade is None:
        console.print("[red]Trade not found.[/red]")
        return

    # Fetch current price
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
    """Check all open positions against stop-loss/take-profit."""
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


def main():
    """Main application loop."""
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
                view_positions(portfolio)
            elif choice == "4":
                view_history(db)
            elif choice == "5":
                close_position(executor)
            elif choice == "6":
                check_stops(executor)
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
