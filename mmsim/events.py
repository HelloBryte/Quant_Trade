"""Normalized market-data events shared by live feeds, the recorder and replay.

Every event carries ``ts``: the local receive time in nanoseconds since the
epoch. The simulator runs on this clock, so a replayed session sees exactly
the same event ordering and timing as the live session that recorded it.
"""
from __future__ import annotations

from dataclasses import dataclass

BUY = 1
SELL = -1


@dataclass(slots=True)
class Quote:
    """Top of book: best bid and best ask."""

    ts: int
    inst: str  # e.g. "binance-spot:BTCUSDT"
    bid: float
    bid_qty: float
    ask: float
    ask_qty: float

    @property
    def mid(self) -> float:
        return 0.5 * (self.bid + self.ask)


@dataclass(slots=True)
class Trade:
    """A public trade print."""

    ts: int
    inst: str
    price: float
    qty: float
    side: int  # aggressor side: BUY lifted the ask, SELL hit the bid
    ts_exch: int = 0  # exchange timestamp in ns, 0 if unknown


@dataclass(slots=True)
class Depth:
    """Partial order book snapshot (top N levels, best price first)."""

    ts: int
    inst: str
    bids: list[tuple[float, float]]
    asks: list[tuple[float, float]]


Event = Quote | Trade | Depth
