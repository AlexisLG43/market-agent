"""SQLite persistence for trades, portfolio, and recommendation history."""

import sqlite3
from datetime import datetime
from pathlib import Path

from config import settings
from data.models import AssetType, PortfolioState, SignalType, Trade, TradeStatus


class Database:
    """SQLite database for the market agent."""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or settings.db_path
        self._conn: sqlite3.Connection | None = None
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _init_db(self):
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                asset_type TEXT NOT NULL,
                signal TEXT NOT NULL,
                entry_price REAL NOT NULL,
                exit_price REAL,
                quantity REAL NOT NULL,
                position_value REAL NOT NULL,
                stop_loss REAL DEFAULT 0,
                take_profit REAL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'open',
                pnl REAL DEFAULT 0,
                pnl_pct REAL DEFAULT 0,
                confidence REAL DEFAULT 0,
                reasoning TEXT DEFAULT '',
                opened_at TEXT NOT NULL,
                closed_at TEXT
            );

            CREATE TABLE IF NOT EXISTS portfolio (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                cash REAL NOT NULL,
                total_value REAL NOT NULL,
                total_pnl REAL DEFAULT 0,
                total_pnl_pct REAL DEFAULT 0,
                win_count INTEGER DEFAULT 0,
                loss_count INTEGER DEFAULT 0,
                total_trades INTEGER DEFAULT 0,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS recommendation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                signal TEXT NOT NULL,
                confidence REAL NOT NULL,
                entry_price REAL NOT NULL,
                reasoning TEXT DEFAULT '',
                approved INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            );
        """)
        conn.commit()

        # Initialize portfolio if not exists
        row = conn.execute("SELECT COUNT(*) as cnt FROM portfolio").fetchone()
        if row["cnt"] == 0:
            conn.execute(
                """INSERT INTO portfolio (id, cash, total_value, updated_at)
                   VALUES (1, ?, ?, ?)""",
                (settings.starting_capital, settings.starting_capital, datetime.now().isoformat()),
            )
            conn.commit()

    def save_trade(self, trade: Trade) -> int:
        conn = self._get_conn()
        cursor = conn.execute(
            """INSERT INTO trades
               (symbol, asset_type, signal, entry_price, exit_price,
                quantity, position_value, stop_loss, take_profit, status,
                pnl, pnl_pct, confidence, reasoning, opened_at, closed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                trade.symbol, trade.asset_type.value, trade.signal.value,
                trade.entry_price, trade.exit_price,
                trade.quantity, trade.position_value,
                trade.stop_loss, trade.take_profit, trade.status.value,
                trade.pnl, trade.pnl_pct, trade.confidence, trade.reasoning,
                trade.opened_at.isoformat(),
                trade.closed_at.isoformat() if trade.closed_at else None,
            ),
        )
        conn.commit()
        return cursor.lastrowid

    def update_trade(self, trade: Trade):
        conn = self._get_conn()
        conn.execute(
            """UPDATE trades SET
               exit_price=?, status=?, pnl=?, pnl_pct=?, closed_at=?
               WHERE id=?""",
            (
                trade.exit_price, trade.status.value,
                trade.pnl, trade.pnl_pct,
                trade.closed_at.isoformat() if trade.closed_at else None,
                trade.id,
            ),
        )
        conn.commit()

    def get_open_trades(self) -> list[Trade]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM trades WHERE status = 'open' ORDER BY opened_at DESC"
        ).fetchall()
        return [self._row_to_trade(r) for r in rows]

    def get_closed_trades(self, limit: int = 50) -> list[Trade]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM trades WHERE status = 'closed' ORDER BY closed_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [self._row_to_trade(r) for r in rows]

    def get_all_trades(self) -> list[Trade]:
        conn = self._get_conn()
        rows = conn.execute("SELECT * FROM trades ORDER BY opened_at DESC").fetchall()
        return [self._row_to_trade(r) for r in rows]

    def save_portfolio(self, state: PortfolioState):
        conn = self._get_conn()
        conn.execute(
            """UPDATE portfolio SET
               cash=?, total_value=?, total_pnl=?, total_pnl_pct=?,
               win_count=?, loss_count=?, total_trades=?, updated_at=?
               WHERE id=1""",
            (
                state.cash, state.total_value,
                state.total_pnl, state.total_pnl_pct,
                state.win_count, state.loss_count, state.total_trades,
                datetime.now().isoformat(),
            ),
        )
        conn.commit()

    def load_portfolio(self) -> PortfolioState:
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM portfolio WHERE id=1").fetchone()
        open_trades = self.get_open_trades()
        return PortfolioState(
            cash=row["cash"],
            total_value=row["total_value"],
            positions=open_trades,
            total_pnl=row["total_pnl"],
            total_pnl_pct=row["total_pnl_pct"],
            win_count=row["win_count"],
            loss_count=row["loss_count"],
            total_trades=row["total_trades"],
        )

    def save_recommendation(self, symbol: str, signal: str, confidence: float,
                            entry_price: float, reasoning: str, approved: bool):
        conn = self._get_conn()
        conn.execute(
            """INSERT INTO recommendation_history
               (symbol, signal, confidence, entry_price, reasoning, approved, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (symbol, signal, confidence, entry_price, reasoning,
             1 if approved else 0, datetime.now().isoformat()),
        )
        conn.commit()

    def get_recommendation_history(self, limit: int = 50) -> list[dict]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM recommendation_history ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def _row_to_trade(self, row: sqlite3.Row) -> Trade:
        return Trade(
            id=row["id"],
            symbol=row["symbol"],
            asset_type=AssetType(row["asset_type"]),
            signal=SignalType(row["signal"]),
            entry_price=row["entry_price"],
            exit_price=row["exit_price"],
            quantity=row["quantity"],
            position_value=row["position_value"],
            stop_loss=row["stop_loss"],
            take_profit=row["take_profit"],
            status=TradeStatus(row["status"]),
            pnl=row["pnl"],
            pnl_pct=row["pnl_pct"],
            confidence=row["confidence"],
            reasoning=row["reasoning"],
            opened_at=datetime.fromisoformat(row["opened_at"]),
            closed_at=datetime.fromisoformat(row["closed_at"]) if row["closed_at"] else None,
        )

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None
