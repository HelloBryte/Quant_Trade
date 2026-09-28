# Signal research: binance SOLUSDT (2026-09-28T12:20:26+00:00)

Grid: 23,980 samples at 50 ms (20.0 min).

Lead-lag peak: corr 0.589 at +0 ms (positive = perp moves first). Corr at 0 ms: 0.589.



Predictive regressions (future spot return in bps on the signal at t):

| signal | horizon_s | beta | corr | r2 | t_stat_nonoverlap |
|---|---|---|---|---|---|
| gap_bps | 0.1000 | 0.0290 | 0.0809 | 0.0065 | 8.6601 |
| imbalance | 0.1000 | 0.1055 | 0.2133 | 0.0455 | 23.2955 |
| gap_bps | 0.2500 | 0.0628 | 0.1027 | 0.0106 | 6.9684 |
| imbalance | 0.2500 | 0.2218 | 0.2633 | 0.0693 | 18.4127 |
| gap_bps | 0.5000 | 0.1061 | 0.1174 | 0.0138 | 5.6408 |
| imbalance | 0.5000 | 0.3776 | 0.3034 | 0.0921 | 15.1873 |
| gap_bps | 1.0000 | 0.1784 | 0.1329 | 0.0177 | 4.5205 |
| imbalance | 1.0000 | 0.6101 | 0.3297 | 0.1087 | 11.7688 |
| gap_bps | 2.0000 | 0.2596 | 0.1302 | 0.0170 | 3.1252 |
| imbalance | 2.0000 | 0.9131 | 0.3318 | 0.1101 | 8.3682 |
| gap_bps | 5.0000 | 0.3415 | 0.1030 | 0.0106 | 1.5503 |
| imbalance | 5.0000 | 1.3944 | 0.3040 | 0.0924 | 4.7759 |
| gap_bps | 10.0000 | 0.1744 | 0.0369 | 0.0014 | 0.3873 |
| imbalance | 10.0000 | 1.6770 | 0.2559 | 0.0655 | 2.7759 |

Joint regression on both signals (use these as beta_gap / beta_imb of as_signal):

| horizon_s | beta_gap | beta_imb | r2 |
|---|---|---|---|
| 0.1000 | 0.0089 | 0.1022 | 0.0461 |
| 0.2500 | 0.0205 | 0.2141 | 0.0703 |
| 0.5000 | 0.0340 | 0.3649 | 0.0934 |
| 1.0000 | 0.0627 | 0.5866 | 0.1107 |
| 2.0000 | 0.0863 | 0.8807 | 0.1118 |
| 5.0000 | 0.0740 | 1.3666 | 0.0929 |
| 10.0000 | -0.1650 | 1.7389 | 0.0666 |
