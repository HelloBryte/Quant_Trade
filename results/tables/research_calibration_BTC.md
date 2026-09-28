# Signal research: binance BTCUSDT (2026-09-28T12:20:26+00:00)

Grid: 23,997 samples at 50 ms (20.0 min).

Lead-lag peak: corr 0.456 at +0 ms (positive = perp moves first). Corr at 0 ms: 0.456.



Predictive regressions (future spot return in bps on the signal at t):

| signal | horizon_s | beta | corr | r2 | t_stat_nonoverlap |
|---|---|---|---|---|---|
| gap_bps | 0.1000 | 0.0208 | 0.1065 | 0.0113 | 11.4287 |
| imbalance | 0.1000 | 0.0282 | 0.1660 | 0.0275 | 17.9640 |
| gap_bps | 0.2500 | 0.0510 | 0.1517 | 0.0230 | 10.3590 |
| imbalance | 0.2500 | 0.0650 | 0.2226 | 0.0496 | 15.4142 |
| gap_bps | 0.5000 | 0.0955 | 0.1885 | 0.0355 | 9.1577 |
| imbalance | 0.5000 | 0.1204 | 0.2740 | 0.0751 | 13.5941 |
| gap_bps | 1.0000 | 0.1784 | 0.2317 | 0.0537 | 8.0279 |
| imbalance | 1.0000 | 0.2198 | 0.3290 | 0.1083 | 11.7436 |
| gap_bps | 2.0000 | 0.3282 | 0.2728 | 0.0744 | 6.7470 |
| imbalance | 2.0000 | 0.3779 | 0.3621 | 0.1311 | 9.2425 |
| gap_bps | 5.0000 | 0.7351 | 0.3444 | 0.1186 | 5.4895 |
| imbalance | 5.0000 | 0.7444 | 0.4018 | 0.1615 | 6.5677 |
| gap_bps | 10.0000 | 1.2332 | 0.3784 | 0.1432 | 4.2881 |
| imbalance | 10.0000 | 1.1498 | 0.4056 | 0.1645 | 4.6533 |

Joint regression on both signals (use these as beta_gap / beta_imb of as_signal):

| horizon_s | beta_gap | beta_imb | r2 |
|---|---|---|---|
| 0.1000 | -0.0062 | 0.0321 | 0.0280 |
| 0.2500 | -0.0080 | 0.0700 | 0.0498 |
| 0.5000 | -0.0128 | 0.1285 | 0.0754 |
| 1.0000 | -0.0144 | 0.2289 | 0.1084 |
| 2.0000 | 0.0217 | 0.3641 | 0.1313 |
| 5.0000 | 0.2339 | 0.5964 | 0.1671 |
| 10.0000 | 0.5754 | 0.7846 | 0.1791 |
