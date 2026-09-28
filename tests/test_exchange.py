import math

from mmsim.events import BUY, SELL, Depth, Quote, Trade
from mmsim.exchange import SimExchange

MS = 1_000_000
INST = "x"


def make(latency_ms=10, fee_bps=0.0):
    ex = SimExchange(tick=0.01, latency_ns=latency_ms * MS, maker_fee_bps=fee_bps)
    ex.on_quote(Quote(0, INST, 100.00, 2.0, 100.01, 3.0))
    return ex


def test_order_is_not_live_until_latency_passes():
    ex = make(latency_ms=10)
    oid = ex.submit(0, BUY, 100.00, 1.0)
    ex.advance(5 * MS)
    ex.on_trade(Trade(5 * MS, INST, 99.99, 5.0, SELL))  # would fill if live
    assert ex.fills == []
    ex.advance(10 * MS)
    assert ex.orders[oid].status == "active"


def test_post_only_rejects_crossing_order():
    ex = make()
    ex.submit(0, BUY, 100.01, 1.0)  # at the best ask
    ex.advance(10 * MS)
    assert ex.orders == {} and ex.n_rejected == 1


def test_trade_through_fills_completely():
    ex = make()
    ex.submit(0, BUY, 100.00, 1.0)
    ex.advance(10 * MS)
    ex.on_trade(Trade(11 * MS, INST, 99.99, 0.01, SELL))
    assert len(ex.fills) == 1
    f = ex.fills[0]
    assert (f.kind, f.side, f.price, f.qty) == ("through", BUY, 100.00, 1.0)
    assert ex.position == 1.0 and math.isclose(ex.cash, -100.0)


def test_queue_must_be_consumed_before_we_fill():
    ex = make()
    ex.submit(0, BUY, 100.00, 1.0)  # joins behind 2.0 already at the best bid
    ex.advance(10 * MS)
    assert ex.orders[1].queue_ahead == 2.0
    ex.on_trade(Trade(11 * MS, INST, 100.00, 1.5, SELL))
    assert ex.fills == []
    ex.on_trade(Trade(12 * MS, INST, 100.00, 1.0, SELL))  # 0.5 left for us
    assert len(ex.fills) == 1 and math.isclose(ex.fills[0].qty, 0.5) and ex.fills[0].kind == "queue"
    ex.on_trade(Trade(13 * MS, INST, 100.00, 1.0, SELL))
    assert math.isclose(ex.position, 1.0) and ex.orders == {}


def test_buy_aggressor_does_not_fill_our_bid():
    ex = make()
    ex.submit(0, BUY, 100.00, 1.0)
    ex.advance(10 * MS)
    ex.on_trade(Trade(11 * MS, INST, 99.99, 5.0, BUY))
    assert ex.fills == []


def test_improving_the_best_price_means_empty_queue():
    ex = make()
    ex.on_quote(Quote(0, INST, 100.00, 2.0, 100.03, 3.0))
    ex.submit(0, SELL, 100.02, 1.0)
    ex.advance(10 * MS)
    assert ex.orders[1].queue_ahead == 0.0
    ex.on_trade(Trade(11 * MS, INST, 100.02, 0.4, BUY))
    assert math.isclose(ex.fills[0].qty, 0.4)


def test_cross_fill_when_book_moves_through_our_quote():
    ex = make()
    ex.submit(0, BUY, 100.00, 1.0)
    ex.advance(10 * MS)
    ex.on_quote(Quote(11 * MS, INST, 99.97, 1.0, 99.98, 0.3))  # someone offers below our bid
    assert len(ex.fills) == 1
    f = ex.fills[0]
    assert f.kind == "cross" and math.isclose(f.qty, 0.3)
    assert math.isclose(f.mid, 99.975)  # adverse: mid already below our price


def test_cancel_can_lose_the_race():
    ex = make(latency_ms=10)
    ex.submit(0, BUY, 100.00, 1.0)
    ex.advance(10 * MS)
    ex.cancel(11 * MS, 1)  # effective at 21 ms
    ex.on_trade(Trade(15 * MS, INST, 99.99, 1.0, SELL))
    assert len(ex.fills) == 1
    ex.advance(30 * MS)
    assert ex.n_canceled == 0


def test_cancel_takes_effect_after_latency():
    ex = make(latency_ms=10)
    ex.submit(0, BUY, 100.00, 1.0)
    ex.advance(10 * MS)
    ex.cancel(11 * MS, 1)
    ex.advance(21 * MS)
    ex.on_trade(Trade(22 * MS, INST, 99.99, 1.0, SELL))
    assert ex.fills == [] and ex.n_canceled == 1


def test_deep_order_queue_unknown_until_depth_shows_level():
    ex = make()
    ex.on_depth(Depth(0, INST, [(100.00, 2.0), (99.99, 1.0)], [(100.01, 3.0)]))
    ex.submit(0, BUY, 99.95, 1.0)  # deeper than the snapshot
    ex.advance(10 * MS)
    assert ex.orders[1].queue_ahead == math.inf
    ex.on_depth(Depth(20 * MS, INST, [(100.00, 2.0), (99.99, 1.0), (99.95, 0.7)], [(100.01, 3.0)]))
    assert ex.orders[1].queue_ahead == 0.7


def test_fees_and_rebates():
    ex = make(fee_bps=-1.0)  # 1 bp rebate
    ex.submit(0, SELL, 100.01, 2.0)
    ex.advance(10 * MS)
    ex.on_trade(Trade(11 * MS, INST, 100.02, 1.0, BUY))
    assert math.isclose(ex.fees, -1e-4 * 100.01 * 2.0)
