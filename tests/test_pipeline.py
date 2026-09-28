"""End-to-end on synthetic data: record -> replay -> engine -> analytics -> report."""
import math

import numpy as np
import pytest

from mmsim.analytics import decompose, markouts, summarize
from mmsim.engine import EngineConfig, run
from mmsim.events import BUY, SELL
from mmsim.report import write_run
from mmsim.research import build_grid, lead_lag, predictive
from mmsim.storage import Recorder, load
from mmsim.strategies import make_strategy
from mmsim.synthetic import generate


@pytest.fixture(scope="module")
def synth(tmp_path_factory):
    meta, events = generate(minutes=5, seed=1)
    path = tmp_path_factory.mktemp("data") / "s.jsonl.gz"
    rec = Recorder(path, meta)
    for ev in events:
        rec.write(ev)
    rec.close()
    return path, meta, events


def _cfg(meta, **kw):
    return EngineConfig(quote_inst=meta["quote_inst"], ref_inst=meta["ref_inst"], tick=meta["tick_size"],
                        warmup_s=10, **kw)


def test_recording_roundtrip(synth):
    path, meta, events = synth
    meta2, events2 = load(path)
    assert meta2["quote_inst"] == meta["quote_inst"]
    assert events2 == events


def test_pnl_decomposition_is_exact(synth):
    _, meta, events = synth
    res = run(events, _cfg(meta, maker_fee_bps=1.0), make_strategy("fixed", half_spread_bps=0.5))
    assert len(res.fills) > 10
    d = decompose(res)
    s = res.snapshots.iloc[-1]
    assert math.isclose(d["gross"], s["cash"] + s["position"] * s["mid"], abs_tol=1e-9)
    assert math.isclose(d["net"], d["gross"] - d["fees"], abs_tol=1e-12)
    assert d["fees"] > 0


def test_markout_at_zero_equals_spread_capture(synth):
    _, meta, events = synth
    res = run(events, _cfg(meta), make_strategy("fixed", half_spread_bps=0.5))
    mk = markouts(res).set_index("horizon_s")["markout_bps"]
    f = res.fills
    expect = np.average(f["side"] * (f["mid"] - f["price"]) / f["price"] * 1e4, weights=f["qty"])
    assert math.isclose(mk[0], expect, rel_tol=1e-6)


def test_informed_flow_shows_up_as_adverse_selection(synth):
    _, meta, events = synth
    res = run(events, _cfg(meta, latency_ms=200), make_strategy("fixed", half_spread_bps=0.5))
    mk = markouts(res).set_index("horizon_s")["markout_bps"]
    assert mk[5] < mk[0]


def test_lead_signal_is_found_in_synthetic_data(synth):
    _, meta, events = synth
    grid = build_grid(events, meta["quote_inst"], meta["ref_inst"])
    xc = lead_lag(grid)
    assert xc.loc[xc["corr"].idxmax(), "lag_ms"] > 0  # perp moves first
    pr = predictive(grid, warmup_s=10)
    gap = pr[(pr.signal == "gap_bps") & (pr.horizon_s == 0.5)].iloc[0]
    assert gap["beta"] > 0 and gap["t_stat_nonoverlap"] > 3


def test_all_strategies_run_and_report(synth, tmp_path):
    _, meta, events = synth
    for name, params in (("fixed", {}), ("as", {"k": 5, "gamma": 0.01}), ("as_signal", {"k": 5, "gamma": 0.01})):
        res = run(events, _cfg(meta), make_strategy(name, **params))
        sm = summarize(res)
        assert sm["fills"] > 0, name
        assert set(res.fills["side"]) <= {BUY, SELL}
        out = write_run(res, sm, tmp_path / name)
        assert (out / "dashboard.png").stat().st_size > 10_000
        assert "Break-even maker fee" in (out / "report.md").read_text()
