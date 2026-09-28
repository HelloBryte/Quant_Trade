"""Simulated matching for our own virtual orders on top of real market data.

Our orders never reach the real exchange, so the simulator decides when they
*would* have been filled. All orders are post-only limit orders (we are the
maker). The rules, checked on every market event:

1. Latency. A new order or a cancel submitted at t takes effect at
   t + latency. A cancel can therefore lose the race against a fill, which is
   exactly how a slow market maker gets picked off.
2. Post-only. An order that would cross the spread on arrival is rejected.
3. Fills:
   - "through": a trade prints at a price worse for the aggressor than ours
     (a sell prints below our bid). By price priority we would have been
     hit first, so we fill completely.
   - "cross": the real book shows an opposite quote at or through our price
     (best ask <= our bid). That seller would have traded with us, so we
     fill up to the displayed size.
   - "queue": a trade prints exactly at our price. It first eats the
     estimated queue ahead of us; whatever is left fills us.
4. Queue estimate. On arrival we join the back of the visible queue at our
   price: 0 if we improve on the best price, the displayed size if we join
   an existing level, unknown (infinite) if the level is deeper than the
   depth snapshot. Afterwards the estimate only shrinks: capped by the
   displayed level size (people ahead of us cancelled) and reduced by trades
   at our price.

Simplifications, documented in the README: our orders are assumed too small
to move the market, and nobody reacts to them.
"""
from __future__ import annotations

import heapq
import math
from dataclasses import dataclass

from .events import BUY, SELL, Depth, Quote, Trade

PENDING, ACTIVE, FILLED, CANCELED, REJECTED = "pending", "active", "filled", "canceled", "rejected"
_EPS = 1e-12


@dataclass(slots=True)
class Order:
    oid: int
    side: int
    px: int  # price in ticks
    qty: float
    ts_submit: int
    remaining: float
    status: str = PENDING
    ts_active: int = 0
    queue_ahead: float = math.inf
    cancel_sent: bool = False


@dataclass(slots=True)
class Fill:
    ts: int
    oid: int
    side: int
    price: float
    qty: float
    fee: float
    mid: float  # mid of the real book at fill time
    kind: str  # "through" | "cross" | "queue"
    position: float  # position after this fill
    ts_submit: int  # when the filled order was sent


