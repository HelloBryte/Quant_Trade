"""Event-driven engine shared by live paper trading and replay backtests.

For every market event:
  1. let order actions that have reached the exchange take effect (latency),
  2. update the real book and check our resting orders for fills,
  3. update signals (volatility, perp-spot gap),
  4. if something relevant changed, ask the strategy for new quotes and
     cancel/replace orders that are too far from the target.
"""
from __future__ import annotations

from array import array
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .events import BUY, SELL, Depth, Event, Quote, Trade
from .exchange import SimExchange
from .signals import BasisGap, EwmaVol, imbalance
from .strategies import MarketState, QuoteTarget, Strategy


@dataclass
class EngineConfig:
    quote_inst: str
    tick: float
    ref_inst: str | None = None
    latency_ms: float = 50.0  # decision -> order live at the exchange
    maker_fee_bps: float = 0.0  # negative = rebate
    warmup_s: float = 60.0  # let signals settle before quoting
    min_order_interval_ms: float = 100.0  # per side, crude rate limit
    snapshot_s: float = 1.0
    vol_halflife_s: float = 60.0
    vol_prior_bps: float = 1.0
    basis_halflife_s: float = 120.0


@dataclass
class RunResult:
    fills: pd.DataFrame
    snapshots: pd.DataFrame
    mid_ts: np.ndarray  # every change of the quoted market's mid
    mid: np.ndarray
    meta: dict = field(default_factory=dict)


class Engine:
    def __init__(self, cfg: EngineConfig, strategy: Strategy):
        self.cfg = cfg
        self.strategy = strategy
        self.ex = SimExchange(cfg.tick, int(cfg.latency_ms * 1e6), cfg.maker_fee_bps)
        self.vol = EwmaVol(cfg.vol_halflife_s, prior_bps=cfg.vol_prior_bps)
        self.gap = BasisGap(cfg.basis_halflife_s)
        self.quote: Quote | None = None
        self.ref_mid: float | None = None
        self.target: QuoteTarget | None = None
        self.t0: int | None = None
        self.ts = 0
        self.n_events = 0
        self._warmup_ns = int(cfg.warmup_s * 1e9)
        self._interval_ns = int(cfg.min_order_interval_ms * 1e6)
        self._snap_ns = int(cfg.snapshot_s * 1e9)
        self._next_snap = 0
        self._last_submit = {BUY: -(1 << 62), SELL: -(1 << 62)}
        self._dirty = False
        self._mid_ts = array("q")
        self._mid = array("d")
        self._snaps: list[tuple] = []

    # ------------------------------------------------------------------ loop
    def on_event(self, ev: Event) -> None:
        ts = ev.ts
        if self.t0 is None:
            self.t0 = self._next_snap = ts
        self.ts = ts
        self.n_events += 1
        self.ex.advance(ts)
        n_fills = len(self.ex.fills)
        requote = False

        if ev.inst == self.cfg.quote_inst:
            if isinstance(ev, Quote):
                prev = self.quote
                self.quote = ev
                self.ex.on_quote(ev)
                if prev is None or ev.bid != prev.bid or ev.ask != prev.ask:
                    mid = ev.mid
                    self._mid_ts.append(ts)
                    self._mid.append(mid)
                    self.vol.update(ts, mid)
                    if self.ref_mid is not None:
                        self.gap.update(ts, mid, self.ref_mid)
                    requote = True
            elif isinstance(ev, Trade):
                self.ex.on_trade(ev)
            elif isinstance(ev, Depth):
                self.ex.on_depth(ev)
        elif ev.inst == self.cfg.ref_inst and isinstance(ev, Quote):
            m = ev.mid
            if m != self.ref_mid:
                self.ref_mid = m
                if self.quote is not None:
                    self.gap.update(ts, self.quote.mid, m)
                    requote = True

        if len(self.ex.fills) != n_fills:
            requote = True
        if (requote or self._dirty) and self.quote is not None and ts - self.t0 >= self._warmup_ns:
            self.target = self.strategy.quote(self._state(ts))
            self._sync(ts, self.target)
        if ts >= self._next_snap and self.quote is not None:
            self._snapshot(ts)
            self._next_snap = ts + self._snap_ns

    def _state(self, ts: int) -> MarketState:
        q = self.quote
        return MarketState(
            ts=ts, bid=q.bid, ask=q.ask, bid_qty=q.bid_qty, ask_qty=q.ask_qty, tick=self.cfg.tick,
            sigma_bps=self.vol.sigma_bps, gap_bps=self.gap.gap if self.cfg.ref_inst else 0.0,
            imbalance=imbalance(q.bid_qty, q.ask_qty), position=self.ex.position,
        )

    def _sync(self, ts: int, target: QuoteTarget) -> None:
        """Cancel/replace so each side has one working order near the target."""
        ex = self.ex
        tol = self.strategy.requote_bps * 1e-4 * self.quote.mid
        self._dirty = False
        for side, px in ((BUY, target.bid), (SELL, target.ask)):
            keep = None
            for o in ex.working(side):
                if px is not None and keep is None and abs(o.px * ex.tick - px) <= tol + 1e-12:
                    keep = o
                else:
                    ex.cancel(ts, o.oid)
            if px is None or keep is not None:
                continue
            if ts - self._last_submit[side] < self._interval_ns:
                self._dirty = True  # rate limited: try again on the next event
                continue
            ex.submit(ts, side, px, target.qty)
            self._last_submit[side] = ts

    def _snapshot(self, ts: int) -> None:
        ex, t = self.ex, self.target
        mid = self.quote.mid
        self._snaps.append((ts, mid, ex.position, ex.cash, ex.fees, ex.cash + ex.position * mid,
                            t.bid if t else np.nan, t.ask if t else np.nan, self.vol.sigma_bps, self.gap.gap))

    # --------------------------------------------------------------- results
    def result(self) -> RunResult:
        if self.quote is not None:
            self._snapshot(self.ts)
        fills = pd.DataFrame([_fill_dict(f) for f in self.ex.fills], columns=list(_FILL_COLS))
        snaps = pd.DataFrame(self._snaps, columns=["ts", "mid", "position", "cash", "fees", "pnl_gross",
                                                   "bid", "ask", "sigma_bps", "gap_bps"])
        snaps["pnl_net"] = snaps["pnl_gross"] - snaps["fees"]
        ex = self.ex
        meta = {
            "strategy": self.strategy.name,
            "params": self.strategy.params(),
            "config": vars(self.cfg).copy(),
            "events": self.n_events,
            "start_ns": self.t0,
            "end_ns": self.ts,
            "orders_submitted": ex.n_submitted,
            "orders_canceled": ex.n_canceled,
            "orders_rejected": ex.n_rejected,
            "final_position": ex.position,
        }
        return RunResult(fills, snaps, np.frombuffer(self._mid_ts, dtype=np.int64).copy(),
                         np.frombuffer(self._mid, dtype=np.float64).copy(), meta)


_FILL_COLS = ("ts", "oid", "side", "price", "qty", "fee", "mid", "kind", "position", "ts_submit")


def _fill_dict(f) -> dict:
    return {c: getattr(f, c) for c in _FILL_COLS}


def run(events, cfg: EngineConfig, strategy: Strategy) -> RunResult:
    eng = Engine(cfg, strategy)
    for ev in events:
        eng.on_event(ev)
    return eng.result()
