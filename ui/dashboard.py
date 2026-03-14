"""Rich CLI dashboard for the market agent."""

from datetime import datetime

from rich.bar import Bar
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from data.models import (
    IndicatorCategory, MarketData, PortfolioState, Recommendation, SignalType,
    TechnicalSummary, Trade,
)


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


def category_style(cat: IndicatorCategory) -> str:
    return {
        IndicatorCategory.TREND: "blue",
        IndicatorCategory.MOMENTUM: "magenta",
        IndicatorCategory.VOLUME: "cyan",
        IndicatorCategory.VOLATILITY: "yellow",
    }.get(cat, "white")


def intensity_bar(intensity: float, signal: SignalType) -> Text:
    """Render a visual intensity bar like [||||      ]."""
    width = 10
    filled = round(intensity * width)
    color = "green" if signal == SignalType.BUY else "red" if signal == SignalType.SELL else "dim"
    bar = "|" * filled + " " * (width - filled)
    return Text(f"[{bar}]", style=color)


# ---------------------------------------------------------------------------
# Banner & Menu
# ---------------------------------------------------------------------------

def show_banner():
    """Show the application banner."""
    now = datetime.now()
    banner = Text()
    banner.append("  AI Market Agent  ", style="bold white on blue")
    banner.append("  Paper Trading Mode  ", style="bold white on dark_green")
    banner.append(f"  {now.strftime('%Y-%m-%d %H:%M')}  ", style="dim")
    console.print()
    console.print(Panel(banner, title="[bold]Market Agent[/bold]", border_style="blue"))
    console.print()


def show_menu():
    """Display the main menu."""
    menu = Table(show_header=False, border_style="blue", box=None, padding=(0, 2))
    menu.add_column(style="bold cyan")
    menu.add_column()
    menu.add_row("[1]", "Scan markets & get recommendations")
    menu.add_row("[2]", "View portfolio & allocation")
    menu.add_row("[3]", "View open positions (with live P&L)")
    menu.add_row("[4]", "View trade history & performance stats")
    menu.add_row("[5]", "Close a position")
    menu.add_row("[6]", "Check stop-loss / take-profit")
    menu.add_row("[7]", "Indicator detail (analyze single asset)")
    menu.add_row("[8]", "Recommendation history")
    menu.add_row("[9]", "Market overview (sentiment summary)")
    menu.add_row("[10]", "Watchlist manager")
    menu.add_row("[11]", "Price alerts")
    menu.add_row("[12]", "Compare two assets")
    menu.add_row("[13]", "Multi-timeframe analysis")
    menu.add_row("[14]", "Backtest strategy")
    menu.add_row("[15]", "Export data to CSV")
    menu.add_row("[16]", "Auto-scan mode")
    menu.add_row("[17]", "Price chart")
    menu.add_row("[18]", "Screener")
    menu.add_row("[19]", "Correlation matrix")
    menu.add_row("[20]", "Support / resistance levels")
    menu.add_row("[21]", "Portfolio risk analysis")
    menu.add_row("[22]", "Trade journal")
    menu.add_row("[23]", "Earnings calendar")
    menu.add_row("[24]", "News headlines")
    menu.add_row("[q]", "Quit")
    console.print(Panel(menu, title="[bold]Menu[/bold]", border_style="blue"))
    console.print()


# ---------------------------------------------------------------------------
# Watchlist — now with daily % change
# ---------------------------------------------------------------------------

def show_watchlist(market_data_list: list[MarketData]):
    """Display the current watchlist with prices and daily change."""
    table = Table(title="Watchlist", border_style="blue", show_lines=False)
    table.add_column("Symbol", style="bold cyan", min_width=12)
    table.add_column("Type", style="dim")
    table.add_column("Price", justify="right")
    table.add_column("Daily Chg", justify="right")
    table.add_column("Trend", min_width=7)

    for md in market_data_list:
        price = md.asset.current_price
        price_str = f"${price:,.2f}" if price else "N/A"

        # Calculate daily change from candles
        if len(md.candles) >= 2 and price:
            prev_close = md.candles[-2].close
            change = ((price - prev_close) / prev_close) * 100
            change_str = f"{change:+.2f}%"
            style = "green" if change > 0 else "red" if change < 0 else "dim"
            change_text = Text(change_str, style=style)

            # Mini trend from last 5 candles
            recent = md.candles[-5:] if len(md.candles) >= 5 else md.candles
            trend = ""
            for i in range(1, len(recent)):
                trend += "[green]^[/green]" if recent[i].close > recent[i - 1].close else "[red]v[/red]"
        else:
            change_text = Text("—", style="dim")
            trend = ""

        table.add_row(md.asset.symbol, md.asset.asset_type.value, price_str, change_text, trend)

    console.print(table)
    console.print()


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------

