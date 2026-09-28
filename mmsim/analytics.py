"""Turn a run into the numbers a market-making desk actually looks at.

PnL decomposition (exact identity, all in quote currency):

    gross PnL      = cash + position * final_mid
                   = spread capture + inventory PnL
    spread capture = sum over fills of side * qty * (mid_at_fill - price)
                     what we earned relative to mid at the moment of the fill
    inventory PnL  = sum over fills of side * qty * (final_mid - mid_at_fill)
                     what the position we were left holding made or lost
    net PnL        = gross PnL - fees

Markout at horizon h (bps, qty-weighted):

    side * (mid(t_fill + h) - price) / price * 1e4

h = 0 is the edge at the moment of the fill. If the curve falls as h grows,
the people trading with us knew where the price was going: adverse selection.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .engine import RunResult

MARKOUT_HORIZONS_S = (0, 0.1, 0.5, 1, 2, 5, 10, 30, 60)
# Illustrative maker fee levels in bps (negative = rebate). Check the venue's
# current schedule before quoting these as facts.
FEE_SCENARIOS_BPS = {
    "retail spot (10 bp)": 10.0,
    "retail perp (2 bp)": 2.0,
    "zero fee": 0.0,
    "MM rebate (-0.5 bp)": -0.5,
}


def mid_at(result: RunResult, ts: np.ndarray) -> np.ndarray:
    """Last known mid at each timestamp (as-of lookup)."""
    idx = np.searchsorted(result.mid_ts, ts, side="right") - 1
    return result.mid[np.clip(idx, 0, len(result.mid) - 1)]


def markouts(result: RunResult, horizons=MARKOUT_HORIZONS_S) -> pd.DataFrame:
    f = result.fills
    end = result.meta.get("end_ns") or (result.mid_ts[-1] if len(result.mid_ts) else 0)
    rows = []
    for h in horizons:
        if f.empty:
            rows.append((h, np.nan, 0))
            continue
        t = f["ts"].to_numpy() + int(h * 1e9)
        ok = t <= end  # drop fills too close to the end of the data
        if not ok.any():
            rows.append((h, np.nan, 0))
            continue
        side, px, qty = f["side"].to_numpy()[ok], f["price"].to_numpy()[ok], f["qty"].to_numpy()[ok]
        m = mid_at(result, t[ok])
        bps = side * (m - px) / px * 1e4
        rows.append((h, float(np.average(bps, weights=qty)), int(ok.sum())))
    return pd.DataFrame(rows, columns=["horizon_s", "markout_bps", "n"])


def decompose(result: RunResult) -> dict:
    f, s = result.fills, result.snapshots
    final_mid = float(s["mid"].iloc[-1]) if len(s) else np.nan
    if f.empty:
        return dict(gross=0.0, spread_capture=0.0, inventory=0.0, fees=0.0, net=0.0, notional=0.0)
    side, px, qty, mid = (f[c].to_numpy() for c in ("side", "price", "qty", "mid"))
    spread = float(np.sum(side * qty * (mid - px)))
    inventory = float(np.sum(side * qty * (final_mid - mid)))
    fees = float(f["fee"].sum())
    return dict(gross=spread + inventory, spread_capture=spread, inventory=inventory,
                fees=fees, net=spread + inventory - fees, notional=float(np.sum(px * qty)))


def summarize(result: RunResult) -> dict:
    f, s, meta = result.fills, result.snapshots, result.meta
    d = decompose(result)
    hours = (meta["end_ns"] - meta["start_ns"]) / 3.6e12 if meta.get("start_ns") else np.nan
    notional = d["notional"]
    order_notional = meta["params"].get("order_notional", np.nan)
    lots = s["position"] * s["mid"] / order_notional
    mk = markouts(result).set_index("horizon_s")["markout_bps"]
    pnl_min = s.set_index(pd.to_datetime(s["ts"], unit="ns"))["pnl_gross"].resample("1min").last().diff().dropna()
    out = {
        "strategy": meta["strategy"],
        "latency_ms": meta["config"]["latency_ms"],
        "hours": hours,
        "fills": len(f),
        "buys": int((f["side"] > 0).sum()) if len(f) else 0,
        "sells": int((f["side"] < 0).sum()) if len(f) else 0,
        "fill_kinds": f["kind"].value_counts().to_dict() if len(f) else {},
        "orders": meta["orders_submitted"],
        "fill_ratio": len(f) / meta["orders_submitted"] if meta["orders_submitted"] else np.nan,
        "notional": notional,
        **{f"pnl_{k}": v for k, v in d.items() if k != "notional"},
        "spread_capture_bps": d["spread_capture"] / notional * 1e4 if notional else np.nan,
        "inventory_bps": d["inventory"] / notional * 1e4 if notional else np.nan,
        # the maker fee at which gross PnL would be exactly eaten by fees
        "breakeven_fee_bps": d["gross"] / notional * 1e4 if notional else np.nan,
        "avg_abs_lots": float(lots.abs().mean()) if len(s) else np.nan,
        "max_abs_lots": float(lots.abs().max()) if len(s) else np.nan,
        "pnl_per_min_std": float(pnl_min.std()) if len(pnl_min) > 1 else np.nan,
        "max_drawdown": float((s["pnl_gross"].cummax() - s["pnl_gross"]).max()) if len(s) else np.nan,
        "markout_bps": {float(k): (None if pd.isna(v) else float(v)) for k, v in mk.items()},
    }
    out["fee_scenarios"] = {name: d["gross"] - fee * 1e-4 * notional for name, fee in FEE_SCENARIOS_BPS.items()}
    return out
