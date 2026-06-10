-- =============================================================================
-- Trade Journal — version 1 (initial schema)
-- =============================================================================
--
-- Applies idempotently on application start. The migration runner executes:
--   PRAGMA journal_mode = WAL;
-- immediately after connecting to every trade-journal SQLite handle.
--
-- Tables
-- ------
-- schema_version   : Tracks which migration version has been applied.
-- trades           : Append-only log of every trade placed, filled, or
--                    rejected. Rows are never updated in place.
-- daily_pnl        : Daily realised + unrealised P&L roll-up.
-- audit_events     : Risk auditor vetoes, emergency flattens, and other
--                    compliance-significant events.
-- =============================================================================

-- PRAGMA journal_mode = WAL;   -- executed by the migration runner, not here

CREATE TABLE IF NOT EXISTS schema_version (
    version     INTEGER PRIMARY KEY,
    applied_at  INTEGER NOT NULL       -- epoch milliseconds (UTC)
);

CREATE TABLE IF NOT EXISTS trades (
    tag             TEXT PRIMARY KEY,               -- uuid4, client-generated
    instrument_key  TEXT NOT NULL,                  -- Upstox instrument key
    symbol          TEXT NOT NULL,                  -- e.g. "NIFTY", "BANKNIFTY"
    side            TEXT NOT NULL CHECK (side IN ('BUY', 'SELL')),
    qty             INTEGER NOT NULL,
    entry_price     REAL NOT NULL,
    exit_price      REAL,                           -- NULL if still open
    stop_loss       REAL,                           -- initial SL
    target          REAL,                           -- initial target
    entry_ts        INTEGER NOT NULL,               -- epoch ms (UTC)
    exit_ts         INTEGER,                        -- epoch ms (UTC)
    status          TEXT NOT NULL CHECK (status IN ('OPEN', 'CLOSED', 'CANCELLED', 'REJECTED')),
    pnl             REAL,                           -- realised P&L; NULL until CLOSED
    signal_snapshot TEXT,                           -- JSON: frozen Signal dataclass
    created_at      INTEGER NOT NULL                -- epoch ms (UTC)
);

CREATE TABLE IF NOT EXISTS daily_pnl (
    trade_date      TEXT PRIMARY KEY,                -- ISO-8601 date e.g. "2026-06-09"
    realised_pnl    REAL NOT NULL DEFAULT 0.0,
    unrealised_pnl  REAL NOT NULL DEFAULT 0.0,
    trade_count     INTEGER NOT NULL DEFAULT 0,
    last_updated    INTEGER NOT NULL                 -- epoch ms (UTC)
);

CREATE TABLE IF NOT EXISTS audit_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          INTEGER NOT NULL,                    -- epoch ms (UTC)
    level       TEXT NOT NULL,
    module      TEXT NOT NULL,
    msg         TEXT NOT NULL,
    tag         TEXT,                                -- uuid4, links to trades(tag)
    reason_code TEXT                                 -- e.g. VETO_TIME, VETO_DAILY_LOSS
);