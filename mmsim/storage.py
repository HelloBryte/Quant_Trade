"""Record events to a gzipped JSON-lines file and replay them.

File layout: the first line is a metadata object, every following line is a
compact JSON array:

    ["Q", ts, inst, bid, bid_qty, ask, ask_qty]
    ["T", ts, inst, price, qty, side, ts_exch]
    ["D", ts, inst, [[px, qty], ...], [[px, qty], ...]]
"""
from __future__ import annotations

import gzip
import json
import sys
import zlib
from pathlib import Path
from typing import Iterable, Iterator

from .events import Depth, Event, Quote, Trade


def encode(ev: Event) -> list:
    if isinstance(ev, Quote):
        return ["Q", ev.ts, ev.inst, ev.bid, ev.bid_qty, ev.ask, ev.ask_qty]
    if isinstance(ev, Trade):
        return ["T", ev.ts, ev.inst, ev.price, ev.qty, ev.side, ev.ts_exch]
    if isinstance(ev, Depth):
        return ["D", ev.ts, ev.inst, ev.bids, ev.asks]
    raise TypeError(f"unknown event {ev!r}")


def decode(row: list) -> Event:
    kind = row[0]
    if kind == "Q":
        return Quote(*row[1:])
    if kind == "T":
        return Trade(*row[1:])
    if kind == "D":
        return Depth(row[1], row[2], [tuple(x) for x in row[3]], [tuple(x) for x in row[4]])
    raise ValueError(f"unknown row kind {kind!r}")


class Recorder:
    """Append events to ``path``; flushes every ``flush_every`` events."""

    def __init__(self, path: str | Path, meta: dict, flush_every: int = 5000):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._f = gzip.open(self.path, "wt", encoding="utf-8")
        self._f.write(json.dumps({"type": "meta", **meta}) + "\n")
        self._n = 0
        self._flush_every = flush_every

    def write(self, ev: Event) -> None:
        self._f.write(json.dumps(encode(ev), separators=(",", ":")) + "\n")
        self._n += 1
        if self._n % self._flush_every == 0:
            self._f.flush()

    @property
    def count(self) -> int:
        return self._n

    def close(self) -> None:
        self._f.close()


def read_meta(path: str | Path) -> dict:
    with gzip.open(path, "rt", encoding="utf-8") as f:
        meta = json.loads(f.readline())
    meta.pop("type", None)
    return meta


def replay(path: str | Path) -> Iterator[Event]:
    """Yield events in file order. A truncated tail (killed recorder) is skipped."""
    with gzip.open(path, "rt", encoding="utf-8") as f:
        f.readline()  # meta
        try:
            for line in f:
                try:
                    yield decode(json.loads(line))
                except json.JSONDecodeError:
                    break  # partial last line
        except (EOFError, zlib.error, gzip.BadGzipFile):
            print(f"warning: {path} is truncated, replayed up to the damaged tail", file=sys.stderr)


def clip(events: Iterable[Event], skip_minutes: float = 0.0, max_minutes: float | None = None) -> Iterator[Event]:
    """Keep events in [start + skip, start + skip + max) where start is the first event."""
    start = None
    for ev in events:
        if start is None:
            start = ev.ts + int(skip_minutes * 6e10)
        if ev.ts < start:
            continue
        if max_minutes is not None and ev.ts >= start + int(max_minutes * 6e10):
            break
        yield ev


def load(path: str | Path) -> tuple[dict, list[Event]]:
    return read_meta(path), list(replay(path))
