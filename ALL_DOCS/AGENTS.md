# Purpose

Read-only knowledge base: research reports, broker API documentation, market analysis transcripts, and raw tick data archives. **No implementation lives here.**

# Ownership

| Owner | Scope |
|-------|-------|
| Upstox API Architect | `UPSTOX-api-docs.json`, `deep-research-report_UPSTOX.md` |
| Strategy & Core Logic Engineer | `deep-research-report_OPTIONS_BUYINGS.md`, `Institutional-Grade Intraday Index Options Edge.md`, `The Premium Divergence Architecture.md` |
| Risk & Compliance Auditor | `2026-06-07-OBJECTIVES-md.pdf` (regulator hard rules reference) |
| All Agents (read) | Every file in this folder is fair game for context retrieval |

# Local Contracts

- **READ-ONLY:** No file in this folder may be modified by an agent.
- **Citation required:** Any code/decision that relies on a doc here must include a one-line citation in the relevant child AGENTS.md (e.g., `> Source: ALL_DOCS/UPSTOX-api-docs.json`).
- **No secrets:** Nothing in this folder may contain live credentials, tokens, or PII.
- **TTL:** Source materials older than 90 days should be flagged with a DOX status note in the child that references them.

# Work Guidance

- Use these files as **research ground truth**, not as the implementation contract.
- When multiple sources disagree, prefer the most recent document, then fall back to Upstox official API docs.
- For institucional cycle logic (Short Buildup, Short Covering, etc.), `Institutional-Grade Intraday Index Options Edge.md` is the primary reference.
- For signal math (COI PCR, 9 EMA, VWAP), `unified_trading_framework.md` and `unified_trading_framework.md` in the Chinese variant are the canonical source.
- For Upstox-specific REST/WebSocket payloads, `UPSTOX-api-docs.json` is the canonical source.

# Verification

- Every code module that consumes `ALL_DOCS/` knowledge must have at least one corresponding unit test that asserts the documented contract is honored.
- The Strategy Engineer is responsible for weekly drift checks: if a referenced doc changes, propagate the change to the relevant child AGENTS.md within 7 days.

# Child DOX Index

This folder is **flat** — no child AGENTS.md files are required. Sub-directories (if any) would be added only if a sub-topic accumulates its own rules, materials, and quality standards.

If the project later needs to split research by source (e.g., `ALL_DOCS/upstox/`, `ALL_DOCS/strategy/`, `ALL_DOCS/market_transcripts/`), add child AGENTS.md files per the DOX Child Doc Shape.
