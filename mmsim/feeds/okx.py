"""OKX public market data (spot quoted market, USDT-margined swap as reference)."""
from __future__ import annotations

import asyncio
import json

from ..events import BUY, SELL, Depth, Event, Quote, Trade
from .base import http_get_json, merged, reader

VENUE = "okx"
WS = "wss://ws.okx.com/ws/v5/public"
INFO = "https://www.okx.com/api/v5/public/instruments?instType=SPOT&instId="


def _spot_id(symbol: str) -> str:
    s = symbol.upper()
    if "-" not in s and s.endswith("USDT"):
        s = s[:-4] + "-USDT"
    return s


def spot_inst(symbol: str) -> str:
    return f"okx-spot:{_spot_id(symbol)}"


def perp_inst(symbol: str) -> str:
    return f"okx-perp:{_spot_id(symbol)}-SWAP"


def fetch_tick_size(symbol: str) -> float:
    info = http_get_json(INFO + _spot_id(symbol))
    return float(info["data"][0]["tickSz"])


def _inst(inst_id: str) -> str:
    return f"okx-perp:{inst_id}" if inst_id.endswith("-SWAP") else f"okx-spot:{inst_id}"


def _levels(rows) -> list[tuple[float, float]]:
    return [(float(r[0]), float(r[1])) for r in rows]


def parse(msg: dict, ts: int) -> list[Event]:
    arg, data = msg.get("arg", {}), msg.get("data")
    if not data:
        return []
    chan, inst = arg.get("channel"), _inst(arg.get("instId", ""))
    out: list[Event] = []
    for d in data:
        if chan == "bbo-tbt":
            if d["bids"] and d["asks"]:
                b, a = d["bids"][0], d["asks"][0]
                out.append(Quote(ts, inst, float(b[0]), float(b[1]), float(a[0]), float(a[1])))
        elif chan == "trades":
            side = BUY if d["side"] == "buy" else SELL
            out.append(Trade(ts, inst, float(d["px"]), float(d["sz"]), side, int(d["ts"]) * 1_000_000))
        elif chan == "books5":
            out.append(Depth(ts, inst, _levels(d["bids"]), _levels(d["asks"])))
    return out


def stream(symbol: str, with_ref: bool = True):
    spot = _spot_id(symbol)
    args = [
        {"channel": "bbo-tbt", "instId": spot},
        {"channel": "trades", "instId": spot},
        {"channel": "books5", "instId": spot},
    ]
    if with_ref:
        args.append({"channel": "bbo-tbt", "instId": spot + "-SWAP"})

    async def on_open(ws):
        await ws.send(json.dumps({"op": "subscribe", "args": args}))

    async def keepalive(ws):  # OKX drops idle connections after 30 s
        while True:
            await asyncio.sleep(20)
            await ws.send("ping")

    return merged([reader(WS, parse, on_open, keepalive)])
