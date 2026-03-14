"""Rich CLI dashboard for the market agent."""

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from data.models import MarketData, PortfolioState, Recommendation, SignalType, Trade


console = Console()


def signal_style(signal: SignalType) -> str:
    if signal == SignalType.BUY:
        return "bold green"
    elif signal == SignalType.SELL:
        return "bold red"
    return "dim"


def pnl_style(value: float) -> str:
    if value > 0:
        return "green"
    elif value < 0:
        return "red"
    return "dim"


def show_banner():
    """Show the application banner."""
    banner = Text()
    banner.append("  AI Market Agent  ", style="bold white on blue")
    banner.append("  Paper Trading Mode  ", style="bold white on dark_green")
    console.print()
    console.print(Panel(banner, title="[bold]Market Agent[/bold]", border_style="blue"))
    console.print()


def show_watchlist(market_data_list: list[MarketData]):
    """Display the current watchlist with prices."""
    table = Table(title="Watchlist", border_style="blue", show_lines=False)
    table.add_column("Symbol", style="bold cyan", min_width=12)
    table.add_column("Type", style="dim")
    table.add_column("Price", justify="right")

    for md in market_data_list:
        price = f"${md.asset.current_price:,.2f}" if md.asset.current_price else "N/A"
        table.add_row(md.asset.symbol, md.asset.asset_type.value, price)

    console.print(table)
    console.print()


def show_recommendations(recs: list[Recommendation]):
    """Display trade recommendations."""
    if not recs:
        console.print("[dim]No recommendations at this time.[/dim]")
        console.print()
        return

    table = Table(title="Recommendations", border_style="yellow", show_lines=True)
    table.add_column("#", style="dim", width=3)
    table.add_column("Symbol", style="bold cyan", min_width=12)
    table.add_column("Signal", min_width=6)
    table.add_column("Confidence", justify="right")
    table.add_column("Entry", justify="right")
    table.add_column("Stop Loss", justify="right")
    table.add_column("Take Profit", justify="right")
    table.add_column("Size", justify="right")
    table.add_column("Reasoning", max_width=40)

    for i, rec in enumerate(recs, 1):
        style = signal_style(rec.signal)
        reasoning = rec.ai_reasoning[:80] + "..." if len(rec.ai_reasoning) > 80 else rec.ai_reasoning
        table.add_row(
            str(i),
            rec.asset.symbol,
            Text(rec.signal.value, style=style),
            Text(rec.confidence_pct, style=style),
            f"${rec.entry_price:,.2f}",
            f"${rec.stop_loss:,.2f}",
            f"${rec.take_profit:,.2f}",
            f"${rec.position_size:,.2f}",
            reasoning,
        )

    console.print(table)
    console.print()


def show_portfolio(state: PortfolioState):
    """Display portfolio summary."""
    table = Table(title="Portfolio", border_style="green")
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")

    pnl_s = pnl_style(state.total_pnl)
    table.add_row("Cash", f"${state.cash:,.2f}")
    table.add_row("Positions Value", f"${state.positions_value:,.2f}")
    table.add_row("Total Value", f"[bold]${state.total_value:,.2f}[/bold]")
    table.add_row("P&L", Text(f"${state.total_pnl:+,.2f} ({state.total_pnl_pct:+.2f}%)", style=pnl_s))
    table.add_row("Win Rate", f"{state.win_rate:.0%} ({state.win_count}W / {state.loss_count}L)")
    table.add_row("Total Trades", str(state.total_trades))

    console.print(table)
    console.print()


def show_positions(positions: list[Trade]):
    """Display open positions."""
    if not positions:
        console.print("[dim]No open positions.[/dim]")
        console.print()
        return

    table = Table(title="Open Positions", border_style="magenta")
    table.add_column("Symbol", style="bold cyan")
    table.add_column("Side", min_width=5)
    table.add_column("Entry", justify="right")
    table.add_column("Qty", justify="right")
    table.add_column("Value", justify="right")
    table.add_column("Stop", justify="right")
    table.add_column("Target", justify="right")
    table.add_column("Opened", style="dim")

    for t in positions:
        style = signal_style(t.signal)
        table.add_row(
            t.symbol,
            Text(t.signal.value, style=style),
            f"${t.entry_price:,.2f}",
            f"{t.quantity:.4f}",
            f"${t.position_value:,.2f}",
            f"${t.stop_loss:,.2f}",
            f"${t.take_profit:,.2f}",
            t.opened_at.strftime("%m/%d %H:%M"),
        )

    console.print(table)
    console.print()


def show_trade_history(trades: list[Trade]):
    """Display closed trade history."""
    if not trades:
        console.print("[dim]No trade history.[/dim]")
        console.print()
        return

    table = Table(title="Trade History", border_style="cyan")
    table.add_column("Symbol", style="bold")
    table.add_column("Side")
    table.add_column("Entry", justify="right")
    table.add_column("Exit", justify="right")
    table.add_column("P&L", justify="right")
    table.add_column("P&L %", justify="right")
    table.add_column("Closed", style="dim")

    for t in trades:
        style = pnl_style(t.pnl)
        exit_p = f"${t.exit_price:,.2f}" if t.exit_price else "—"
        closed = t.closed_at.strftime("%m/%d %H:%M") if t.closed_at else "—"
        table.add_row(
            t.symbol,
            Text(t.signal.value, style=signal_style(t.signal)),
            f"${t.entry_price:,.2f}",
            exit_p,
            Text(f"${t.pnl:+,.2f}", style=style),
            Text(f"{t.pnl_pct:+.2f}%", style=style),
            closed,
        )

    console.print(table)
    console.print()


def show_menu():
    """Display the main menu."""
    menu = Table(show_header=False, border_style="blue", box=None, padding=(0, 2))
    menu.add_column(style="bold cyan")
    menu.add_column()
    menu.add_row("[1]", "Scan markets & get recommendations")
    menu.add_row("[2]", "View portfolio")
    menu.add_row("[3]", "View open positions")
    menu.add_row("[4]", "View trade history")
    menu.add_row("[5]", "Close a position")
    menu.add_row("[6]", "Check stop-loss / take-profit")
    menu.add_row("[q]", "Quit")
    console.print(Panel(menu, title="[bold]Menu[/bold]", border_style="blue"))
    console.print()


def prompt_approval(rec: Recommendation) -> bool:
    """Ask user to approve or reject a recommendation."""
    style = signal_style(rec.signal)
    console.print(
        f"  [bold]{rec.signal.value}[/bold] [{style}]{rec.asset.symbol}[/{style}] "
        f"@ ${rec.entry_price:,.2f}  |  "
        f"Confidence: [{style}]{rec.confidence_pct}[/{style}]  |  "
        f"Size: ${rec.position_size:,.2f}"
    )
    if rec.ai_reasoning:
        console.print(f"  Reason: [dim]{rec.ai_reasoning}[/dim]")

    response = console.input("  Approve? [y/n]: ").strip().lower()
    return response in ("y", "yes")


def show_closed_trades_for_selection(positions: list[Trade]) -> int | None:
    """Show positions and let user select one to close. Returns trade ID or None."""
    if not positions:
        console.print("[dim]No open positions to close.[/dim]")
        return None

    show_positions(positions)
    choice = console.input("Enter position # to close (or 'c' to cancel): ").strip()
    if choice.lower() == "c":
        return None

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(positions):
            return positions[idx].id
    except ValueError:
        pass

    console.print("[red]Invalid selection.[/red]")
    return None
