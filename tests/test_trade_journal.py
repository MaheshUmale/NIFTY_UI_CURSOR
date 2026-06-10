"""Unit tests for the append-only SQLite trade journal.

Source citation:
    > src/risk/AGENTS.md — Verification: WAL mode, unique uuid4 tag,
      idempotent schema migrations.
    > data/AGENTS.md — SQLite WAL mode, naive-timestamps banned.
"""
from __future__ import annotations

import sqlite3
import uuid
from pathlib import Path

import pytest

from src.risk.trade_journal import TradeJournal


@pytest.fixture
def journal(tmp_path: str) -> TradeJournal:
    db_path = Path(str(tmp_path)) / "test_trades.db"
    j = TradeJournal(db_path=db_path)
    j.connect()
    yield j
    j.close()


class TestConnection:
    """WAL mode and schema setup."""

    def test_wal_mode(self, journal: TradeJournal) -> None:
        cursor = journal.conn.execute("PRAGMA journal_mode")
        assert cursor.fetchone()[0].upper() == "WAL"

    def test_schema_version_table(self, journal: TradeJournal) -> None:
        cursor = journal.conn.execute("SELECT COUNT(*) FROM schema_version")
        assert cursor.fetchone()[0] >= 1

    def test_migration_idempotent(self, journal: TradeJournal) -> None:
        """Running connect again should not crash."""
        journal.close()
        journal.connect()
        cursor = journal.conn.execute("SELECT MAX(version) FROM schema_version")
        assert cursor.fetchone()[0] == 1


class TestTrades:
    """Append-only trade recording."""

    def test_record_trade(self, journal: TradeJournal) -> None:
        tag = str(uuid.uuid4())
        jtag = journal.record_trade({
            "tag": tag,
            "instrument_key": "NSE_FO|12345",
            "symbol": "NIFTY",
            "side": "BUY",
            "qty": 25,
            "entry_price": 150.0,
        })
        assert jtag == tag

    def test_duplicate_tag_raises(self, journal: TradeJournal) -> None:
        tag = str(uuid.uuid4())
        journal.record_trade({
            "tag": tag,
            "instrument_key": "NSE_FO|12345",
            "symbol": "NIFTY",
            "side": "BUY",
            "qty": 25,
            "entry_price": 150.0,
        })
        with pytest.raises(sqlite3.IntegrityError):
            journal.record_trade({
                "tag": tag,
                "instrument_key": "NSE_FO|99999",
                "symbol": "BANKNIFTY",
                "side": "SELL",
                "qty": 15,
                "entry_price": 200.0,
            })

    def test_missing_tag_raises(self, journal: TradeJournal) -> None:
        with pytest.raises(ValueError, match="tag"):
            journal.record_trade({
                "instrument_key": "NSE_FO|1",
                "symbol": "NIFTY",
                "side": "BUY",
                "qty": 25,
                "entry_price": 100.0,
            })


class TestCloseTrade:
    """Trade close/exit."""

    def test_close_trade(self, journal: TradeJournal) -> None:
        tag = str(uuid.uuid4())
        journal.record_trade({
            "tag": tag,
            "instrument_key": "NSE_FO|12345",
            "symbol": "NIFTY",
            "side": "BUY",
            "qty": 25,
            "entry_price": 150.0,
        })
        journal.close_trade(tag, exit_price=160.0)
        cursor = journal.conn.execute("SELECT status, exit_price FROM trades WHERE tag = ?", (tag,))
        row = cursor.fetchone()
        assert row[0] == "CLOSED"
        assert row[1] == 160.0


class TestTradeCountToday:
    def test_zero_trades(self, journal: TradeJournal) -> None:
        assert journal.trade_count_today() == 0

    def test_one_trade(self, journal: TradeJournal) -> None:
        journal.record_trade({
            "tag": str(uuid.uuid4()),
            "instrument_key": "NSE_FO|1",
            "symbol": "NIFTY",
            "side": "BUY",
            "qty": 25,
            "entry_price": 100.0,
        })
        assert journal.trade_count_today() == 1

    def test_three_trades(self, journal: TradeJournal) -> None:
        for i in range(3):
            journal.record_trade({
                "tag": str(uuid.uuid4()),
                "instrument_key": f"NSE_FO|{i}",
                "symbol": "NIFTY",
                "side": "BUY",
                "qty": 25,
                "entry_price": 100.0 + i,
            })
        assert journal.trade_count_today() == 3


class TestAuditEvents:
    def test_record_audit_event(self, journal: TradeJournal) -> None:
        eid = journal.record_audit_event(
            level="WARNING",
            module="test_trade_journal",
            msg="test audit",
            reason_code="VETO_TIME",
        )
        assert isinstance(eid, int)
        assert eid >= 1

    def test_audit_event_with_tag(self, journal: TradeJournal) -> None:
        tag = str(uuid.uuid4())
        eid = journal.record_audit_event(
            level="CRITICAL",
            module="test",
            msg="emergency flatten",
            tag=tag,
            reason_code="VETO_DAILY_LOSS",
        )
        cursor = journal.conn.execute("SELECT tag, reason_code FROM audit_events WHERE id = ?", (eid,))
        row = cursor.fetchone()
        assert row[0] == tag
        assert row[1] == "VETO_DAILY_LOSS"


class TestDailyPnl:
    def test_upsert_and_retrieve(self, journal: TradeJournal) -> None:
        journal.upsert_daily_pnl("2026-06-09", realised_pnl=500.0, unrealised_pnl=0.0, trade_count=1)
        row = journal.get_daily_pnl("2026-06-09")
        assert row is not None
        assert row["realised_pnl"] == 500.0
        assert row["trade_count"] == 1

    def test_upsert_update(self, journal: TradeJournal) -> None:
        journal.upsert_daily_pnl("2026-06-09", realised_pnl=500.0, unrealised_pnl=0.0, trade_count=1)
        journal.upsert_daily_pnl("2026-06-09", realised_pnl=600.0, unrealised_pnl=50.0, trade_count=2)
        row = journal.get_daily_pnl("2026-06-09")
        assert row["realised_pnl"] == 600.0
        assert row["trade_count"] == 2