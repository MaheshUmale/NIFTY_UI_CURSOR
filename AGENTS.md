# DOX framework

- DOX is highly performant AGENTS.md hierarchy installed here
- Agent must follow DOX instructions across any edits

## Core Contract

- AGENTS.md files are binding work contracts for their subtrees
- Work products, source materials, instructions, records, assets, and durable docs must stay understandable from the nearest applicable AGENTS.md plus every parent AGENTS.md above it

## Read Before Editing

1. Read the root AGENTS.md
2. Identify every file or folder you expect to touch
3. Walk from the repository root to each target path
4. Read every AGENTS.md found along each route
5. If a parent AGENTS.md lists a child AGENTS.md whose scope contains the path, read that child and continue from there
6. Use the nearest AGENTS.md as the local contract and parent docs for repo-wide rules
7. If docs conflict, the closer doc controls local work details, but no child doc may weaken DOX

Do not rely on memory. Re-read the applicable DOX chain in the current session before editing.

## Update After Editing

Every meaningful change requires a DOX pass before the task is done.

Update the closest owning AGENTS.md when a change affects:

- purpose, scope, ownership, or responsibilities
- durable structure, contracts, workflows, or operating rules
- required inputs, outputs, permissions, constraints, side effects, or artifacts
- user preferences about behavior, communication, process, organization, or quality
- AGENTS.md creation, deletion, move, rename, or index contents

Update parent docs when parent-level structure, ownership, workflow, or child index changes. Update child docs when parent changes alter local rules. Remove stale or contradictory text immediately. Small edits that do not change behavior or contracts may leave docs unchanged, but the DOX pass still must happen.

## Hierarchy

- Root AGENTS.md is the DOX rail: project-wide instructions, global preferences, durable workflow rules, and the top-level Child DOX Index
- Child AGENTS.md files own domain-specific instructions and their own Child DOX Index
- Each parent explains what its direct children cover and what stays owned by the parent
- The closer a doc is to the work, the more specific and practical it must be

## Child Doc Shape

- Create a child AGENTS.md when a folder becomes a durable boundary with its own purpose, rules, responsibilities, workflow, materials, or quality standards
- Work Guidance must reflect the current standards of the project or user instructions; if there are no specific standards or instructions yet, leave it empty
- Verification must reflect an existing check; if no verification framework exists yet, leave it empty and update it when one exists

Default section order:
- Purpose
- Ownership
- Local Contracts
- Work Guidance
- Verification
- Child DOX Index

## Style

- Keep docs concise, current, and operational
- Document stable contracts, not diary entries
- Put broad rules in parent docs and concrete details in child docs
- Prefer direct bullets with explicit names
- Do not duplicate rules across many files unless each scope needs a local version
- Delete stale notes instead of explaining history
- Trim obvious statements, repeated rules, misplaced detail, and warnings for risks that no longer exist

## Closeout

1. Re-check changed paths against the DOX chain
2. Update nearest owning docs and any affected parents or children
3. Refresh every affected Child DOX Index
4. Remove stale or contradictory text
5. Run existing verification when relevant
6. Report any docs intentionally left unchanged and why

## User Preferences

- Always follow DOX guidelines before any code edit
- The trading system uses **Python 3.11+** with strict type hints and `logging` everywhere
- **Upstox API v2/v3** is the broker — OAuth2 + WebSocket + REST
- **MIS product** (`"I"`) is mandatory on every order
- **No `ApiException` is ever silently swallowed** — always log + handle gracefully
- Every code edit must be accompanied by a DOX pass (update nearest owning doc)
- Hard risk rules (3:15 PM entry cut, 3:20 PM square-off, 2% per trade, 4% daily, 3 trades/day, OI ≥ 50K) are **IMMUTABLE** — see `config/AGENTS.md`

## Child DOX Index

The project contains the following durable boundaries, each with its own AGENTS.md contract:

| Folder | Purpose | Owns |
|-------|---------|------|
| `ALL_DOCS/` | Read-only knowledge base: research reports, broker API docs, market analysis transcripts | Source material reference; no implementation |
| `config/` | Risk constants, strategy config, index parameters, environment variables | Immutable risk rules; tunable strategy parameters; .env secrets |
| `src/` | Python source code root; shared types and constants across modules | Module-level contracts; logging config; shared exceptions |
| `src/auth/` | Upstox OAuth2 authentication, daily token persistence, rate-limit token bucket | Broker authentication lifecycle; token refresh scheduler |
| `src/data/` | Market data ingestion: instrument CSV loader, async WebSocket V3, ring buffer | Raw tick normalization; ATM ± 3 strike window tracking; OI/IV data caching |
| `src/strategy/` | Signal generation: ORB (Opening Range Breakout), VWAP engine, 9 EMA filter, confluence logic | Trading signal computation; backtesting; strategy tuning |
| `src/execution/` | Order management: place/modify/cancel with ApiException handling; position tracker; EOD square-off | Live order routing; position lifecycle; forced exit logic |
| `src/risk/` | Risk gates (VETO POWER), daily loss circuit breaker, SQLite trade journal | Pre-trade validation; capital preservation; audit trail |
| `src/utils/` | Logger, time helpers, exception wrappers, shared constants | Cross-cutting utilities used by all other modules |
| `tests/` | Unit and integration tests for all modules | Test coverage requirements; mock data generators |
| `data/` | Runtime data store: SQLite journal DB, instrument cache (pickle/CSV), tick snapshots | Persistent runtime state; daily-refreshed contract master; append-only audit trail |
| `logs/` | Application log files (rotated JSON lines) | Operational observability; error trail; post-mortem evidence |
| `app.py` | FastAPI server — main entry point for E2E live streaming & UI | REST API, WebSocket relay, dashboard serving, tick processing |
| `static/` | Dashboard UI assets (HTML/CSS/JS) — real-time trading dashboard | Frontend: live ticks, signals, risk meters, connection panel |

> **Clarification — `data/` vs `src/data/`:** These are NOT duplicates.
> - `src/data/` — Python source module: instrument CSV loader, async WebSocket V3 client, in-memory ring buffer. Pure ingestion, zero computation.
> - `data/` — Runtime filesystem store: SQLite DBs, pickled instrument caches, parquet snapshots. Persistent across restarts.

DOX Status (as of 2026-06-10):
- Root AGENTS.md: ✅ has Child DOX Index — updated data/ vs src/data/ clarification
- Root AGENTS.md: ✅ has Child DOX Index
- ALL_DOCS/AGENTS.md: ✅ created
- config/AGENTS.md: ✅ created
- src/AGENTS.md: ✅ created
- src/auth/AGENTS.md: ✅ created
- src/data/AGENTS.md: ✅ created
- src/strategy/AGENTS.md: ✅ created
- src/execution/AGENTS.md: ✅ created
- src/risk/AGENTS.md: ✅ created
- src/utils/AGENTS.md: ✅ created
- tests/AGENTS.md: ✅ created
- data/AGENTS.md: ✅ created
- logs/AGENTS.md: ✅ created

All 13 AGENTS.md contracts are in place. The DOX hierarchy is complete and ready for the coding agent (Cline) to begin implementation.
