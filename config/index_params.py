"""Index-specific broker constants — owner: Upstox API Architect.

These values are hard-coded by the Upstox / NSE contract and must NOT be
tuned by the strategy or risk layers. They govern strike selection,
lot sizing, and price-tick resolution for each supported index.

The canonical narrative contract lives in ``config/AGENTS.md`` under
"Index-Specific Constants".

Source citation:
    > config/AGENTS.md — Index-Specific Constants
    > ALL_DOCS/UPSTOX-api-docs.json (Upstox instrument master contract)
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class IndexSymbol(str, Enum):
    """Supported index symbols.

    String-valued enum so it can be serialised directly into Upstox
    instrument keys, log fields, and journal rows.
    """

    NIFTY = "NIFTY"
    BANKNIFTY = "BANKNIFTY"
    FINNIFTY = "FINNIFTY"
    MIDCPNIFTY = "MIDCPNIFTY"


@dataclass(frozen=True, slots=True)
class IndexParams:
    """Static contract for a tradable index."""

    symbol: IndexSymbol
    strike_step: int
    lot_size: int
    tick_size: float
    exchange: str
    segment: str


#: The complete table of supported indices. Frozen so it cannot be mutated
#: at runtime — lookups by symbol are O(1).
INDEX_PARAMS: dict[IndexSymbol, IndexParams] = {
    IndexSymbol.NIFTY: IndexParams(
        symbol=IndexSymbol.NIFTY,
        strike_step=50,
        lot_size=25,
        tick_size=0.05,
        exchange="NSE",
        segment="NSE_FO",
    ),
    IndexSymbol.BANKNIFTY: IndexParams(
        symbol=IndexSymbol.BANKNIFTY,
        strike_step=100,
        lot_size=15,
        tick_size=0.05,
        exchange="NSE",
        segment="NSE_FO",
    ),
    IndexSymbol.FINNIFTY: IndexParams(
        symbol=IndexSymbol.FINNIFTY,
        strike_step=50,
        lot_size=25,
        tick_size=0.05,
        exchange="NSE",
        segment="NSE_FO",
    ),
    IndexSymbol.MIDCPNIFTY: IndexParams(
        symbol=IndexSymbol.MIDCPNIFTY,
        strike_step=25,
        lot_size=50,
        tick_size=0.05,
        exchange="NSE",
        segment="NSE_FO",
    ),
}


def get_params(symbol: IndexSymbol) -> IndexParams:
    """Return the :class:`IndexParams` for ``symbol``.

    Raises
    ------
    KeyError
        If ``symbol`` is not a supported index. This is treated as a
        configuration error, not a recoverable runtime error.
    """
    try:
        return INDEX_PARAMS[symbol]
    except KeyError as exc:
        raise KeyError(
            f"Index {symbol!r} is not configured in INDEX_PARAMS. "
            f"Supported: {sorted(p.symbol.value for p in INDEX_PARAMS.values())}"
        ) from exc
