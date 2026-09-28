"""Signal research: does the perpetual future lead spot, and by how much?

Before putting a signal into a strategy, a desk checks it offline:

1. Lead-lag: correlation of spot returns with perp returns shifted in time.
   A peak at a positive lag means perp moves first.
2. Predictive regression: future spot mid return over horizon h regressed on
   the basis gap at time t. The slope is what ``beta_gap`` in the v2
   strategy should roughly be; R^2 says how much of the move it explains.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .events import Quote
from .signals import BasisGap, imbalance

GRID_MS = 50
HORIZONS_S = (0.1, 0.25, 0.5, 1, 2, 5, 10)


def _asof(ts: np.ndarray, values: np.ndarray, grid: np.ndarray) -> np.ndarray:
    idx = np.searchsorted(ts, grid, side="right") - 1
    out = values[np.clip(idx, 0, None)].astype(float)
    out[idx < 0] = np.nan
    return out


def build_grid(events, quote_inst: str, ref_inst: str, grid_ms: int = GRID_MS,
               basis_halflife_s: float = 120.0) -> pd.DataFrame:
    """Sample spot mid, perp mid, basis gap and imbalance on a regular clock."""
    q_ts, q_mid, q_imb, r_ts, r_mid, g_ts, g_val = [], [], [], [], [], [], []
    gap = BasisGap(basis_halflife_s)
    last_q = last_r = None
    for ev in events:
        if not isinstance(ev, Quote):
            continue
        if ev.inst == quote_inst:
            last_q = ev.mid
            q_ts.append(ev.ts); q_mid.append(last_q); q_imb.append(imbalance(ev.bid_qty, ev.ask_qty))
        elif ev.inst == ref_inst:
            last_r = ev.mid
            r_ts.append(ev.ts); r_mid.append(last_r)
        else:
            continue
        if last_q is not None and last_r is not None:
            gap.update(ev.ts, last_q, last_r)  # causal: uses only past data
            g_ts.append(ev.ts); g_val.append(gap.gap)
    q_ts, r_ts, g_ts = (np.asarray(a, dtype=np.int64) for a in (q_ts, r_ts, g_ts))
    start, end = max(q_ts[0], r_ts[0]), min(q_ts[-1], r_ts[-1])
    grid = np.arange(start, end, grid_ms * 1_000_000, dtype=np.int64)
    return pd.DataFrame({
        "ts": grid,
        "spot": _asof(q_ts, np.asarray(q_mid), grid),
        "perp": _asof(r_ts, np.asarray(r_mid), grid),
        "gap_bps": _asof(g_ts, np.asarray(g_val), grid),
        "imbalance": _asof(q_ts, np.asarray(q_imb), grid),
    })


def lead_lag(grid: pd.DataFrame, max_lag_ms: int = 2000, step_ms: int = 100) -> pd.DataFrame:
    """corr(spot return over (t-step, t], perp return over (t-step-lag, t-lag])."""
    k = step_ms // GRID_MS
    rs = np.log(grid["spot"]).diff(k).to_numpy()
    rp = np.log(grid["perp"]).diff(k).to_numpy()
    rows = []
    for lag in range(-max_lag_ms, max_lag_ms + 1, GRID_MS):
        shift = lag // GRID_MS
        a = rs[max(shift, 0):len(rs) + min(shift, 0)]
        b = rp[max(-shift, 0):len(rp) - max(shift, 0)]
        ok = ~(np.isnan(a) | np.isnan(b))
        rows.append((lag, float(np.corrcoef(a[ok], b[ok])[0, 1]) if ok.sum() > 10 else np.nan))
    return pd.DataFrame(rows, columns=["lag_ms", "corr"])


def predictive(grid: pd.DataFrame, horizons=HORIZONS_S, warmup_s: float = 60.0) -> pd.DataFrame:
    """OLS of future spot return (bps) on the gap and on imbalance, separately."""
    g = grid.iloc[int(warmup_s * 1000 / GRID_MS):].reset_index(drop=True)
    rows = []
    for h in horizons:
        k = int(round(h * 1000 / GRID_MS))
        fut = (np.log(g["spot"].shift(-k)) - np.log(g["spot"])).to_numpy() * 1e4
        for name in ("gap_bps", "imbalance"):
            x = g[name].to_numpy()
            ok = ~(np.isnan(x) | np.isnan(fut))
            xs, ys = x[ok], fut[ok]
            if len(xs) < 30 or xs.std() == 0:
                continue
            beta = float(np.cov(xs, ys)[0, 1] / xs.var())
            corr = float(np.corrcoef(xs, ys)[0, 1])
            # overlapping returns inflate naive t-stats; use non-overlapping count
            n_eff = max(len(xs) // max(k, 1), 2)
            rows.append((name, h, beta, corr, corr**2, corr * np.sqrt(n_eff - 2) / np.sqrt(max(1 - corr**2, 1e-12))))
    return pd.DataFrame(rows, columns=["signal", "horizon_s", "beta", "corr", "r2", "t_stat_nonoverlap"])


def joint(grid: pd.DataFrame, horizons=HORIZONS_S, warmup_s: float = 60.0) -> pd.DataFrame:
    """OLS of future spot return (bps) on both signals together (with intercept).

    The slopes are directly usable as ``beta_gap`` and ``beta_imb`` of the
    as_signal strategy: they are the expected move per unit of each signal,
    holding the other fixed.
    """
    g = grid.iloc[int(warmup_s * 1000 / GRID_MS):].reset_index(drop=True)
    rows = []
    for h in horizons:
        k = int(round(h * 1000 / GRID_MS))
        y = (np.log(g["spot"].shift(-k)) - np.log(g["spot"])).to_numpy() * 1e4
        X = np.column_stack([np.ones(len(g)), g["gap_bps"].to_numpy(), g["imbalance"].to_numpy()])
        ok = ~(np.isnan(y) | np.isnan(X).any(axis=1))
        if ok.sum() < 30:
            continue
        coef, *_ = np.linalg.lstsq(X[ok], y[ok], rcond=None)
        resid = y[ok] - X[ok] @ coef
        r2 = 1 - resid.var() / y[ok].var()
        rows.append((h, coef[1], coef[2], r2))
    return pd.DataFrame(rows, columns=["horizon_s", "beta_gap", "beta_imb", "r2"])
