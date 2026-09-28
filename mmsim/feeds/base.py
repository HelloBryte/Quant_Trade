"""Shared websocket plumbing: reconnecting readers merged into one queue."""
from __future__ import annotations

import asyncio
import json
import logging
import ssl
import time
import urllib.request
from typing import AsyncIterator, Awaitable, Callable

import websockets

from ..events import Event

log = logging.getLogger(__name__)

Parser = Callable[[dict, int], list[Event]]


def http_get_json(url: str, timeout: float = 10.0) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "mmsim/0.1"})
    with urllib.request.urlopen(req, timeout=timeout, context=ssl.create_default_context()) as r:
        return json.loads(r.read())


async def _reader(
    url: str,
    parse: Parser,
    queue: asyncio.Queue,
    on_open: Callable[[websockets.ClientConnection], Awaitable[None]] | None = None,
    keepalive: Callable[[websockets.ClientConnection], Awaitable[None]] | None = None,
) -> None:
    backoff = 1.0
    while True:
        try:
            async with websockets.connect(url, open_timeout=15, max_size=2**22) as ws:
                if on_open:
                    await on_open(ws)
                ka = asyncio.create_task(keepalive(ws)) if keepalive else None
                backoff = 1.0
                try:
                    async for raw in ws:
                        ts = time.time_ns()
                        if raw == "pong":
                            continue
                        for ev in parse(json.loads(raw), ts):
                            queue.put_nowait(ev)
                finally:
                    if ka:
                        ka.cancel()
        except asyncio.CancelledError:
            raise
        except Exception as e:  # network errors: reconnect with backoff
            log.warning("feed %s disconnected (%s: %s); reconnecting in %.0fs", url, type(e).__name__, e, backoff)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 30.0)


async def merged(readers: list[Callable[[asyncio.Queue], Awaitable[None]]]) -> AsyncIterator[Event]:
    """Run several readers concurrently and yield their events in arrival order."""
    queue: asyncio.Queue = asyncio.Queue()
    tasks = [asyncio.create_task(r(queue)) for r in readers]
    try:
        while True:
            yield await queue.get()
    finally:
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


def reader(url: str, parse: Parser, on_open=None, keepalive=None):
    return lambda q: _reader(url, parse, q, on_open, keepalive)
