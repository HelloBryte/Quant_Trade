"""Charts and markdown reports (static PNG via matplotlib)."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from .analytics import MARKOUT_HORIZONS_S, markouts  # noqa: E402
from .engine import RunResult  # noqa: E402

# Palette: fixed categorical order, recessive chrome, text never in series colors.
SURFACE, INK, INK_2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
STRATEGY_COLOR = {"fixed": SERIES[0], "as": SERIES[1], "as_signal": SERIES[2]}
STRATEGY_LABEL = {"fixed": "v0 fixed spread", "as": "v1 Avellaneda-Stoikov", "as_signal": "v2 AS + signals"}


def _style() -> None:
    plt.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "axes.edgecolor": AXIS, "axes.labelcolor": INK_2, "axes.titlecolor": INK,
        "axes.titlesize": 11, "axes.titleweight": "bold", "axes.titlelocation": "left",
        "axes.labelsize": 9, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
        "axes.spines.top": False, "axes.spines.right": False, "xtick.color": MUTED, "ytick.color": MUTED,
        "xtick.labelsize": 8, "ytick.labelsize": 8, "legend.frameon": False, "legend.fontsize": 8,
        "lines.linewidth": 1.5, "lines.solid_capstyle": "round", "font.family": "DejaVu Sans",
    })


def _end_label(ax, x, y, text) -> None:
    ax.annotate(text, (x, y), xytext=(4, 0), textcoords="offset points", va="center",
                fontsize=8, color=INK_2)


def _horizon_labels(hs) -> list[str]:
    return ["fill" if h == 0 else (f"{h:g}s") for h in hs]


def dashboard(result: RunResult, summary: dict, path: Path) -> None:
    _style()
    s, f = result.snapshots, result.fills
    t0 = s["ts"].iloc[0]
    tmin = (s["ts"] - t0) / 6e10
    fig, axes = plt.subplots(2, 2, figsize=(13, 8), constrained_layout=True)
    title = f"{STRATEGY_LABEL.get(summary['strategy'], summary['strategy'])} · latency {summary['latency_ms']:g} ms"
    fig.suptitle(title, x=0.01, ha="left", fontsize=13, fontweight="bold", color=INK)

    ax = axes[0, 0]
    ax.plot(tmin, s["mid"], color=MUTED, lw=1.0, label="mid")
    if len(f):
        fm = (f["ts"] - t0) / 6e10
        buy, sell = f["side"] > 0, f["side"] < 0
        ax.scatter(fm[buy], f["price"][buy], marker="^", s=36, color=SERIES[0], edgecolor=SURFACE, lw=1, label="our buy", zorder=3)
        ax.scatter(fm[sell], f["price"][sell], marker="v", s=36, color=SERIES[1], edgecolor=SURFACE, lw=1, label="our sell", zorder=3)
    nd = 0 if s["mid"].iloc[-1] >= 1000 else 2 if s["mid"].iloc[-1] >= 1 else 5
    ax.yaxis.set_major_formatter(matplotlib.ticker.StrMethodFormatter(f"{{x:,.{nd}f}}"))
    ax.set_title("Price and our fills")
    ax.set_xlabel("minutes")
    ax.legend(loc="upper left", ncols=3)

    ax = axes[0, 1]
    lots = s["position"] * s["mid"] / result.meta["params"]["order_notional"]
    ax.step(tmin, lots, where="post", color=SERIES[0])
    ax.axhline(0, color=AXIS, lw=1)
    ax.set_title("Inventory (in orders of size 1 lot)")
    ax.set_xlabel("minutes")

    ax = axes[1, 0]
    spread_cum = np.zeros(len(s))
    if len(f):
        edge = (f["side"] * f["qty"] * (f["mid"] - f["price"])).cumsum().to_numpy()
        idx = np.searchsorted(f["ts"].to_numpy(), s["ts"].to_numpy(), side="right") - 1
        spread_cum = np.where(idx >= 0, edge[np.clip(idx, 0, None)], 0.0)
    series = [("gross", s["pnl_gross"].to_numpy(), SERIES[0]),
              ("spread capture", spread_cum, SERIES[2]),
              ("inventory", s["pnl_gross"].to_numpy() - spread_cum, SERIES[1])]
    if s["fees"].abs().sum() > 0:
        series.append(("net of fees", s["pnl_net"].to_numpy(), SERIES[3]))
    for name, y, c in series:  # final values ride in the legend; end labels collide when lines converge
        ax.plot(tmin, y, color=c, label=f"{name} {y[-1]:+.2f}")
    ax.axhline(0, color=AXIS, lw=1)
    ax.set_title("Cumulative PnL decomposition (USDT)")
    ax.set_xlabel("minutes")
    ax.legend(loc="upper left", ncols=len(series))

    ax = axes[1, 1]
    mk = markouts(result)
    x = np.arange(len(mk))
    ax.plot(x, mk["markout_bps"], color=SERIES[0], marker="o", ms=5, mec=SURFACE, mew=1.5)
    ax.axhline(0, color=AXIS, lw=1)
    ax.set_xticks(x, _horizon_labels(mk["horizon_s"]))
    last = mk["markout_bps"].dropna()
    if len(last):
        _end_label(ax, x[last.index[-1]], last.iloc[-1], f"{last.iloc[-1]:+.2f} bp")
    ax.set_title(f"Markout after our fills (bps, {len(f)} fills)")
    ax.set_xlabel("time after fill")
    fig.savefig(path, dpi=130)
    plt.close(fig)


def df_markdown(df: pd.DataFrame, nd: int = 4) -> str:
    """Minimal markdown table (avoids a tabulate dependency)."""
    cells = [[f"{v:.{nd}f}" if isinstance(v, float) else str(v) for v in row] for row in df.itertuples(index=False)]
    lines = ["| " + " | ".join(map(str, df.columns)) + " |", "|" + "---|" * len(df.columns)]
    lines += ["| " + " | ".join(r) + " |" for r in cells]
    return "\n".join(lines)


def _fmt(v, nd=2):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "n/a"
    return f"{v:,.{nd}f}" if isinstance(v, float) else str(v)


def summary_markdown(sm: dict) -> str:
    mk = sm["markout_bps"]
    lines = [
        f"# {STRATEGY_LABEL.get(sm['strategy'], sm['strategy'])} (latency {sm['latency_ms']:g} ms)", "",
        f"- Duration: {sm['hours'] * 60:.1f} min, fills: {sm['fills']} ({sm['buys']} buys / {sm['sells']} sells), "
        f"orders sent: {sm['orders']}, fill ratio: {_fmt(sm['fill_ratio'], 3)}",
        f"- Fill types: {sm['fill_kinds']}",
        f"- Traded notional: {_fmt(sm['notional'])} USDT", "",
        "| PnL component | USDT | bps of notional |", "|---|---:|---:|",
        f"| Spread capture | {_fmt(sm['pnl_spread_capture'])} | {_fmt(sm['spread_capture_bps'])} |",
        f"| Inventory | {_fmt(sm['pnl_inventory'])} | {_fmt(sm['inventory_bps'])} |",
        f"| **Gross** | **{_fmt(sm['pnl_gross'])}** | **{_fmt(sm['breakeven_fee_bps'])}** |",
        f"| Fees (as simulated) | {_fmt(-sm['pnl_fees'])} | |",
        f"| **Net** | **{_fmt(sm['pnl_net'])}** | |", "",
        f"Break-even maker fee: **{_fmt(sm['breakeven_fee_bps'])} bps** "
        "(gross PnL per unit of notional; any fee above this loses money).", "",
        "| Fee scenario | Net PnL (USDT) |", "|---|---:|",
        *[f"| {k} | {_fmt(v)} |" for k, v in sm["fee_scenarios"].items()], "",
        "| Markout horizon | " + " | ".join(_horizon_labels(mk)) + " |",
        "|---|" + "---:|" * len(mk),
        "| bps | " + " | ".join(_fmt(v) for v in mk.values()) + " |",
        "| s.e. | " + " | ".join(_fmt(v) for v in sm.get("markout_se_bps", {}).values()) + " |", "",
        f"- Inventory: mean |lots| {_fmt(sm['avg_abs_lots'])}, max |lots| {_fmt(sm['max_abs_lots'])}",
        f"- Gross PnL std per minute: {_fmt(sm['pnl_per_min_std'], 3)} USDT, max drawdown: {_fmt(sm['max_drawdown'], 3)} USDT",
    ]
    return "\n".join(lines) + "\n"


def write_run(result: RunResult, summary: dict, outdir: str | Path) -> Path:
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    result.fills.to_csv(out / "fills.csv", index=False)
    result.snapshots.to_csv(out / "snapshots.csv", index=False)
    (out / "summary.json").write_text(json.dumps({**summary, "meta": result.meta}, indent=2, default=str))
    (out / "report.md").write_text(summary_markdown(summary) + "\n![dashboard](dashboard.png)\n")
    dashboard(result, summary, out / "dashboard.png")
    return out


# ------------------------------------------------------------------- sweeps
def sweep_markouts(rows: list[dict], path: Path) -> None:
    """Small multiples: one panel per latency, one line per strategy."""
    _style()
    lats = sorted({r["latency_ms"] for r in rows})
    fig, axes = plt.subplots(1, len(lats), figsize=(4.4 * len(lats), 3.8), sharey=True, constrained_layout=True)
    axes = np.atleast_1d(axes)
    x = np.arange(len(MARKOUT_HORIZONS_S))
    for ax, lat in zip(axes, lats):
        for r in (r for r in rows if r["latency_ms"] == lat):
            y = [r["markout_bps"].get(float(h)) for h in MARKOUT_HORIZONS_S]
            y = np.array([np.nan if v is None else v for v in y])
            ax.plot(x, y, color=STRATEGY_COLOR.get(r["strategy"], MUTED), marker="o", ms=4, mec=SURFACE,
                    mew=1.2, label=STRATEGY_LABEL.get(r["strategy"], r["strategy"]))
        ax.axhline(0, color=AXIS, lw=1)
        ax.set_xticks(x, _horizon_labels(MARKOUT_HORIZONS_S), rotation=0)
        ax.set_title(f"latency {lat:g} ms")
        ax.set_xlabel("time after fill")
    axes[0].set_ylabel("markout (bps)")
    axes[0].legend(loc="lower left")
    fig.suptitle("Markout after our fills, by strategy and latency", x=0.01, ha="left",
                 fontsize=12, fontweight="bold", color=INK)
    fig.savefig(path, dpi=130)
    plt.close(fig)


def latency_chart(rows: list[dict], path: Path, title: str) -> None:
    """Gross PnL per notional (= break-even maker fee) against latency, one line per strategy."""
    _style()
    fig, ax = plt.subplots(figsize=(7.5, 4.2), constrained_layout=True)
    for strat in dict.fromkeys(r["strategy"] for r in rows):
        rs = sorted((r for r in rows if r["strategy"] == strat), key=lambda r: r["latency_ms"])
        x = [r["latency_ms"] for r in rs]
        y = [r["breakeven_fee_bps"] for r in rs]
        ax.plot(x, y, color=STRATEGY_COLOR.get(strat, MUTED), marker="o", ms=5, mec=SURFACE, mew=1.5,
                label=STRATEGY_LABEL.get(strat, strat))
    ax.axhline(0, color=AXIS, lw=1)
    ax.set_xscale("log")
    lats = sorted({r["latency_ms"] for r in rows})
    ax.set_xticks(lats, [f"{v:g}" for v in lats])
    ax.minorticks_off()
    ax.set_xlabel("latency (ms, log scale)")
    ax.set_ylabel("gross PnL per notional (bps)")
    ax.set_title(title)
    ax.legend(loc="best")
    fig.savefig(path, dpi=130)
    plt.close(fig)


def _markout_cell(r: dict, h: float) -> str:
    v, se = r["markout_bps"].get(h), r.get("markout_se_bps", {}).get(h)
    return _fmt(v) if se is None else f"{_fmt(v)} ± {se:.2f}"


def sweep_table(rows: list[dict]) -> str:
    # show only the parameters that differ between rows
    keys = sorted({k for r in rows for k in r.get("params", {})})
    groups = {r["strategy"] for r in rows}
    varying = [k for k in keys if any(
        len({r["params"][k] for r in rows if r["strategy"] == g and k in r.get("params", {})}) > 1 for g in groups)]
    pcol = " params |" if varying else ""
    head = (f"| strategy | latency ms |{pcol} fills | spread capture bp | inventory bp "
            "| gross = break-even fee bp | gross USDT | markout 5s bp (± s.e.) | mean abs lots |")
    lines = [head, "|---|---:|" + ("---|" if varying else "") + "---:|" * 7]
    for r in rows:
        shown = [f"{k}={r['params'][k]:g}" for k in varying if k in r.get("params", {})]
        pv = " " + ", ".join(shown) + " |" if varying else ""
        lines.append(
            f"| {STRATEGY_LABEL.get(r['strategy'], r['strategy'])} | {r['latency_ms']:g} |{pv} {r['fills']} "
            f"| {_fmt(r['spread_capture_bps'])} | {_fmt(r['inventory_bps'])} | {_fmt(r['breakeven_fee_bps'])} "
            f"| {_fmt(r['pnl_gross'])} | {_markout_cell(r, 5.0)} | {_fmt(r['avg_abs_lots'])} |")
    return "\n".join(lines) + "\n"


def research_chart(xcorr: pd.DataFrame, path: Path, title: str) -> None:
    _style()
    fig, ax = plt.subplots(figsize=(8, 3.8), constrained_layout=True)
    ax.plot(xcorr["lag_ms"], xcorr["corr"], color=SERIES[0], marker="o", ms=4, mec=SURFACE, mew=1.2)
    ax.axhline(0, color=AXIS, lw=1)
    ax.axvline(0, color=AXIS, lw=1)
    best = xcorr.loc[xcorr["corr"].idxmax()]
    _end_label(ax, best["lag_ms"], best["corr"], f"peak at {best['lag_ms']:+.0f} ms")
    ax.set_xlabel("lag (ms): positive = perp return earlier than spot return")
    ax.set_ylabel("correlation")
    ax.set_title(title)
    fig.savefig(path, dpi=130)
    plt.close(fig)
