"""Synthetic market with a known lead-lag, for tests and offline demos.

A latent "true" price follows a random walk. The perp mid tracks it
instantly; the spot mid catches up with a lag. A share of spot takers are
informed: they trade in the direction spot is about to move. A market maker
quoting spot therefore faces real adverse selection, and a perp-lead signal
has something to find.
"""
from __future__ import annotations

import math
import random

from .events import BUY, SELL, Depth, Event, Quote, Trade

QUOTE_INST = "synth-spot:TEST"
REF_INST = "synth-perp:TEST"


def generate(minutes: float = 10.0, seed: int = 0, start: float = 100.0, tick: float = 0.01,
             sigma_bps: float = 1.0, lag_s: float = 0.3, basis_bps: float = 2.0,
             trade_rate: float = 5.0, informed: float = 0.5) -> tuple[dict, list[Event]]:
    rng = random.Random(seed)
    dt_ns = 10_000_000  # 10 ms steps
    dt = dt_ns / 1e9
    step_sd = sigma_bps * 1e-4 * math.sqrt(dt)
    catch = 1 - math.exp(-dt / lag_s)
    ts = 1_700_000_000_000_000_000
    true = spot = start
    events: list[Event] = []
    last_bbo = None
    for i in range(int(minutes * 60 / dt)):
        ts += dt_ns
        true *= math.exp(rng.gauss(0, step_sd))
        spot += (true - spot) * catch
        perp_mid = true * (1 + basis_bps * 1e-4)
        events.append(Quote(ts, REF_INST, perp_mid - 0.05, 5.0, perp_mid + 0.05, 5.0))
        bid = math.floor(spot / tick) * tick
        bid, ask = round(bid, 10), round(bid + tick, 10)
        if (bid, ask) != last_bbo or rng.random() < 0.05:
            events.append(Quote(ts + 1, QUOTE_INST, bid, rng.uniform(0.5, 5), ask, rng.uniform(0.5, 5)))
            last_bbo = (bid, ask)
        if rng.random() < trade_rate * dt:
            if rng.random() < informed:
                side = BUY if true > spot else SELL
            else:
                side = BUY if rng.random() < 0.5 else SELL
            events.append(Trade(ts + 2, QUOTE_INST, ask if side == BUY else bid, rng.expovariate(1.0), side, ts))
        if i % 10 == 0:
            events.append(Depth(ts + 3, QUOTE_INST,
                                [(round(bid - j * tick, 10), rng.uniform(0.1, 3)) for j in range(10)],
                                [(round(ask + j * tick, 10), rng.uniform(0.1, 3)) for j in range(10)]))
    meta = {"venue": "synthetic", "symbol": "TEST", "quote_inst": QUOTE_INST, "ref_inst": REF_INST,
            "tick_size": tick, "started": "synthetic", "seed": seed}
    return meta, events
