# mmsim: a crypto market-making simulator on live Binance data

A small, self-contained project that does what a market-making quant does day to
day, on real data: stream the order book, quote both sides with virtual orders,
decide honestly when those orders would have been filled, and then measure
where the money came from and where it went.

It runs **live** (paper trading on the Binance websocket feed, no API key, no
real orders) and as a **replay backtest** on recorded sessions. Both go through
the same event-driven engine, so replaying a recorded paper session reproduces
it fill for fill.

**Headline results** are in [RESULTS.md](RESULTS.md). In short, from two
60-minute live sessions and 40 minutes of out-of-sample replay on Binance
BTC/USDT and SOL/USDT spot:

- Every strategy lost 0.35 to 2 bps of traded notional *before* fees. Fills
  are about 1 to 1.5 bps under water five seconds later: adverse selection.
- Breaking even would take a maker rebate of 1.2 to 2 bps; at retail spot fees
  the loss is 6 to 9 times larger.
- Inventory control cut inventory 5 to 8 times. A top-of-book imbalance signal
  predicts about 11% of 1-second spot variance, but did not reliably reduce the
  loss live. The perp did not lead spot.
- Replaying the live sessions reproduces 1,573 of 1,573 fills exactly.

That matches how the business works: the edge is in fees, order flow and
speed, not in the textbook quoting formula.

A Chinese walkthrough of the concepts and code is in
[docs/guide_zh.md](docs/guide_zh.md).

## What is in here

```
mmsim/
  feeds/        Binance (spot + USD-M perp) and OKX websocket feeds -> normalised events
  storage.py    record events to .jsonl.gz, replay them
  exchange.py   simulated matching for our virtual orders: latency, post-only,
                queue position, trade-through and book-cross fills, maker fees
  signals.py    EWMA volatility, perp-spot basis gap, book imbalance
  strategies/   v0 fixed spread, v1 Avellaneda-Stoikov, v2 AS + signals
  engine.py     event loop shared by live paper trading and backtests
  analytics.py  PnL decomposition, markouts, break-even fee, inventory stats
  research.py   lead-lag and predictive regressions for candidate signals
  report.py     charts and markdown reports
  live.py       live recording and paper trading
  cli.py        `python -m mmsim ...`
tests/          fill-model unit tests, strategy tests, end-to-end pipeline tests
```

## Quick start

```bash
pip install -e ".[dev]"
pytest                                   # 25 tests, no network needed

# offline: 5 minutes of real Binance data ship in samples/
python -m mmsim backtest --data samples/binance_SOLUSDT_5min.jsonl.gz --strategy as_signal -p beta_imb=0.6
python -m mmsim sweep --data samples/binance_BTCUSDT_5min.jsonl.gz --latencies 5,50,200

# offline: synthetic market with a known lead-lag
python -m mmsim synth --out data/synthetic.jsonl.gz
python -m mmsim backtest --data data/synthetic.jsonl.gz --strategy as

# live: paper-trade all three strategies side by side for 30 minutes
python -m mmsim paper --symbol BTCUSDT --minutes 30

# record raw data, then research signals and sweep strategies x latency on it
python -m mmsim record --symbol SOLUSDT --minutes 60 --out data/sol.jsonl.gz
python -m mmsim research --data data/sol.jsonl.gz --max-minutes 20
python -m mmsim sweep --data data/sol.jsonl.gz --latencies 5,50,200 --skip-minutes 20

# check that a paper session replays to the exact same fills
python -m mmsim reproduce --data data/paper_....jsonl.gz
```

Every run writes a folder with `report.md`, `dashboard.png`, `fills.csv`,
`snapshots.csv` and `summary.json`. Strategy parameters are passed as
`-p name=value` (or `-p as_signal.beta_imb=0.3` to target one strategy), and
`sweep` takes `-g name=v1,v2,...` grids.

