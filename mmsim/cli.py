"""Command line entry point: ``python -m mmsim <command>`` or ``mmsim <command>``."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from .analytics import summarize
from .engine import EngineConfig, run
from .report import df_markdown, research_chart, summary_markdown, sweep_markouts, sweep_table, write_run
from .storage import Recorder, clip, read_meta, replay
from .strategies import STRATEGIES, accepted_params, make_strategy


def _params(pairs: list[str]) -> dict:
    """name=value pairs. ``strategy.name=value`` applies to one strategy only."""
    out = {}
    for p in pairs or []:
        k, _, v = p.partition("=")
        if not v:
            raise SystemExit(f"bad --param {p!r}, expected name=value")
        out[k.strip()] = float(v)
    return out


def _check_params(names: list[str], params: dict) -> None:
    """Fail fast on typos: every parameter must be taken by some strategy it targets."""
    for key in params:
        target, _, name = key.rpartition(".")
        pool = [target] if target else names
        if not any(name in accepted_params(STRATEGIES[n]) for n in pool if n in STRATEGIES):
            raise SystemExit(f"parameter {key!r} is not used by {pool}")


def _params_for(strategy: str, params: dict) -> dict:
    shared = {k: v for k, v in params.items() if "." not in k}
    own = {k.split(".", 1)[1]: v for k, v in params.items() if k.startswith(strategy + ".")}
    return {**shared, **own}


def _engine_kw(a) -> dict:
    return dict(latency_ms=a.latency_ms, maker_fee_bps=a.fee_bps, warmup_s=a.warmup_s,
                min_order_interval_ms=a.min_order_interval_ms)


def _stamp() -> str:
    return dt.datetime.now().strftime("%Y%m%d_%H%M%S")


def _config_for(path: str, **kw) -> EngineConfig:
    meta = read_meta(path)
    return EngineConfig(quote_inst=meta["quote_inst"], ref_inst=meta.get("ref_inst"), tick=meta["tick_size"], **kw)


def _events(path: str, window: tuple[float, float | None]):
    skip, length = window
    return clip(replay(path), skip, length) if (skip or length) else replay(path)


# ----------------------------------------------------------------- commands
def cmd_record(a) -> None:
    from .live import record

    out = a.out or f"data/{a.venue}_{a.symbol.upper()}_{_stamp()}.jsonl.gz"
    record(a.venue, a.symbol, a.minutes, out)


def cmd_paper(a) -> None:
    from .live import paper

    names = a.strategy.split(",")
    params = _params(a.param)
    _check_params(names, params)
    strats = [make_strategy(n, strict=len(names) == 1, **_params_for(n, params)) for n in names]
    tag = f"{a.venue}_{a.symbol.upper()}_{_stamp()}"
    data = a.record_to or f"data/paper_{tag}.jsonl.gz"
    print(f"paper trading {', '.join(names)} on {a.venue} {a.symbol} for {a.minutes} min "
          f"(latency {a.latency_ms} ms, maker fee {a.fee_bps} bp). Ctrl-C stops early.", flush=True)
    for st in strats:
        print(f"  {st.name}: {st.params()}", flush=True)
    results = paper(a.venue, a.symbol, a.minutes, strats, data, status_s=a.status_s, **_engine_kw(a))
    out = Path(a.out or f"runs/paper_{tag}")
    rows = []
    for name, res in results.items():
        sm = summarize(res)
        rows.append(sm)
        write_run(res, sm, out / name)
        print(summary_markdown(sm))
    _write_comparison(rows, out, f"Live paper trading: {a.venue} {a.symbol.upper()}",
                      f"Live session of {a.minutes:g} min, maker fee as simulated: {a.fee_bps} bp. "
                      f"Input stream recorded to `{data}`.")
    print(f"input stream recorded to {data}; reports in {out}")


def _write_comparison(rows: list[dict], out: Path, title: str, note: str) -> None:
    out.mkdir(parents=True, exist_ok=True)
    table = sweep_table(rows)
    sweep_markouts(rows, out / "markouts.png")
    (out / "summary.json").write_text(json.dumps(rows, indent=2, default=str))
    (out / "README.md").write_text(f"# {title}\n\n{note}\n\n{table}\n![markouts](markouts.png)\n")
    print(table)


def _backtest_one(job: tuple) -> dict:
    path, name, params, engine_kw, window, outdir = job
    res = run(_events(path, window), _config_for(path, **engine_kw), make_strategy(name, strict=False, **params))
    sm = summarize(res)
    sm["params"] = res.meta["params"]
    if outdir:
        write_run(res, sm, outdir)
    return sm


def cmd_backtest(a) -> None:
    out = a.out or f"runs/bt_{Path(a.data).name.split('.')[0]}_{a.strategy}_{_stamp()}"
    sm = _backtest_one((a.data, a.strategy, _params_for(a.strategy, _params(a.param)), _engine_kw(a),
                        (a.skip_minutes, a.max_minutes), out))
    print(summary_markdown(sm))
    print(f"report in {out}")


def _grid(specs: list[str] | None) -> list[dict]:
    """--grid k=1,2,4 --grid gamma=0.02,0.1 -> cartesian product of parameter dicts."""
    combos = [{}]
    for spec in specs or []:
        k, _, vs = spec.partition("=")
        combos = [{**c, k.strip(): float(v)} for c in combos for v in vs.split(",")]
    return combos


def cmd_sweep(a) -> None:
    strategies = a.strategies.split(",")
    latencies = [float(x) for x in a.latencies.split(",")]
    out = Path(a.out or f"runs/sweep_{Path(a.data).name.split('.')[0]}_{_stamp()}")
    params = _params(a.param)
    _check_params(strategies, params)
    grid = _grid(a.grid)
    jobs, seen = [], set()
    for lat in latencies:
        for s in strategies:
            ok = accepted_params(STRATEGIES[s])
            for g in grid:
                g = {k: v for k, v in g.items() if k in ok}  # a grid over as_signal's betas skips "as"
                if (lat, s, tuple(sorted(g.items()))) in seen:
                    continue
                seen.add((lat, s, tuple(sorted(g.items()))))
                kw = {**_engine_kw(a), "latency_ms": lat}
                tag = "_".join(f"{k}{v:g}" for k, v in g.items())
                sub = out / f"{s}_lat{lat:g}{'_' + tag if tag else ''}" if a.reports else None
                jobs.append((a.data, s, {**_params_for(s, params), **g}, kw, (a.skip_minutes, a.max_minutes), sub))
    with ProcessPoolExecutor(max_workers=a.workers) as pool:
        rows = list(pool.map(_backtest_one, jobs))
    meta = read_meta(a.data)
    window = f"minutes {a.skip_minutes or 0:g} to {a.skip_minutes + a.max_minutes if a.max_minutes else 'end'}"
    note = (f"Data: {Path(a.data).name}, {window}. Shared params: {params or 'defaults'}"
            f"{', grid: ' + ' '.join(a.grid) if a.grid else ''}. Maker fee as simulated: {a.fee_bps} bp.")
    if len(grid) > 1:
        rows.sort(key=lambda r: -r["pnl_gross"])
    _write_comparison(rows, out, f"Sweep: {meta['venue']} {meta['symbol']}", note)
    print(f"sweep written to {out}")


def cmd_research(a) -> None:
    from .research import build_grid, joint, lead_lag, predictive

    meta = read_meta(a.data)
    out = Path(a.out or f"runs/research_{Path(a.data).name.split('.')[0]}")
    out.mkdir(parents=True, exist_ok=True)
    grid = build_grid(_events(a.data, (a.skip_minutes, a.max_minutes)), meta["quote_inst"], meta["ref_inst"])
    xc = lead_lag(grid)
    pr = predictive(grid)
    jt = joint(grid)
    research_chart(xc, out / "lead_lag.png",
                   f"{meta['symbol']}: spot vs perp return correlation by lag (100 ms returns)")
    best = xc.loc[xc["corr"].idxmax()]
    md = (f"# Signal research: {meta['venue']} {meta['symbol']} ({meta.get('started')})\n\n"
          f"Grid: {len(grid):,} samples at 50 ms ({len(grid) * 0.05 / 60:.1f} min).\n\n"
          f"Lead-lag peak: corr {best['corr']:.3f} at {best['lag_ms']:+.0f} ms "
          f"(positive = perp moves first). Corr at 0 ms: {xc.loc[xc.lag_ms == 0, 'corr'].iloc[0]:.3f}.\n\n"
          "![lead-lag](lead_lag.png)\n\n"
          "Predictive regressions (future spot return in bps on the signal at t):\n\n"
          + df_markdown(pr) + "\n\n"
          "Joint regression on both signals (use these as beta_gap / beta_imb of as_signal):\n\n"
          + df_markdown(jt) + "\n")
    (out / "README.md").write_text(md)
    xc.to_csv(out / "lead_lag.csv", index=False)
    pr.to_csv(out / "predictive.csv", index=False)
    jt.to_csv(out / "joint.csv", index=False)
    print(md)


def cmd_reproduce(a) -> None:
    """Re-run a recorded paper session through the backtester with the same
    settings. Because the engine only ever sees the recorded events, the
    result must match the live session fill for fill."""
    meta = read_meta(a.data)
    if "paper" not in meta:
        raise SystemExit(f"{a.data} is not a paper-trading recording")
    engine = meta.get("engine", {"latency_ms": meta.get("latency_ms", 50.0)})
    out = Path(a.out or f"runs/reproduce_{Path(a.data).name.split('.')[0]}")
    rows = []
    for name, params in meta["paper"].items():
        res = run(replay(a.data), _config_for(a.data, **engine), make_strategy(name, **params))
        sm = summarize(res)
        rows.append(sm)
        write_run(res, sm, out / name)
    _write_comparison(rows, out, f"Replay of paper session {Path(a.data).name}",
                      f"Engine settings from the recording: {engine}.")
    print(f"written to {out}")


def cmd_synth(a) -> None:
    from .synthetic import generate

    meta, events = generate(minutes=a.minutes, seed=a.seed)
    rec = Recorder(a.out, meta)
    for ev in events:
        rec.write(ev)
    rec.close()
    print(f"wrote {len(events):,} synthetic events to {a.out}")


# ---------------------------------------------------------------------- CLI
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="mmsim", description="Crypto market-making simulator")
    sub = p.add_subparsers(dest="cmd", required=True)

    def engine_args(sp):
        sp.add_argument("--latency-ms", type=float, default=50.0, help="decision -> order live (default 50)")
        sp.add_argument("--fee-bps", type=float, default=0.0, help="maker fee in bps, negative = rebate")
        sp.add_argument("--warmup-s", type=float, default=60.0)
        sp.add_argument("--min-order-interval-ms", type=float, default=100.0)

    def strat_args(sp, multi=False):
        if multi:
            sp.add_argument("--strategy", "-s", default="fixed,as,as_signal",
                            help=f"comma-separated, run side by side on the same stream: {sorted(STRATEGIES)}")
        else:
            sp.add_argument("--strategy", "-s", choices=sorted(STRATEGIES), default="as")
        sp.add_argument("--param", "-p", action="append",
                        help="strategy parameter name=value, or strategy.name=value for one strategy")

    sp = sub.add_parser("record", help="record live market data")
    sp.add_argument("--venue", default="binance", choices=["binance", "okx"])
    sp.add_argument("--symbol", default="BTCUSDT")
    sp.add_argument("--minutes", type=float, default=30.0)
    sp.add_argument("--out")
    sp.set_defaults(func=cmd_record)

    sp = sub.add_parser("paper", help="paper-trade a strategy on the live feed")
    sp.add_argument("--venue", default="binance", choices=["binance", "okx"])
    sp.add_argument("--symbol", default="BTCUSDT")
    sp.add_argument("--minutes", type=float, default=30.0)
    sp.add_argument("--status-s", type=float, default=10.0)
    sp.add_argument("--record-to")
    sp.add_argument("--out")
    strat_args(sp, multi=True)
    engine_args(sp)
    sp.set_defaults(func=cmd_paper)

    def window_args(sp):
        sp.add_argument("--skip-minutes", type=float, default=0.0, help="ignore the first N minutes of data")
        sp.add_argument("--max-minutes", type=float, help="use at most N minutes after the skipped part")

    sp = sub.add_parser("backtest", help="replay a recording through one strategy")
    sp.add_argument("--data", required=True)
    window_args(sp)
    sp.add_argument("--out")
    strat_args(sp)
    engine_args(sp)
    sp.set_defaults(func=cmd_backtest)

    sp = sub.add_parser("sweep", help="grid of strategies x latencies on one recording")
    sp.add_argument("--data", required=True)
    sp.add_argument("--strategies", default="fixed,as,as_signal")
    sp.add_argument("--latencies", default="5,50,200")
    sp.add_argument("--param", "-p", action="append",
                    help="strategy parameter name=value, or strategy.name=value for one strategy")
    sp.add_argument("--grid", "-g", action="append", help="parameter grid name=v1,v2,... (repeatable)")
    sp.add_argument("--reports", action="store_true", help="also write a full report per run")
    window_args(sp)
    sp.add_argument("--workers", type=int, default=4)
    sp.add_argument("--out")
    engine_args(sp)
    sp.set_defaults(func=cmd_sweep)

    sp = sub.add_parser("research", help="lead-lag and predictive power of signals")
    sp.add_argument("--data", required=True)
    window_args(sp)
    sp.add_argument("--out")
    sp.set_defaults(func=cmd_research)

    sp = sub.add_parser("reproduce", help="replay a recorded paper session with its original settings")
    sp.add_argument("--data", required=True)
    sp.add_argument("--out")
    sp.set_defaults(func=cmd_reproduce)

    sp = sub.add_parser("synth", help="write a synthetic recording (no network needed)")
    sp.add_argument("--out", default="data/synthetic.jsonl.gz")
    sp.add_argument("--minutes", type=float, default=10.0)
    sp.add_argument("--seed", type=int, default=0)
    sp.set_defaults(func=cmd_synth)
    return p


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
    a = build_parser().parse_args(argv)
    a.func(a)


if __name__ == "__main__":
    main(sys.argv[1:])
