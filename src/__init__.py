"""Upstox intraday index options trading system.
Automated signal generation, risk-gated order execution, and audit-journal
persistence designed for NSE index options (NIFTY 50, BANKNIFTY, FINNIFTY,
MIDCPNIFTY).
Architecture
-----------
    Market Data (WebSocket V3)
        → Strategy Layer (ORB, VWAP, EMA9, Confluence)
            → Risk Gate (VETO POWER — Five Hard Vetoes)
                → Execution Layer (order placement, position tracking)
                    → Trade Journal (SQLite, append-only)
Dependency flow (strict — enforced by linter):
    data → strategy → risk → execution → journal
Source citation:
    > AGENTS.md — Root DOX contract
    > src/AGENTS.md — Module-level contracts
"""
from __future__ import annotations
__version__ = "0.1.0"