Binance's main REST API geo-blocks some regions; the feeds only use the
market-data endpoints `data-stream.binance.vision`, `data-api.binance.vision`
and `fstream.binance.com`. `--venue okx` is available as a fallback.

## How a fill is decided

Our orders never reach the exchange, so the simulator has to decide whether a
real order at the same price would have traded. This is the part of any
market-making backtest that is easiest to get wrong, so the rules are explicit
(`mmsim/exchange.py`) and unit-tested (`tests/test_exchange.py`):

| Rule | What happens |
|---|---|
| Latency | A new order or cancel takes effect `latency_ms` after the decision. A cancel can lose the race against a fill. |
| Post-only | An order that would cross the book on arrival is rejected. |
| Trade-through | A trade prints at a price worse than ours (a sell below our bid). Price priority says we would have been hit first: full fill. |
| Book cross | The real book shows an opposite quote at or through our price (best ask <= our bid). That seller would have traded with us: fill up to the displayed size. |
| Queue | A trade prints exactly at our price. It first consumes the estimated queue ahead of us, then fills us. |
| Queue estimate | On arrival we join the back of the visible queue (0 if we improve the best price; unknown if deeper than the 20-level snapshot). The estimate then only shrinks: capped by the displayed size, reduced by trades at our price. |

Known simplifications, which all make the simulation *kinder* than reality
unless noted:

- Our orders are assumed too small to move the market, and nobody reacts to them.
- Market data and order entry share one clock: timestamps are our receive times
  (about 55 ms after the exchange from this machine), and `latency_ms` is the
  extra delay before our order is live. Real round trips from outside the
  exchange's region are longer.
- The queue estimate counts everyone displayed at our level as ahead of us, even
  orders that arrived later (this one is conservative).
- Fees are applied at a flat maker rate; the break-even fee in every report shows
  how any fee schedule would change the result.

## Strategies

All three quote one order per side around a fair value, rounded outwards to the
tick grid, and stop quoting the side that would push inventory past `max_lots`.

- **v0 `fixed`**: bid/ask at mid -/+ `half_spread_bps`. No inventory control.
- **v1 `as`**: Avellaneda & Stoikov (2008) in bps, inventory `q` in lots:
  reservation shift `-q * gamma * sigma^2 * tau`, half spread
  `gamma * sigma^2 * tau / 2 + ln(1 + gamma / k) / gamma`, with `sigma` estimated
  online (EWMA of mid returns). Long inventory lowers both quotes so we are more
  likely to sell.
- **v2 `as_signal`**: v1 around `mid * (1 + (beta_gap * gap + beta_imb * imbalance) / 1e4)`,
  where `gap` is the perp's deviation from its usual premium over spot and
  `imbalance` is `(bid_qty - ask_qty) / (bid_qty + ask_qty)` at the top of the
  book. The betas come from `mmsim research` (joint regression of future spot
  returns on both signals).

## What the numbers mean

- **Spread capture**: sum of `side * qty * (mid_at_fill - price)`, what we earned
  against mid at the moment of each fill.
- **Inventory PnL**: what the position we were left holding made or lost
  afterwards. Spread capture + inventory = gross PnL, exactly.
- **Markout(h)**: `side * (mid(t + h) - price) / price` in bps, averaged over
  fills. The drop from h = 0 to h = 5 s is adverse selection: the people who
  traded with us knew where the price was going.
- **Break-even maker fee**: gross PnL per unit of notional. Any maker fee above
  it loses money; a rebate below zero is what the strategy needs to survive.

## Limitations and next steps

- One exchange, two symbols, a few hours of data from one day. Treat the
  numbers as an illustration of the mechanics, not a statistical result.
- `k` in Avellaneda-Stoikov should be calibrated from fill intensity as a
  function of distance to mid; here it is set by a small grid on a calibration
  window.
- Natural extensions: cross-venue quoting (make on OKX, hedge on Binance),
  queue-position-aware quoting for large-tick assets, a proper L2 book with
  diff-depth updates instead of 20-level snapshots, and options market making
  on Deribit.
