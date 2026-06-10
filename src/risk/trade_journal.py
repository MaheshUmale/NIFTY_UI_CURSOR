"""Append-only SQLite trade journal.

Write-once, never-update journal that persists every trade, daily P&L roll-up,
and audit event. Schema is versioned and migrations are applied idempotently
on application start.

Source citation:
    > src/risk/AGENTS.md — Trade journal: WAL mode, unique uuid4 tag,
      idempotent migrations.
    > data/AGENTS.md — SQLite WAL mode, naive-timestamps banned.
    > data/schema_v1.sql — Reference schema definition.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from src.utils.time_utils import now_ist, to_epoch_ms

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_SCHEMA_SQL: str = (Path(__file__).parent.parent.parent / "data" / "schema_v1.sql").read_text(
    encoding="utf-8"
)


# ---------------------------------------------------------------------------
# Journal
# ---------------------------------------------------------------------------


class TradeJournal:
    """Append-only trade journal backed by SQLite with WAL mode.

    Parameters
    ----------
    db_path : str | Path
        Filesystem path to the SQLite database file.
        Default: ``data/trade_journal.db``.
    """

    def __init__(self, db_path: str | Path = "data/trade_journal.db") -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def connect(self) -> None:
        """Open or reuse the SQLite connection.

        Must be called once before any read/write operation. Idempotent.
        """
        if self._conn is not None:
            return
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode = WAL;")
        self._conn.execute("PRAGMA foreign_keys = ON;")
        self._apply_migrations()

    def close(self) -> None:
        """Close the SQLite connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    @property
    def conn(self) -> sqlite3.Connection:
        """The underlying SQLite connection. Raises if not connected."""
        if self._conn is None:
            raise RuntimeError("TradeJournal is not connected. Call connect() first.")
        return self._conn

    # ------------------------------------------------------------------
    # Migrations
    # ------------------------------------------------------------------

    def _apply_migrations(self) -> None:
        """Apply schema_v1.sql idempotently.

        This method checks the ``schema_version`` table and skips versions
        that have already been applied.
        """
        cursor = self.conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='schema_version'")
        has_version_table = cursor.fetchone()[0] > 0

        if not has_version_table:
            # First time — run the full schema
            self.conn.executescript(_SCHEMA_SQL.replace("PRAGMA journal_mode = WAL; -- executed by the migration runner, not here", ""))
            self.conn.execute(
                "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
                (1, to_epoch_ms(now_ist())),
            )
            self.conn.commit()
        else:
            # Check if version 1 is already applied
            cursor = self.conn.execute("SELECT MAX(version) FROM schema_version")
            max_ver = cursor.fetchone()[0] or 0
            if max_ver < 1:
                self.conn.executescript(_SCHEMA_SQL.replace("PRAGMA journal_mode = WAL; -- executed by the migration runner, not here", ""))
                self.conn.execute(
                    "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
                    (1, to_epoch_ms(now_ist())),
                )
                self.conn.commit()

    # ------------------------------------------------------------------
    # Trade CRUD (append-only)
    # ------------------------------------------------------------------

    def record_trade(self, trade: dict[str, Any]) -> str:
        """Insert a new trade row.

        Parameters
        ----------
        trade : dict
            Must contain keys matching the ``trades`` table columns.

        Returns
        -------
        str
            The ``tag`` of the inserted trade.
        """
        tag = trade.get("tag")
        if tag is None:
            raise ValueError("trade must contain a 'tag' field")

        self.conn.execute(
            """INSERT INTO trades (
                tag, instrument_key, symbol, side, qty,
                entry_price, entry_ts, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                tag,
                trade["instrument_key"],
                trade["symbol"],
                trade["side"],
                trade["qty"],
                trade["entry_price"],
                trade.get("entry_ts", to_epoch_ms(now_ist())),
                trade.get("status", "OPEN"),
                trade.get("created_at", to_epoch_ms(now_ist())),
            ),
        )
        self.conn.commit()
        return tag

    def close_trade(self, tag: str, exit_price: float) -> None:
        """Mark a trade as CLOSED with the realised exit price."""
        self.conn.execute(
            """UPDATE trades
               SET exit_price = ?, exit_ts = ?, status = 'CLOSED'
               WHERE tag = ?""",
            (exit_price, to_epoch_ms(now_ist()), tag),
        )
        self.conn.commit()

    def trade_count_today(self) -> int:
        """Number of trades recorded today (any status)."""
        import datetime as _dt

        today_start = _dt.datetime.combine(now_ist().date(), _dt.time.min, tzinfo=now_ist().tzinfo)
        epoch_start = to_epoch_ms(today_start)
        cursor = self.conn.execute(
            "SELECT COUNT(*) FROM trades WHERE created_at >= ?",
            (epoch_start,),
        )
        return cursor.fetchone()[0]

    # ------------------------------------------------------------------
    # Daily P&L
    # ------------------------------------------------------------------

    def get_daily_pnl(self, trade_date: str | None = None) -> dict[str, Any] | None:
        """Return the daily P&L row for ``trade_date`` (ISO date) or today."""
        if trade_date is None:
            trade_date = now_ist().strftime("%Y-%m-%d")
        cursor = self.conn.execute(
            "SELECT * FROM daily_pnl WHERE trade_date = ?",
            (trade_date,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    def upsert_daily_pnl(self, trade_date: str, realised_pnl: float, unrealised_pnl: float, trade_count: int) -> None:
        """Insert or update the daily P&L row."""
        self.conn.execute(
            """INSERT INTO daily_pnl (trade_date, realised_pnl, unrealised_pnl, trade_count, last_updated)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(trade_date) DO UPDATE SET
                   realised_pnl = excluded.realised_pnl,
                   unrealised_pnl = excluded.unrealised_pnl,
                   trade_count = excluded.trade_count,
                   last_updated = excluded.last_updated""",
            (trade_date, realised_pnl, unrealised_pnl, trade_count, to_epoch_ms(now_ist())),
        )
        self.conn.commit()

    # ------------------------------------------------------------------
    # Audit events
    # ------------------------------------------------------------------

    def record_audit_event(self, level: str, module: str, msg: str, tag: str | None = None, reason_code: str | None = None) -> int:
        """Insert a risk-auditor audit event.

        Returns the auto-increment ``id`` of the inserted row.
        """
        cursor = self.conn.execute(
            "INSERT INTO audit_events (ts, level, module, msg, tag, reason_code) VALUES (?, ?, ?, ?, ?, ?)",
            (to_epoch_ms(now_ist()), level, module, msg, tag, reason_code),
        )
        self.conn.commit()
        return cursor.lastrowid  # type: ignore[return-value]