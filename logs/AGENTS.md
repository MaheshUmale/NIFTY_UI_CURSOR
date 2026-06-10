# Purpose

Application log files (rotated). The operational observability layer — the only place a post-mortem investigator looks when "the bot did something weird at 14:32 IST."

# Ownership

| Resource | Owner |
|------|-------|
| `trader.log` (rotating) | All agents (shared) |
| `error.log` (errors only) | All agents (shared) |
| `trader_audit.log` (Risk Auditor + journal events) | Risk & Compliance Auditor |
| `.gitkeep` | All agents |

# Local Contracts

- **Format:** JSON lines (one event per line). Each line carries at minimum:
  - `ts` (ISO-8601 with explicit `+05:30` offset)
  - `level` (DEBUG / INFO / WARNING / ERROR / CRITICAL)
  - `module` (dotted path)
  - `msg` (free text)
  - `tag` (uuid4 if associated with a trade)
- **Rotation:** `RotatingFileHandler` with `maxBytes=10 MB`, `backupCount=20`. Compress rotated files to `.log.gz` after 24 h.
- **Sensitive data masking:** The logger must **never** emit raw `access_token`, `api_secret`, or PII. A custom `Filter` must scrub these fields.
- **Clock:** All timestamps logged in IST (not UTC) for human readability. The raw `epoch_ms` is included as a secondary field for machines.
- **Retention:** 30 days hot, 1 year cold (in `logs/archive/{YYYY-MM}.tar.gz`).

# Work Guidance

- **Log levels:**
  - `DEBUG` — per-tick diagnostics (off in production).
  - `INFO` — signal generated, order placed, position opened/closed.
  - `WARNING` — recoverable异常 (network blip, OI null, retry succeeded).
  - `ERROR` — recoverable error (order rejected, slippage exceeded).
  - `CRITICAL` — risk guard trip, emergency flatten, auth failure.
- **Structured fields over string concatenation:** `logger.info("order_placed", extra={"tag": tag, "qty": qty})` — never `f"order placed for {tag}"`.
- **Per-trade correlation:** Every log event associated with a trade must carry the trade's `tag` uuid4. The post-mortem query is `grep "tag=<uuid>" logs/`.
- **Risk Auditor's audit log:** All veto decisions, daily-loss trips, and emergency flattens go to `trader_audit.log` separately, for compliance review.
- **No PII in messages:** Use `user_id` hash (uuid5) if a user identifier is required.

# Verification

- `test_logger.py` integration checks:
  - Sensitive fields (`access_token`, `api_secret`) are scrubbed in both file and console handlers.
  - Rotation kicks in at the configured `maxBytes`.
  - Log records carry a parseable `ts`, `level`, `module`, `msg`.
- Post-mortem test: given a known scenario, an investigator can recover the full event timeline via `grep` on the log files alone.

# Child DOX Index

This folder is **flat** — no child AGENTS.md files required. Sub-resources are documented in the Ownership table above.