def show_recommendations(recs: list[Recommendation]):
    """Display trade recommendations."""
    if not recs:
        console.print("[dim]No recommendations at this time.[/dim]")
        console.print()
        return

    table = Table(title="Recommendations", border_style="yellow", show_lines=True)
    table.add_column("#", style="dim", width=3)
    table.add_column("Symbol", style="bold cyan", min_width=10)
    table.add_column("Signal", min_width=5)
    table.add_column("Conf", justify="right", min_width=5)
    table.add_column("Entry", justify="right")
    table.add_column("Stop", justify="right")
    table.add_column("Target", justify="right")
    table.add_column("Size", justify="right")
    table.add_column("Indicators", min_width=10)

    for i, rec in enumerate(recs, 1):
        style = signal_style(rec.signal)

        # Compact indicator summary: 3B/2S/5H
        if rec.technical_summary:
            ts = rec.technical_summary
            ind_summary = f"[green]{ts.buy_count}B[/green] [red]{ts.sell_count}S[/red] [dim]{len(ts.indicators) - ts.buy_count - ts.sell_count}H[/dim]"
        else:
            ind_summary = "—"

        table.add_row(
            str(i),
            rec.asset.symbol,
            Text(rec.signal.value, style=style),
            Text(rec.confidence_pct, style=style),
            f"${rec.entry_price:,.2f}",
            f"${rec.stop_loss:,.2f}",
            f"${rec.take_profit:,.2f}",
            f"${rec.position_size:,.2f}",
            ind_summary,
        )

    console.print(table)
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


# ---------------------------------------------------------------------------
# Portfolio — now with allocation bar
# ---------------------------------------------------------------------------

def show_portfolio(state: PortfolioState):
    """Display portfolio summary with allocation breakdown."""
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

    # Allocation bar
    if state.total_value > 0:
        cash_pct = state.cash / state.total_value
        pos_pct = state.positions_value / state.total_value
        bar_width = 40

        cash_bars = round(cash_pct * bar_width)
        pos_bars = bar_width - cash_bars

        alloc = Text()
        alloc.append("  Allocation: [")
        alloc.append("$" * pos_bars, style="bold yellow")
        alloc.append("." * cash_bars, style="dim green")
        alloc.append("]  ")
        alloc.append(f"Invested {pos_pct:.0%}", style="yellow")
        alloc.append(" | ", style="dim")
        alloc.append(f"Cash {cash_pct:.0%}", style="green")
        console.print(alloc)

    console.print()


# ---------------------------------------------------------------------------
# Positions — now with live P&L
# ---------------------------------------------------------------------------

def show_positions(positions: list[Trade], live_prices: dict[str, float] | None = None):
    """Display open positions with optional live P&L."""
    if not positions:
        console.print("[dim]No open positions.[/dim]")
        console.print()
        return

    has_live = live_prices and len(live_prices) > 0

    table = Table(title="Open Positions", border_style="magenta")
    table.add_column("Symbol", style="bold cyan")
    table.add_column("Side", min_width=5)
    table.add_column("Entry", justify="right")
    table.add_column("Qty", justify="right")
    if has_live:
        table.add_column("Now", justify="right")
        table.add_column("Unreal P&L", justify="right")
    table.add_column("Value", justify="right")
    table.add_column("Stop", justify="right")
    table.add_column("Target", justify="right")
    table.add_column("Opened", style="dim")

    for t in positions:
        style = signal_style(t.signal)
        row = [
            t.symbol,
            Text(t.signal.value, style=style),
            f"${t.entry_price:,.2f}",
            f"{t.quantity:.4f}",
        ]

        if has_live:
            current = live_prices.get(t.symbol)
            if current:
                row.append(f"${current:,.2f}")
                if t.signal == SignalType.BUY:
                    unreal = (current - t.entry_price) * t.quantity
                else:
                    unreal = (t.entry_price - current) * t.quantity
                unreal_pct = (unreal / t.position_value * 100) if t.position_value else 0
                ps = pnl_style(unreal)
                row.append(Text(f"${unreal:+,.2f} ({unreal_pct:+.1f}%)", style=ps))
            else:
                row.append("—")
                row.append("—")

        row.extend([
            f"${t.position_value:,.2f}",
            f"${t.stop_loss:,.2f}",
            f"${t.take_profit:,.2f}",
            t.opened_at.strftime("%m/%d %H:%M"),
        ])

        table.add_row(*row)

    console.print(table)
    console.print()


# ---------------------------------------------------------------------------
# Trade history — now with performance stats
# ---------------------------------------------------------------------------

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
    table.add_column("Conf", justify="right", style="dim")
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
            f"{t.confidence:.0%}",
            closed,
        )

    console.print(table)
    console.print()


