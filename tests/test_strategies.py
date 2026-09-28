import math

import pytest

from mmsim.strategies import MarketState, make_strategy


def state(position=0.0, gap=0.0, imb=0.0, sigma=1.0, bid=100.00, ask=100.02):
    return MarketState(ts=0, bid=bid, ask=ask, bid_qty=1, ask_qty=1, tick=0.01, sigma_bps=sigma,
                       gap_bps=gap, imbalance=imb, position=position)


def test_fixed_spread_is_symmetric_and_on_tick_grid():
    q = make_strategy("fixed", half_spread_bps=5).quote(state())
    assert q.bid == 99.95 and q.ask == 100.07  # mid 100.01 -/+ 5 bp (0.05), rounded outwards
    assert math.isclose(q.qty * 100.01, 100.0)


def test_quotes_never_cross_the_book():
    q = make_strategy("fixed", half_spread_bps=0.0).quote(state())
    assert q.bid < 100.02 and q.ask > 100.00


def test_as_long_inventory_shifts_quotes_down():
    s = make_strategy("as", gamma=0.1, tau_s=30)
    flat = s.quote(state())
    lots = 2.0
    long = s.quote(state(position=lots * 100.0 / 100.01))
    assert long.bid < flat.bid and long.ask < flat.ask


def test_as_spread_widens_with_volatility():
    s = make_strategy("as")
    calm, wild = s.quote(state(sigma=0.5)), s.quote(state(sigma=3.0))
    assert (wild.ask - wild.bid) > (calm.ask - calm.bid)


def test_inventory_limit_pulls_one_side():
    s = make_strategy("fixed", max_lots=3)
    q = s.quote(state(position=3.1 * 100 / 100.01))
    assert q.bid is None and q.ask is not None


def test_lead_signal_moves_fair_value():
    s = make_strategy("as_signal", beta_gap=1.0, beta_imb=2.0)
    base = s.quote(state())
    for up in (s.quote(state(gap=5.0)), s.quote(state(imb=0.9))):
        assert up.bid > base.bid and up.ask > base.ask


def test_unknown_param_is_an_error_unless_not_strict():
    with pytest.raises(ValueError):
        make_strategy("fixed", gamma=1)
    assert make_strategy("fixed", strict=False, gamma=1).name == "fixed"