class SimExchange:
    def __init__(self, tick: float, latency_ns: int, maker_fee_bps: float = 0.0):
        self.tick = tick
        self.latency_ns = latency_ns
        self.fee_rate = maker_fee_bps * 1e-4
        self.orders: dict[int, Order] = {}  # pending or active only
        self._actions: list[tuple[int, int, str, int]] = []  # (due_ts, seq, kind, oid)
        self._seq = 0
        # real book, prices in ticks
        self.bid = self.ask = 0
        self.bid_qty = self.ask_qty = 0.0
        self.has_book = False
        self._depth: dict[int, dict[int, float]] = {BUY: {}, SELL: {}}
        self._deepest: dict[int, int | None] = {BUY: None, SELL: None}
        # account
        self.position = 0.0
        self.cash = 0.0
        self.fees = 0.0
        self.fills: list[Fill] = []
        self.n_submitted = self.n_cancel_sent = self.n_canceled = self.n_rejected = 0

    # ----------------------------------------------------------------- helpers
    def to_ticks(self, price: float) -> int:
        return round(price / self.tick)

    @property
    def mid(self) -> float:
        return 0.5 * (self.bid + self.ask) * self.tick

    def working(self, side: int) -> list[Order]:
        """Orders on ``side`` that we have not asked to cancel."""
        return [o for o in self.orders.values() if o.side == side and not o.cancel_sent]

    # ------------------------------------------------------------- order entry
    def submit(self, ts: int, side: int, price: float, qty: float) -> int:
        self._seq += 1
        oid = self._seq
        self.orders[oid] = Order(oid, side, self.to_ticks(price), qty, ts, qty)
        heapq.heappush(self._actions, (ts + self.latency_ns, self._seq, "new", oid))
        self.n_submitted += 1
        return oid

    def cancel(self, ts: int, oid: int) -> None:
        o = self.orders.get(oid)
        if o is None or o.cancel_sent:
            return
        o.cancel_sent = True
        self._seq += 1
        heapq.heappush(self._actions, (ts + self.latency_ns, self._seq, "cancel", oid))
        self.n_cancel_sent += 1

    def advance(self, ts: int) -> None:
        """Apply every order action that has reached the exchange by ``ts``."""
        while self._actions and self._actions[0][0] <= ts:
            due, _, kind, oid = heapq.heappop(self._actions)
            o = self.orders.get(oid)
            if o is None:
                continue  # already filled
            if kind == "new":
                self._activate(o, due)
            else:
                o.status = CANCELED
                del self.orders[oid]
                self.n_canceled += 1

    def _activate(self, o: Order, ts: int) -> None:
        crosses = self.has_book and (o.px >= self.ask if o.side == BUY else o.px <= self.bid)
        if not self.has_book or crosses:
            o.status = REJECTED
            del self.orders[o.oid]
            self.n_rejected += 1
            return
        o.status = ACTIVE
        o.ts_active = ts
        o.queue_ahead = self._initial_queue(o)

    def _initial_queue(self, o: Order) -> float:
        best, best_qty = (self.bid, self.bid_qty) if o.side == BUY else (self.ask, self.ask_qty)
        better = o.px > best if o.side == BUY else o.px < best
        if better:
            return 0.0
        if o.px == best:
            return best_qty
        return self._depth_level(o.side, o.px)

    def _depth_level(self, side: int, px: int) -> float:
        deepest = self._deepest[side]
        if deepest is None:
            return math.inf
        beyond = px < deepest if side == BUY else px > deepest
        return math.inf if beyond else self._depth[side].get(px, 0.0)

    # ------------------------------------------------------------ market data
    def on_quote(self, q: Quote) -> None:
        self.bid, self.ask = self.to_ticks(q.bid), self.to_ticks(q.ask)
        self.bid_qty, self.ask_qty = q.bid_qty, q.ask_qty
        self.has_book = True
        for o in self._active():
            if o.side == BUY:
                if self.ask <= o.px:
                    self._fill(o, q.ts, min(o.remaining, q.ask_qty), "cross")
                elif o.px > self.bid:
                    o.queue_ahead = 0.0
                elif o.px == self.bid:
                    o.queue_ahead = min(o.queue_ahead, q.bid_qty)
            else:
                if self.bid >= o.px:
                    self._fill(o, q.ts, min(o.remaining, q.bid_qty), "cross")
                elif o.px < self.ask:
                    o.queue_ahead = 0.0
                elif o.px == self.ask:
                    o.queue_ahead = min(o.queue_ahead, q.ask_qty)

    def on_depth(self, d: Depth) -> None:
        for side, levels in ((BUY, d.bids), (SELL, d.asks)):
            book = {self.to_ticks(p): q for p, q in levels}
            self._depth[side] = book
            self._deepest[side] = (min(book) if side == BUY else max(book)) if book else None
        # Depth snapshots lag the real-time best quote, so they only refine
        # queues strictly behind the current best price.
        for o in self._active():
            behind = o.px < self.bid if o.side == BUY else o.px > self.ask
            if behind:
                o.queue_ahead = min(o.queue_ahead, self._depth_level(o.side, o.px))

    def on_trade(self, t: Trade) -> None:
        px = self.to_ticks(t.price)
        for o in self._active():
            if o.side == BUY and t.side == SELL:
                if px < o.px:
                    self._fill(o, t.ts, o.remaining, "through")
                elif px == o.px:
                    self._queue_fill(o, t)
            elif o.side == SELL and t.side == BUY:
                if px > o.px:
                    self._fill(o, t.ts, o.remaining, "through")
                elif px == o.px:
                    self._queue_fill(o, t)

    # ------------------------------------------------------------------ fills
    def _active(self) -> list[Order]:
        return [o for o in self.orders.values() if o.status == ACTIVE]

    def _queue_fill(self, o: Order, t: Trade) -> None:
        o.queue_ahead -= t.qty
        if o.queue_ahead < 0:
            qty = min(o.remaining, -o.queue_ahead)
            o.queue_ahead = 0.0
            self._fill(o, t.ts, qty, "queue")

    def _fill(self, o: Order, ts: int, qty: float, kind: str) -> None:
        if qty <= _EPS:
            return
        price = o.px * self.tick
        fee = self.fee_rate * price * qty
        o.remaining -= qty
        self.position += o.side * qty
        self.cash -= o.side * qty * price
        self.fees += fee
        self.fills.append(Fill(ts, o.oid, o.side, price, qty, fee, self.mid, kind, self.position, o.ts_submit))
        if o.remaining <= _EPS:
            o.status = FILLED
            del self.orders[o.oid]
