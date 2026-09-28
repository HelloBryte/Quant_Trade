"""Binance public market data.

Quoted market: spot, via the market-data-only endpoint data-stream.binance.vision
(bookTicker = real-time best bid/ask, trade = every print, depth20 = top-20
snapshot every 100 ms). Reference market: USD-M perpetual bookTicker.
"""
from __future__ import annotations

from ..events import BUY, SELL, Depth, Event, Quote, Trade
from .base import http_get_json, merged, reader

VENUE = "binance"
SPOT_WS = "wss://data-stream.binance.vision/stream?streams="
PERP_WS = "wss://fstream.binance.com/stream?streams="
SPOT_INFO = "https://data-api.binance.vision/api/v3/exchangeInfo?symbol="


def spot_inst(symbol: str) -> str:
    return f"binance-spot:{symbol.upper()}"


def perp_inst(symbol: str) -> str:
    return f"binance-perp:{symbol.upper()}"


def fetch_tick_size(symbol: str) -> float:
    info = http_get_json(SPOT_INFO + symbol.upper())
    for f in info["symbols"][0]["filters"]:
        if f["filterType"] == "PRICE_FILTER":
            return float(f["tickSize"])
    raise RuntimeError(f"no PRICE_FILTER for {symbol}")


def _levels(rows) -> list[tuple[float, float]]:
    return [(float(p), float(q)) for p, q in rows]


def parse_spot(msg: dict, ts: int) -> list[Event]:
    stream, d = msg.get("stream", ""), msg.get("data", {})
    inst = spot_inst(d.get("s", stream.split("@")[0]))
    if stream.endswith("@bookTicker"):
        return [Quote(ts, inst, float(d["b"]), float(d["B"]), float(d["a"]), float(d["A"]))]
    if stream.endswith("@trade"):
        # m = buyer is the maker, i.e. the aggressor was the seller
        side = SELL if d["m"] else BUY
        return [Trade(ts, inst, float(d["p"]), float(d["q"]), side, int(d["T"]) * 1_000_000)]
    if "@depth" in stream:
        return [Depth(ts, inst, _levels(d["bids"]), _levels(d["asks"]))]
    return []


def parse_perp(msg: dict, ts: int) -> list[Event]:
    stream, d = msg.get("stream", ""), msg.get("data", {})
    if stream.endswith("@bookTicker"):
        return [Quote(ts, perp_inst(d["s"]), float(d["b"]), float(d["B"]), float(d["a"]), float(d["A"]))]
    return []


def stream(symbol: str, with_ref: bool = True):
    s = symbol.lower()
    readers = [reader(SPOT_WS + f"{s}@bookTicker/{s}@trade/{s}@depth20@100ms", parse_spot)]
    if with_ref:
        readers.append(reader(PERP_WS + f"{s}@bookTicker", parse_perp))
    return merged(readers)