def show_performance_stats(trades: list[Trade]):
    """Show performance statistics from closed trades."""
    if not trades:
        return

    total_pnl = sum(t.pnl for t in trades)
    wins = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl < 0]

    avg_pnl = total_pnl / len(trades) if trades else 0
    avg_win = sum(t.pnl for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t.pnl for t in losses) / len(losses) if losses else 0
    best = max(trades, key=lambda t: t.pnl)
    worst = min(trades, key=lambda t: t.pnl)

    gross_profit = sum(t.pnl for t in wins)
    gross_loss = abs(sum(t.pnl for t in losses))
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float("inf") if gross_profit > 0 else 0

    table = Table(title="Performance Stats", border_style="yellow")
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")

    table.add_row("Total Trades", str(len(trades)))
    table.add_row("Total P&L", Text(f"${total_pnl:+,.2f}", style=pnl_style(total_pnl)))
    table.add_row("Avg P&L / Trade", Text(f"${avg_pnl:+,.2f}", style=pnl_style(avg_pnl)))
    table.add_row("Avg Win", Text(f"${avg_win:+,.2f}", style="green") if wins else Text("—", style="dim"))
    table.add_row("Avg Loss", Text(f"${avg_loss:+,.2f}", style="red") if losses else Text("—", style="dim"))
    table.add_row("Best Trade", Text(f"{best.symbol} ${best.pnl:+,.2f}", style=pnl_style(best.pnl)))
    table.add_row("Worst Trade", Text(f"{worst.symbol} ${worst.pnl:+,.2f}", style=pnl_style(worst.pnl)))
    table.add_row("Profit Factor", f"{profit_factor:.2f}" if profit_factor != float("inf") else "INF")
    table.add_row("Win Rate", f"{len(wins)}/{len(trades)} ({len(wins)/len(trades):.0%})" if trades else "—")

    console.print(table)
    console.print()


# ---------------------------------------------------------------------------
# Indicator detail view
# ---------------------------------------------------------------------------

def show_indicator_detail(market_data: MarketData, summary: TechnicalSummary):
    """Show detailed indicator breakdown for a single asset."""
    asset = market_data.asset

    # Header
    console.print(Panel(
        f"[bold cyan]{asset.symbol}[/bold cyan] ({asset.asset_type.value})  "
        f"Price: [bold]${asset.current_price:,.2f}[/bold]  "
        f"Signal: [{signal_style(summary.overall_signal)}]{summary.overall_signal.value}[/{signal_style(summary.overall_signal)}]  "
        f"Score: {summary.overall_score:+.4f}  "
        f"Confidence: {abs(summary.overall_score)*100:.0f}%",
        title="[bold]Indicator Detail[/bold]",
        border_style="cyan",
    ))

    # Indicator table
    table = Table(border_style="cyan", show_lines=True)
    table.add_column("Indicator", style="bold", min_width=12)
    table.add_column("Category", min_width=10)
    table.add_column("Signal", min_width=5)
    table.add_column("Intensity", min_width=14)
    table.add_column("Weight", justify="right")
    table.add_column("Impact", justify="right")
    table.add_column("Description", max_width=50)

    for ind in summary.indicators:
        style = signal_style(ind.signal)
        cat_s = category_style(ind.category)

        # Impact = direction * intensity * weight
        direction = 1 if ind.signal == SignalType.BUY else (-1 if ind.signal == SignalType.SELL else 0)
        impact = direction * ind.intensity * ind.weight
        impact_style = pnl_style(impact)

        bar = intensity_bar(ind.intensity, ind.signal)

        table.add_row(
            ind.name,
            Text(ind.category.value, style=cat_s),
            Text(ind.signal.value, style=style),
            bar,
            f"{ind.weight:.1f}x",
            Text(f"{impact:+.3f}", style=impact_style),
            ind.description,
        )

    console.print(table)

    # Category summary
    cat_table = Table(title="Category Summary", border_style="dim", show_lines=False)
    cat_table.add_column("Category", style="bold")
    cat_table.add_column("Direction")
    cat_table.add_column("Avg Intensity", justify="right")

    direction_map = {SignalType.BUY: 1.0, SignalType.SELL: -1.0, SignalType.HOLD: 0.0}
    categories: dict[str, list[tuple[float, float]]] = {}
    for ind in summary.indicators:
        cat_name = ind.category.value
        d = direction_map[ind.signal]
        categories.setdefault(cat_name, []).append((d, ind.intensity))

    for cat_name, values in categories.items():
        weighted_dirs = [d * i for d, i in values]
        avg_dir = sum(weighted_dirs) / len(weighted_dirs)
        avg_int = sum(i for _, i in values) / len(values)

        if avg_dir > 0.1:
            dir_text = Text("BULLISH", style="green")
        elif avg_dir < -0.1:
            dir_text = Text("BEARISH", style="red")
        else:
            dir_text = Text("MIXED", style="dim")

        cat_table.add_row(cat_name.capitalize(), dir_text, f"{avg_int:.2f}")

    console.print(cat_table)
    console.print()


