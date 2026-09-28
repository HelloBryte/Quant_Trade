"""Strategy interface.

A strategy looks at the market state and answers one question: where should
my bid and ask be right now? Everything is expressed in bps around a fair
value, then rounded outwards to the tick grid.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(slots=True)
class MarketState:
    ts: int
    bid: float
    ask: float
    bid_qty: float
    ask_qty: float
    tick: float
    sigma_bps: float  # volatility, bps per sqrt(second)
    gap_bps: float  # perp-vs-spot basis gap, 0 without a reference market
    imbalance: float  # top-of-book size imbalance in [-1, 1]
    position: float  # base currency

    @property
    def mid(self) -> float:
        return 0.5 * (self.bid + self.ask)


@dataclass(slots=True)
class QuoteTarget:
    bid: float | None  # None = do not quote this side
    ask: float | None
    qty: float


class Strategy:
    name = "base"

    def __init__(self, order_notional: float = 100.0, max_lots: float = 5.0, requote_bps: float = 0.3):
        self.order_notional = order_notional  # quote currency per order
        self.max_lots = max_lots  # inventory limit, in orders
        self.requote_bps = requote_bps  # keep a resting order if it is this close to the new target

    def params(self) -> dict:
        return {k: v for k, v in vars(self).items() if not k.startswith("_")}

    # --- to override -------------------------------------------------------
    def fair_value(self, s: MarketState) -> float:
        return s.mid

    def skew_and_half_spread(self, s: MarketState, lots: float) -> tuple[float, float]:
        """(centre shift, half spread) in bps relative to fair value."""
        raise NotImplementedError

    # --- shared ------------------------------------------------------------
    def quote(self, s: MarketState) -> QuoteTarget:
        fair = self.fair_value(s)
        lots = s.position * s.mid / self.order_notional
        centre, half = self.skew_and_half_spread(s, lots)
        bid = _floor_tick(fair * (1 + (centre - half) / 1e4), s.tick)
        ask = _ceil_tick(fair * (1 + (centre + half) / 1e4), s.tick)
        # post-only: never cross the real book
        bid = min(bid, round(s.ask - s.tick, 10))
        ask = max(ask, round(s.bid + s.tick, 10))
        return QuoteTarget(
            bid=None if lots >= self.max_lots else bid,
            ask=None if lots <= -self.max_lots else ask,
            qty=self.order_notional / s.mid,
        )


def _floor_tick(price: float, tick: float) -> float:
    return round(math.floor(price / tick + 1e-9) * tick, 10)


def _ceil_tick(price: float, tick: float) -> float:
    return round(math.ceil(price / tick - 1e-9) * tick, 10)
