"""Live market-data feeds. Each venue module exposes the same functions:

    spot_inst(symbol), perp_inst(symbol), fetch_tick_size(symbol), stream(symbol, with_ref)
"""
from __future__ import annotations

from types import ModuleType

from . import binance, okx

VENUES: dict[str, ModuleType] = {"binance": binance, "okx": okx}


def get_feed(venue: str) -> ModuleType:
    try:
        return VENUES[venue]
    except KeyError:
        raise ValueError(f"unknown venue {venue!r}; choose from {sorted(VENUES)}") from None