# ---------------------------------------------------------------------------
# Recommendation history
# ---------------------------------------------------------------------------

def show_recommendation_history(history: list[dict]):
    """Show past recommendations with approved/rejected status."""
    if not history:
        console.print("[dim]No recommendation history.[/dim]")
        console.print()
        return

    table = Table(title="Recommendation History", border_style="blue")
    table.add_column("Symbol", style="bold cyan")
    table.add_column("Signal")
    table.add_column("Conf", justify="right")
    table.add_column("Price", justify="right")
    table.add_column("Status")
    table.add_column("Time", style="dim")

    for rec in history:
        sig = SignalType(rec["signal"])
        style = signal_style(sig)
        approved = rec.get("approved", 0)
        status = Text("APPROVED", style="green") if approved else Text("REJECTED", style="red")
        conf = f"{rec['confidence']:.0%}"
        time_str = rec.get("created_at", "—")
        if isinstance(time_str, str) and len(time_str) > 16:
            time_str = time_str[:16]

        table.add_row(
            rec["symbol"],
            Text(sig.value, style=style),
            Text(conf, style=style),
            f"${rec['entry_price']:,.2f}",
            status,
            time_str,
        )

    console.print(table)

    # Summary stats
    total = len(history)
    approved_count = sum(1 for r in history if r.get("approved"))
    console.print(
        f"  [dim]Total: {total} | Approved: {approved_count} | "
        f"Rejected: {total - approved_count} | "
        f"Approval rate: {approved_count/total:.0%}[/dim]"
    )
    console.print()


# ---------------------------------------------------------------------------
# Close position selector
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Market overview — sentiment summary
# ---------------------------------------------------------------------------

def show_market_overview(summaries: list[tuple[str, str, str, float]]):
    """Show market sentiment overview.

    summaries: list of (symbol, asset_type, signal, score)
    """
    buy_count = sum(1 for _, _, s, _ in summaries if s == "BUY")
    sell_count = sum(1 for _, _, s, _ in summaries if s == "SELL")
    hold_count = sum(1 for _, _, s, _ in summaries if s == "HOLD")
    total = len(summaries)

    # Overall sentiment
    if buy_count > sell_count * 1.5:
        sentiment = Text("BULLISH", style="bold green")
    elif sell_count > buy_count * 1.5:
        sentiment = Text("BEARISH", style="bold red")
    else:
        sentiment = Text("MIXED", style="bold yellow")

    console.print(Panel(
        f"  Overall: {sentiment}  |  "
        f"[green]{buy_count} BUY[/green]  [red]{sell_count} SELL[/red]  [dim]{hold_count} HOLD[/dim]  "
        f"({total} assets scanned)",
        title="[bold]Market Sentiment[/bold]",
        border_style="yellow",
    ))

    # Per asset-type breakdown
    by_type: dict[str, list[tuple[str, str, float]]] = {}
    for sym, atype, sig, score in summaries:
        by_type.setdefault(atype, []).append((sym, sig, score))

    table = Table(border_style="yellow", show_lines=False)
    table.add_column("Market", style="bold")
    table.add_column("BUY", style="green", justify="right")
    table.add_column("SELL", style="red", justify="right")
    table.add_column("HOLD", style="dim", justify="right")
    table.add_column("Avg Score", justify="right")
    table.add_column("Sentiment")

    for atype, items in by_type.items():
        b = sum(1 for _, s, _ in items if s == "BUY")
        s = sum(1 for _, s, _ in items if s == "SELL")
        h = sum(1 for _, s, _ in items if s == "HOLD")
        avg = sum(sc for _, _, sc in items) / len(items)
        if avg > 0.1:
            sent = Text("BULLISH", style="green")
        elif avg < -0.1:
            sent = Text("BEARISH", style="red")
        else:
            sent = Text("NEUTRAL", style="dim")
        table.add_row(atype.capitalize(), str(b), str(s), str(h), f"{avg:+.3f}", sent)

    console.print(table)

    # Top movers
    sorted_by_score = sorted(summaries, key=lambda x: x[3])
    most_bearish = sorted_by_score[:3]
    most_bullish = sorted_by_score[-3:][::-1]

    movers = Table(border_style="dim", show_lines=False)
    movers.add_column("Most Bullish", style="green", min_width=20)
    movers.add_column("Most Bearish", style="red", min_width=20)

    for i in range(3):
        bull = f"{most_bullish[i][0]} ({most_bullish[i][3]:+.3f})" if i < len(most_bullish) else ""
        bear = f"{most_bearish[i][0]} ({most_bearish[i][3]:+.3f})" if i < len(most_bearish) else ""
        movers.add_row(bull, bear)

    console.print(movers)
    console.print()


