"""Online estimators the strategies quote on. All outputs are in basis points."""
from __future__ import annotations

import math


class EwmaVol:
    """EWMA volatility of mid log-returns, in bps per sqrt(second).

    Returns are taken between mid samples at least ``sample_s`` apart and
    normalised by the elapsed time, so quiet periods are handled correctly.
    """

    def __init__(self, halflife_s: float = 60.0, sample_s: float = 1.0, prior_bps: float = 1.0):
        self.halflife_s = halflife_s
        self.sample_ns = int(sample_s * 1e9)
        self.var = prior_bps**2
        self.n = 0
        self._ts: int | None = None
        self._mid = 0.0

    def update(self, ts: int, mid: float) -> None:
        if self._ts is None:
            self._ts, self._mid = ts, mid
            return
        if ts - self._ts < self.sample_ns:
            return
        dt = (ts - self._ts) / 1e9
        r = math.log(mid / self._mid) * 1e4
        a = 1.0 - 0.5 ** (dt / self.halflife_s)
        self.var += a * (r * r / dt - self.var)
        self._ts, self._mid = ts, mid
        self.n += 1

    @property
    def sigma_bps(self) -> float:
        return math.sqrt(self.var)


class BasisGap:
    """How far the reference market (perp) has moved away from its usual
    premium over the quoted market (spot), in bps.

    basis = ref_mid / quote_mid - 1 fluctuates around a slowly moving level
    (funding, carry). Its EWMA tracks that level; the gap is today's basis
    minus the EWMA. If the perp moves first, the gap turns positive before
    spot catches up, which makes it a short-horizon predictor of spot.
    """

    def __init__(self, halflife_s: float = 120.0):
        self.halflife_s = halflife_s
        self.level: float | None = None
        self.gap = 0.0
        self._ts = 0

    def update(self, ts: int, quote_mid: float, ref_mid: float) -> None:
        basis = (ref_mid / quote_mid - 1.0) * 1e4
        if self.level is None:
            self.level, self._ts = basis, ts
            return
        a = 1.0 - 0.5 ** (max(ts - self._ts, 0) / 1e9 / self.halflife_s)
        self.level += a * (basis - self.level)
        self._ts = ts
        self.gap = basis - self.level


def imbalance(bid_qty: float, ask_qty: float) -> float:
    """Top-of-book size imbalance in [-1, 1]; positive means more buyers."""
    tot = bid_qty + ask_qty
    return (bid_qty - ask_qty) / tot if tot > 0 else 0.0
