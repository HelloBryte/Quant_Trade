"""Live sessions: record raw market data, or paper-trade a strategy in real time.

Paper trading drives exactly the same Engine as a backtest; the only
difference is that events come from the websocket instead of a file. Every
paper session also records its input stream, so it can be replayed later
with different parameters.
"""
from __future__ import annotations

import asyncio
import datetime as dt
import time
from pathlib import Path

from .feeds import get_feed
from .storage import Recorder


def session_meta(venue: str, symbol: str, with_ref: bool = True) -> dict:
    feed = get_feed(venue)
    return {
        "venue": venue,
        "symbol": symbol.upper(),
        "quote_inst": feed.spot_inst(symbol),
        "ref_inst": feed.perp_inst(symbol) if with_ref else None,
        "tick_size": feed.fetch_tick_size(symbol),
        "started": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
    }


async def _run(venue: str, symbol: str, minutes: float, on_event, on_tick=None, tick_s: float = 5.0) -> None:
    feed = get_feed(venue)
    deadline = time.monotonic() + minutes * 60
    next_tick = time.monotonic() + tick_s
    agen = feed.stream(symbol)
    # Keep one pending __anext__ across timeouts: cancelling it (as wait_for
    # would) closes the generator and ends the session on a quiet feed.
    pending: asyncio.Future | None = None
    try:
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            if pending is None:
                pending = asyncio.ensure_future(agen.__anext__())
            done, _ = await asyncio.wait({pending}, timeout=min(remaining, tick_s))
            if done:
                fut, pending = pending, None
                try:
                    ev = fut.result()
                except StopAsyncIteration:
                    break
                on_event(ev)
            if on_tick and time.monotonic() >= next_tick:
                on_tick()
                next_tick += tick_s
    finally:
        if pending is not None:
            pending.cancel()
            await asyncio.gather(pending, return_exceptions=True)
        await agen.aclose()


def record(venue: str, symbol: str, minutes: float, out: str | Path) -> Path:
    meta = session_meta(venue, symbol)
    rec = Recorder(out, meta)
    t0 = time.monotonic()

    def status():
        print(f"[{dt.datetime.now():%H:%M:%S}] {rec.count:,} events in {time.monotonic() - t0:.0f}s", flush=True)

    try:
        asyncio.run(_run(venue, symbol, minutes, rec.write, status, tick_s=30.0))
    except KeyboardInterrupt:
        pass
    finally:
        rec.close()
    print(f"saved {rec.count:,} events to {out}")
    return Path(out)


def paper(venue: str, symbol: str, minutes: float, strategies, record_to: str | Path, status_s: float = 10.0,
          **engine_kw) -> dict:
    """Paper-trade one or more strategies side by side on the same live feed.

    Each strategy gets its own Engine (own virtual orders, position and PnL)
    but they all see the identical event stream, so the comparison is fair.
    Returns {strategy name: RunResult}.
    """
    from .engine import Engine, EngineConfig

    meta = session_meta(venue, symbol)
    cfg = EngineConfig(quote_inst=meta["quote_inst"], ref_inst=meta["ref_inst"], tick=meta["tick_size"], **engine_kw)
    engines = {st.name: Engine(cfg, st) for st in strategies}
    engine_cfg = {k: v for k, v in vars(cfg).items() if k not in ("quote_inst", "ref_inst", "tick")}
    rec = Recorder(record_to, {**meta, "paper": {n: e.strategy.params() for n, e in engines.items()},
                               "latency_ms": cfg.latency_ms, "engine": engine_cfg})

    def on_event(ev):
        rec.write(ev)
        for eng in engines.values():
            eng.on_event(ev)

    def status():
        for name, eng in engines.items():
            ex, q, t = eng.ex, eng.quote, eng.target
            if q is None:
                return
            mid = q.mid
            warm = (eng.ts - eng.t0) / 1e9 < cfg.warmup_s
            quotes = "warming up" if warm or t is None else f"bid {_bps(t.bid, mid)} ask {_bps(t.ask, mid)}"
            pnl = ex.cash + ex.position * mid
            print(f"[{dt.datetime.now():%H:%M:%S}] {name:9s} mid {mid:,.2f} | {quotes} | pos {ex.position:+.5f} "
                  f"| fills {len(ex.fills)} | orders {ex.n_submitted} | gross {pnl:+.3f} net {pnl - ex.fees:+.3f} "
                  f"| vol {eng.vol.sigma_bps:.2f}bp gap {eng.gap.gap:+.2f}bp", flush=True)

    try:
        asyncio.run(_run(venue, symbol, minutes, on_event, status, tick_s=status_s))
    except KeyboardInterrupt:
        pass
    finally:
        rec.close()
    return {name: eng.result() for name, eng in engines.items()}


def _bps(px, mid) -> str:
    return "  off  " if px is None else f"{(px / mid - 1) * 1e4:+.2f}bp"