# ---------------------------------------------------------------------------
# Watchlist manager
# ---------------------------------------------------------------------------

def show_watchlist_manager(current: list[str]):
    """Display watchlist manager."""
    console.print(Panel(
        f"  {len(current)} assets: " + ", ".join(current[:10])
        + (f"... +{len(current)-10} more" if len(current) > 10 else ""),
        title="[bold]Watchlist Manager[/bold]",
        border_style="blue",
    ))
    menu = Table(show_header=False, box=None, padding=(0, 2))
    menu.add_column(style="bold cyan")
    menu.add_column()
    menu.add_row("[a]", "Add a symbol")
    menu.add_row("[r]", "Remove a symbol")
    menu.add_row("[l]", "List all")
    menu.add_row("[c]", "Back to main menu")
    console.print(menu)
    console.print()


# ---------------------------------------------------------------------------
# Price alerts
# ---------------------------------------------------------------------------

def show_alerts(alerts: list[dict]):
    """Show active price alerts."""
    if not alerts:
        console.print("[dim]No active price alerts.[/dim]")
        console.print()
        return

    table = Table(title="Active Price Alerts", border_style="yellow")
    table.add_column("#", style="dim", width=4)
    table.add_column("Symbol", style="bold cyan")
    table.add_column("Condition")
    table.add_column("Target", justify="right")
    table.add_column("Set", style="dim")

    for i, a in enumerate(alerts, 1):
        cond_style = "green" if a["condition"] == "above" else "red"
        table.add_row(
            str(i),
            a["symbol"],
            Text(a["condition"].upper(), style=cond_style),
            f"${a['target_price']:,.2f}",
            a["created_at"][:16],
        )

    console.print(table)
    console.print()


def show_triggered_alerts(triggered: list[tuple[dict, float]]):
    """Show alerts that were just triggered."""
    for alert, price in triggered:
        console.print(
            f"  [bold yellow]ALERT[/bold yellow] {alert['symbol']} is "
            f"{'[green]above[/green]' if alert['condition'] == 'above' else '[red]below[/red]'} "
            f"${alert['target_price']:,.2f} — now at ${price:,.2f}"
        )


# ---------------------------------------------------------------------------
# Asset comparison
# ---------------------------------------------------------------------------

def show_asset_comparison(
    md1: MarketData, summary1: TechnicalSummary,
    md2: MarketData, summary2: TechnicalSummary,
):
    """Compare two assets side by side."""
    console.print(Panel(
        f"  [bold cyan]{md1.asset.symbol}[/bold cyan] vs [bold cyan]{md2.asset.symbol}[/bold cyan]",
        title="[bold]Asset Comparison[/bold]",
        border_style="cyan",
    ))

    table = Table(border_style="cyan", show_lines=True)
    table.add_column("Indicator", style="bold", min_width=12)
    table.add_column(md1.asset.symbol, justify="center", min_width=18)
    table.add_column(md2.asset.symbol, justify="center", min_width=18)

    # Price row
    table.add_row("Price", f"${md1.asset.current_price:,.2f}", f"${md2.asset.current_price:,.2f}")
    table.add_row(
        "Signal",
        Text(summary1.overall_signal.value, style=signal_style(summary1.overall_signal)),
        Text(summary2.overall_signal.value, style=signal_style(summary2.overall_signal)),
    )
    table.add_row(
        "Confidence",
        Text(f"{abs(summary1.overall_score)*100:.0f}%", style=signal_style(summary1.overall_signal)),
        Text(f"{abs(summary2.overall_score)*100:.0f}%", style=signal_style(summary2.overall_signal)),
    )

    # Per indicator
    for i in range(min(len(summary1.indicators), len(summary2.indicators))):
        ind1 = summary1.indicators[i]
        ind2 = summary2.indicators[i]
        s1 = signal_style(ind1.signal)
        s2 = signal_style(ind2.signal)
        table.add_row(
            ind1.name,
            Text(f"{ind1.signal.value} I={ind1.intensity:.2f}", style=s1),
            Text(f"{ind2.signal.value} I={ind2.intensity:.2f}", style=s2),
        )

    console.print(table)
    console.print()


