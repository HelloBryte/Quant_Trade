"""The three strategy versions compared in this project.

v0 FixedSpread            symmetric quotes at mid +/- a constant half spread
v1 AvellanedaStoikov      inventory-aware quotes (Avellaneda & Stoikov, 2008)
v2 AvellanedaStoikovSignal v1 around a fair value shifted by short-term signals
"""
from __future__ import annotations

import math

from .base import MarketState, Strategy


class FixedSpread(Strategy):
    """Baseline: no inventory control, no signal."""

    name = "fixed"

    def __init__(self, half_spread_bps: float = 1.0, **kw):
        super().__init__(**kw)
        self.half_spread_bps = half_spread_bps

    def skew_and_half_spread(self, s: MarketState, lots: float) -> tuple[float, float]:
        return 0.0, self.half_spread_bps


class AvellanedaStoikov(Strategy):
    """Reservation price and optimal spread from Avellaneda & Stoikov (2008),
    written in bps of mid with inventory q measured in orders ("lots"):

        reservation shift = -q * gamma * sigma^2 * tau
        half spread       = gamma * sigma^2 * tau / 2 + ln(1 + gamma / k) / gamma

    sigma: volatility in bps/sqrt(s), estimated online.
    gamma: risk aversion. Higher -> more skew per lot and wider quotes.
    k:     how fast fill probability decays with distance from mid (1/bps).
           As gamma -> 0 the second term tends to 1/k.
    tau:   risk horizon in seconds. The paper uses time to the end of the
           trading day; a continuously running crypto market maker uses a
           fixed rolling horizon instead.
    """

    name = "as"

    def __init__(self, gamma: float = 0.05, k: float = 1.0, tau_s: float = 30.0,
                 min_half_spread_bps: float = 0.2, **kw):
        super().__init__(**kw)
        self.gamma = gamma
        self.k = k
        self.tau_s = tau_s
        self.min_half_spread_bps = min_half_spread_bps

    def skew_and_half_spread(self, s: MarketState, lots: float) -> tuple[float, float]:
        risk = self.gamma * s.sigma_bps**2 * self.tau_s
        half = 0.5 * risk + math.log1p(self.gamma / self.k) / self.gamma
        return -lots * risk, max(self.min_half_spread_bps, half)


class AvellanedaStoikovSignal(AvellanedaStoikov):
    """v1, but quoting around a signal-adjusted fair value:

        fair = mid * (1 + (beta_gap * gap_bps + beta_imb * imbalance) / 1e4)

    gap_bps:   how far the perpetual future has moved away from its usual
               premium over spot. If the perp just jumped up, spot tends to
               follow.
    imbalance: top-of-book size imbalance. A thin ask and a thick bid mean
               the next mid move is more likely up.

    Shifting fair value moves both quotes together: when the signal says
    "up", our ask moves away from the buyers who are about to lift it and our
    bid moves closer to where the price is going. The betas are the slopes
    from ``mmsim research`` (future return in bps per unit of signal).
    """

    name = "as_signal"

    def __init__(self, beta_gap: float = 0.2, beta_imb: float = 0.3, **kw):
        super().__init__(**kw)
        self.beta_gap = beta_gap
        self.beta_imb = beta_imb

    def fair_value(self, s: MarketState) -> float:
        shift_bps = self.beta_gap * s.gap_bps + self.beta_imb * s.imbalance
        return s.mid * (1 + shift_bps / 1e4)
