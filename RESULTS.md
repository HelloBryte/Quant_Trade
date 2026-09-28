# Results: market making Binance BTC/USDT and SOL/USDT spot

All numbers come from one afternoon of real Binance data on 2026-09-28
(roughly 12:20 to 13:40 UTC), with virtual orders of 100 USDT per quote,
at most 5 orders of inventory, and no fees unless stated. They are an
illustration of the mechanics, not a statistically robust claim about the
market. Everything can be regenerated with `experiments/run_all.sh`.

## Protocol

| Step | Data | Purpose |
|---|---|---|
| 1. Calibration | minutes 0-20 of a 60-minute raw recording per symbol | signal research, choose `k`, `gamma` and the signal betas |
| 2. Out-of-sample replay | minutes 20-60 of the same recordings | strategy x latency sweep |
| 3. Live paper trading | a separate 60-minute live session per symbol, all three strategies side by side | fully out of sample, in real time |
| 4. Consistency check | replay of the live sessions' own recordings | must reproduce the live fills exactly |

Fixed parameters for every run: `k = 1` (base half spread about 1 bp),
`gamma = 0.05`, `tau = 30 s`, v0 half spread 1 bp, latency 50 ms unless swept.
Signal betas (v2) are the joint-regression slopes at the 1-second horizon on the
calibration window: BTC `beta_gap = 0`, `beta_imb = 0.25`; SOL `beta_gap = 0.08`,
`beta_imb = 0.6`.

## 1. Signals: the perp does not lead, book imbalance does predict

Correlation of 100 ms spot and perp returns peaks at **lag 0** in every
window, for both symbols (BTC 0.46 / 0.55, SOL 0.59 / 0.61 in the calibration /
out-of-sample windows). At the resolution this setup can see (50 ms grid,
about 55 ms of feed delay with jitter), the perpetual future does not move
first. The original hypothesis for v2 was wrong.

![lead-lag BTC](results/lead_lag_BTC.png)

What does predict the next second of spot is the top-of-book size imbalance,
and it is stable out of sample:

| 1 s horizon, univariate | BTC calib. | BTC out-of-sample | SOL calib. | SOL out-of-sample |
|---|---:|---:|---:|---:|
| imbalance: beta (bp per unit), corr | 0.22, 0.33 | 0.22, 0.34 | 0.61, 0.33 | 0.52, 0.32 |
| perp-spot gap: beta, corr | 0.18, 0.23 | 0.25, 0.28 | 0.18, 0.13 | 0.26, 0.21 |
| joint regression: beta_imb / beta_gap | 0.23 / -0.01 | 0.17 / 0.10 | 0.59 / 0.06 | 0.46 / 0.11 |

The gap does predict spot on its own, but once imbalance is in the
regression it adds little: both mostly measure the same short-term pressure.
Full tables: [results/tables](results/tables).

## 2. Out-of-sample replay: strategy x latency (minutes 20-60)

Gross PnL per unit of traded notional, in bps (= the break-even maker fee):

| Latency | BTC v0 | BTC v1 | BTC v2 | SOL v0 | SOL v1 | SOL v2 |
|---:|---:|---:|---:|---:|---:|---:|
| 5 ms | -0.42 | -0.35 | -1.49 | -0.71 | -1.27 | -0.83 |
| 50 ms | -1.23 | -1.59 | **-1.00** | -0.70 | -1.14 | **-0.67** |
| 200 ms | -1.81 | -1.50 | **-1.11** | -1.99 | -1.28 | **-1.09** |
| 500 ms | -1.87 | -1.52 | **-1.07** | -1.83 | -1.15 | **-1.00** |

(v0 fixed spread, v1 Avellaneda-Stoikov, v2 AS + signals; fill counts range
from 13 to 463, see [results/tables/latency_BTC.md](results/tables/latency_BTC.md)
and [latency_SOL.md](results/tables/latency_SOL.md).)

![latency BTC](results/latency_BTC.png)
![latency SOL](results/latency_SOL.png)

Markouts are nearly identical across strategies and latencies: close to zero
at the fill, about **-1 bp five seconds later** (standard errors 0.1 to 0.4 bp).

![markouts BTC](results/markouts_latency_BTC.png)

## 3. Live paper trading (60 minutes, fully out of sample)

_Pending: the two 60-minute live sessions are still running._

## What this says

_Pending the live results._