# ---------------------------------------------------------------------------
# Multi-timeframe analysis
# ---------------------------------------------------------------------------

def show_multi_timeframe(symbol: str, daily_summary: TechnicalSummary, weekly_summary: TechnicalSummary):
    """Show daily vs weekly analysis comparison."""
    console.print(Panel(
        f"  [bold cyan]{symbol}[/bold cyan] — Multi-Timeframe Analysis",
        title="[bold]Daily vs Weekly[/bold]",
        border_style="magenta",
    ))

    table = Table(border_style="magenta", show_lines=True)
    table.add_column("Indicator", style="bold", min_width=12)
    table.add_column("Daily", justify="center", min_width=16)
    table.add_column("Weekly", justify="center", min_width=16)
    table.add_column("Agreement")

    table.add_row(
        "Overall",
        Text(f"{daily_summary.overall_signal.value} ({abs(daily_summary.overall_score)*100:.0f}%)",
             style=signal_style(daily_summary.overall_signal)),
        Text(f"{weekly_summary.overall_signal.value} ({abs(weekly_summary.overall_score)*100:.0f}%)",
             style=signal_style(weekly_summary.overall_signal)),
        Text("YES", style="green") if daily_summary.overall_signal == weekly_summary.overall_signal
        else Text("NO", style="red"),
    )

    for i in range(min(len(daily_summary.indicators), len(weekly_summary.indicators))):
        d = daily_summary.indicators[i]
        w = weekly_summary.indicators[i]
        agree = d.signal == w.signal and d.signal != SignalType.HOLD
        table.add_row(
            d.name,
            Text(f"{d.signal.value} I={d.intensity:.2f}", style=signal_style(d.signal)),
            Text(f"{w.signal.value} I={w.intensity:.2f}", style=signal_style(w.signal)),
            Text("YES", style="green") if agree else (Text("—", style="dim") if d.signal == SignalType.HOLD and w.signal == SignalType.HOLD else Text("NO", style="red")),
        )

    console.print(table)

    # Agreement count
    agreements = sum(
        1 for i in range(min(len(daily_summary.indicators), len(weekly_summary.indicators)))
        if daily_summary.indicators[i].signal == weekly_summary.indicators[i].signal
        and daily_summary.indicators[i].signal != SignalType.HOLD
    )
    total_active = sum(
        1 for i in range(min(len(daily_summary.indicators), len(weekly_summary.indicators)))
        if daily_summary.indicators[i].signal != SignalType.HOLD
        or weekly_summary.indicators[i].signal != SignalType.HOLD
    )
    if total_active > 0:
        console.print(f"  [dim]Timeframe agreement: {agreements}/{total_active} active indicators align[/dim]")
    console.print()


# ---------------------------------------------------------------------------
# Backtest results
# ---------------------------------------------------------------------------

def show_backtest_results(result):
    """Show backtest results."""
    from analysis.backtest import BacktestResult
    r: BacktestResult = result

    console.print(Panel(
        f"  [bold cyan]{r.symbol}[/bold cyan] — {r.period_days} day backtest  |  "
        f"{r.total_signals} signals  |  {len(r.trades)} trades",
        title="[bold]Backtest Results[/bold]",
        border_style="green",
    ))

    if not r.trades:
        console.print("[dim]No trades generated during backtest period.[/dim]")
        console.print()
        return

    # Summary stats
    table = Table(border_style="green")
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")

    table.add_row("Total P&L", Text(f"{r.total_pnl_pct:+.2f}%", style=pnl_style(r.total_pnl_pct)))
    table.add_row("Avg P&L / Trade", Text(f"{r.avg_pnl_pct:+.2f}%", style=pnl_style(r.avg_pnl_pct)))
    table.add_row("Best Trade", Text(f"{r.best_pct:+.2f}%", style="green"))
    table.add_row("Worst Trade", Text(f"{r.worst_pct:+.2f}%", style="red"))
    table.add_row("Win Rate", f"{r.win_rate:.0%} ({r.win_count}W / {r.loss_count}L)")

    console.print(table)

    # Trade list (last 15)
    trades_to_show = r.trades[-15:]
    t_table = Table(title=f"Trades (last {len(trades_to_show)})", border_style="dim", show_lines=False)
    t_table.add_column("Entry", style="dim")
    t_table.add_column("Exit", style="dim")
    t_table.add_column("Signal")
    t_table.add_column("Entry $", justify="right")
    t_table.add_column("Exit $", justify="right")
    t_table.add_column("P&L %", justify="right")
    t_table.add_column("Conf", justify="right", style="dim")

    for t in trades_to_show:
        ps = pnl_style(t.pnl_pct)
        sig = SignalType.BUY if t.signal == "BUY" else SignalType.SELL
        t_table.add_row(
            t.entry_date,
            t.exit_date,
            Text(t.signal, style=signal_style(sig)),
            f"${t.entry_price:,.2f}",
            f"${t.exit_price:,.2f}",
            Text(f"{t.pnl_pct:+.2f}%", style=ps),
            f"{t.confidence:.0%}",
        )

    console.print(t_table)
    console.print()


