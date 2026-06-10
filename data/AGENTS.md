# Purpose

Runtime data: SQLite trade-journal DB, instrument master cache, tick snapshots. Persistent state that survives process restarts.

# Ownership

| File / Resource | Owner | Mutability |
|------|-------|-------------|
| `trade_journal.db` (SQLite, WAL mode) | Risk & Compliance Auditor | Append-only, rotated monthly |
| `instrument_cache/` (per-day CSV / .csv.gz) | Upstox API Architect | Refreshed daily, retained 7 days |
| `tick_snapshots/` (rotated parquet) | Strategy & Core Logic Engineer | Optional, retained 30 days |
| `cache/` (Redis state) | Shared | Volatile, rebuilt on process start |

# Local Contracts

- **SQLite WAL mode mandated:** `PRAGMA journal_mode = WAL` must be set on every connection. Without it, concurrent reads during writes will block.
- **No PII in tick data:** Ticks are public market data; do not embed any user identifier in tick snapshots.
- **No credentials here:** This folder is shared with the audit pipeline. Tokens, secrets, and `.env` files **must not** be placed here.
- **Time zone in DB:** Every timestamp column is `INTEGER` storing epoch milliseconds (UTC) OR `TEXT` storing ISO-8601 with explicit `+05:30` offset. Never naive.
- **Schema migrations:** Use a versioned migration file (`schema_v1.sql`, `schema_v2.sql`, …). Migrations are applied on application start, idempotently.

# Work Guidance

- **Append-only trade log:** Once a row is written to `trade_journal.db`, it is never updated except by a `corrected` column append. No in-place mutation of historical P&L.
- **Daily rotation:** The journal DB is rotated monthly. Old DBs are zipped and stored at `data/journal_archive/{YYYY-MM}.db.zip`.
- **Instrument cache TTL:** The Upstox instrument CSV is re-downloaded if the local file is older than 24 hours. Old files are kept for 7 days then deleted.
- **Tick snapshots (optional):** If the strategy wants to record raw ticks for backtest replay, write to parquet partitioned by `(index, trade_date)`. Use `pyarrow.parquet.write_table()` for speed.

# Verification

- DB-level checks:
  - `PRAGMA journal_mode` returns `wal`.
  - Row count grows monotonically (no deletes except in `archive_*`).
- Migration test:
  - Running `migrate.py` twice on a fresh DB is idempotent.
  - Running `migrate.py` on an old-version DB upgrades without data loss.

# Child DOX Index

This folder is **flat** — no child AGENTS.md files required. Sub-resources are documented in the Ownership table above.