# ---------------------------------------------------------------------------
# Export confirmation
# ---------------------------------------------------------------------------

def show_export_menu():
    """Show export options."""
    menu = Table(show_header=False, box=None, padding=(0, 2))
    menu.add_column(style="bold cyan")
    menu.add_column()
    menu.add_row("[a]", "Export all (trades + portfolio + recommendations)")
    menu.add_row("[t]", "Export trades only")
    menu.add_row("[r]", "Export recommendations only")
    menu.add_row("[c]", "Cancel")
    console.print(Panel(menu, title="[bold]Export to CSV[/bold]", border_style="blue"))
    console.print()


# ---------------------------------------------------------------------------
# ASCII price chart
# ---------------------------------------------------------------------------

def show_price_chart(symbol: str, chart_lines: list[str], current_price: float, change_pct: float):
    """Display ASCII price chart."""
    ps = pnl_style(change_pct)
    console.print(Panel(
        f"  [bold cyan]{symbol}[/bold cyan]  "
        f"Price: [bold]${current_price:,.2f}[/bold]  "
        f"Change: [{ps}]{change_pct:+.2f}%[/{ps}]",
        title="[bold]Price Chart[/bold]",
        border_style="cyan",
    ))
    for line in chart_lines:
        # Color up/down markers
        colored = line.replace("^", "[green]^[/green]").replace("v", "[red]v[/red]")
        console.print(f"  {colored}")
    console.print()


# ---------------------------------------------------------------------------
# Screener results
# ---------------------------------------------------------------------------

def show_screener_menu():
    """Show screener preset options."""
    menu = Table(show_header=False, box=None, padding=(0, 2))
    menu.add_column(style="bold cyan")
    menu.add_column()
    menu.add_row("[1]", "Oversold (RSI < 30)")
    menu.add_row("[2]", "Overbought (RSI > 70)")
    menu.add_row("[3]", "Strong BUY signals (confidence > 30%)")
    menu.add_row("[4]", "Strong SELL signals (confidence > 30%)")
    menu.add_row("[5]", "Trending (ADX > 25)")
    menu.add_row("[6]", "High volume (Volume > 1.5x avg)")
    menu.add_row("[c]", "Cancel")
    console.print(Panel(menu, title="[bold]Screener[/bold]", border_style="yellow"))
    console.print()


def show_screener_results(screen_name: str, results: list[tuple]):
    """Show screener results."""
    if not results:
        console.print(f"  [dim]No assets match '{screen_name}'.[/dim]")
        console.print()
        return

    table = Table(title=f"Screener: {screen_name} ({len(results)} matches)", border_style="yellow")
    table.add_column("Symbol", style="bold cyan")
    table.add_column("Type", style="dim")
    table.add_column("Price", justify="right")
    table.add_column("Signal")
    table.add_column("Confidence", justify="right")
    table.add_column("Score", justify="right")

    for md, summary in results:
        style = signal_style(summary.overall_signal)
        table.add_row(
            md.asset.symbol,
            md.asset.asset_type.value,
            f"${md.asset.current_price:,.2f}",
            Text(summary.overall_signal.value, style=style),
            f"{abs(summary.overall_score)*100:.0f}%",
            f"{summary.overall_score:+.4f}",
        )

    console.print(table)
    console.print()


# ---------------------------------------------------------------------------
# Correlation matrix
# ---------------------------------------------------------------------------

def show_correlation_matrix(symbols: list[str], matrix: list[list[float]]):
    """Display a correlation matrix."""
    table = Table(title="Correlation Matrix (90-day returns)", border_style="magenta")
    table.add_column("", style="bold cyan", min_width=10)

    for sym in symbols:
        table.add_column(sym[:6], justify="center", min_width=7)

    for i, sym in enumerate(symbols):
        row = [sym]
        for j in range(len(symbols)):
            val = matrix[i][j]
            if i == j:
                row.append("[dim]1.00[/dim]")
            elif val > 0.7:
                row.append(f"[bold red]{val:.2f}[/bold red]")
            elif val > 0.4:
                row.append(f"[yellow]{val:.2f}[/yellow]")
            elif val < -0.3:
                row.append(f"[green]{val:.2f}[/green]")
            else:
                row.append(f"[dim]{val:.2f}[/dim]")
        table.add_row(*row)

    console.print(table)
    console.print("  [dim]Red = high correlation | Green = negative correlation | Yellow = moderate[/dim]")
    console.print()


# ---------------------------------------------------------------------------
# Support / resistance levels
# ---------------------------------------------------------------------------

def show_levels(symbol: str, current_price: float, levels: list, pivots: dict):
    """Display support/resistance levels and pivot points."""
    console.print(Panel(
        f"  [bold cyan]{symbol}[/bold cyan]  Current: [bold]${current_price:,.2f}[/bold]",
        title="[bold]Support & Resistance[/bold]",
        border_style="blue",
    ))

    if levels:
        table = Table(border_style="blue", show_lines=False)
        table.add_column("Type", min_width=12)
        table.add_column("Price", justify="right")
        table.add_column("Strength", justify="right")
        table.add_column("Distance")

        for lv in levels:
            style = "green" if lv.level_type == "support" else "red"
            stars = "*" * min(lv.strength, 5)
            table.add_row(
                Text(lv.level_type.upper(), style=style),
                f"${lv.price:,.2f}",
                Text(stars, style=style),
                lv.description,
            )

        console.print(table)
    else:
        console.print("  [dim]No significant levels detected.[/dim]")

    if pivots:
        p_table = Table(title="Pivot Points", border_style="dim", show_lines=False)
        p_table.add_column("Level", style="bold")
        p_table.add_column("Price", justify="right")
        for name, price in pivots.items():
            style = "green" if name.startswith("S") else "red" if name.startswith("R") else "bold"
            p_table.add_row(Text(name, style=style), f"${price:,.2f}")
        console.print(p_table)

    console.print()


# ---------------------------------------------------------------------------
# Portfolio risk analysis
# ---------------------------------------------------------------------------

def show_risk_analysis(metrics: dict):
    """Display portfolio risk metrics."""
    table = Table(title="Portfolio Risk Analysis", border_style="red")
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")

    for key, val in metrics.items():
        if isinstance(val, float):
            if "pct" in key.lower() or "ratio" in key.lower() or "drawdown" in key.lower():
                style = pnl_style(val) if "return" in key.lower() else "white"
                table.add_row(key, Text(f"{val:+.2f}%", style=style) if "pct" in key.lower() or "drawdown" in key.lower()
                             else Text(f"{val:.3f}", style=style))
            else:
                table.add_row(key, f"${val:,.2f}")
        else:
            table.add_row(key, str(val))

    console.print(table)
    console.print()


# ---------------------------------------------------------------------------
# Trade journal
# ---------------------------------------------------------------------------

def show_trade_journal(notes: list[dict]):
    """Show trade journal entries."""
    if not notes:
        console.print("[dim]No journal entries yet.[/dim]")
        console.print()
        return

    table = Table(title="Trade Journal", border_style="green")
    table.add_column("Trade", style="bold cyan", min_width=12)
    table.add_column("Note", max_width=60)
    table.add_column("Time", style="dim")

    for n in notes:
        symbol = n.get("symbol", "?")
        signal = n.get("signal", "?")
        table.add_row(
            f"{symbol} ({signal})",
            n["note"],
            n["created_at"][:16],
        )

    console.print(table)
    console.print()


# ---------------------------------------------------------------------------
# Earnings calendar
# ---------------------------------------------------------------------------

def show_earnings(earnings: list[tuple[str, dict]]):
    """Show upcoming earnings for stocks."""
    has_data = False

    table = Table(title="Earnings Calendar", border_style="yellow")
    table.add_column("Symbol", style="bold cyan")
    table.add_column("Next Earnings", justify="right")
    table.add_column("Details", style="dim")

    for symbol, info in earnings:
        if info:
            has_data = True
            date_str = info.get("date", "Unknown")
            details = info.get("details", "")
            table.add_row(symbol, str(date_str), details)

    if has_data:
        console.print(table)
    else:
        console.print("[dim]No earnings data available.[/dim]")
    console.print()


# ---------------------------------------------------------------------------
# News headlines
# ---------------------------------------------------------------------------

def show_news(symbol: str, articles: list[dict]):
    """Show news headlines for an asset."""
    if not articles:
        console.print(f"[dim]No news found for {symbol}.[/dim]")
        console.print()
        return

    console.print(Panel(
        f"  [bold cyan]{symbol}[/bold cyan] — Latest News",
        title="[bold]News Headlines[/bold]",
        border_style="blue",
    ))

    for i, article in enumerate(articles[:10], 1):
        title = article.get("title", "No title")
        publisher = article.get("publisher", "")
        pub_str = f" [dim]({publisher})[/dim]" if publisher else ""
        console.print(f"  {i:2}. {title}{pub_str}")

    console.print()
