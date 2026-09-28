# Signal research: binance BTCUSDT (2026-09-28T12:20:26+00:00)

Grid: 47,981 samples at 50 ms (40.0 min).

Lead-lag peak: corr 0.548 at +0 ms (positive = perp moves first). Corr at 0 ms: 0.548.



Predictive regressions (future spot return in bps on the signal at t):

| signal | horizon_s | beta | corr | r2 | t_stat_nonoverlap |
|---|---|---|---|---|---|
| gap_bps | 0.1000 | 0.0306 | 0.1261 | 0.0159 | 19.4372 |
| imbalance | 0.1000 | 0.0286 | 0.1640 | 0.0269 | 25.4179 |
| gap_bps | 0.2500 | 0.0723 | 0.1787 | 0.0319 | 17.5671 |
| imbalance | 0.2500 | 0.0658 | 0.2258 | 0.0510 | 22.4139 |
| gap_bps | 0.5000 | 0.1353 | 0.2242 | 0.0502 | 15.7262 |
| imbalance | 0.5000 | 0.1219 | 0.2803 | 0.0786 | 19.9684 |
| gap_bps | 1.0000 | 0.2523 | 0.2778 | 0.0772 | 13.9749 |
| imbalance | 1.0000 | 0.2193 | 0.3350 | 0.1123 | 17.1866 |
| gap_bps | 2.0000 | 0.4562 | 0.3317 | 0.1100 | 12.0043 |
| imbalance | 2.0000 | 0.3714 | 0.3749 | 0.1405 | 13.8086 |
| gap_bps | 5.0000 | 0.9413 | 0.3948 | 0.1559 | 9.2557 |
| imbalance | 5.0000 | 0.6890 | 0.4011 | 0.1609 | 9.4324 |
| gap_bps | 10.0000 | 1.3061 | 0.3502 | 0.1226 | 5.6699 |
| imbalance | 10.0000 | 0.8507 | 0.3163 | 0.1000 | 5.0557 |

Joint regression on both signals (use these as beta_gap / beta_imb of as_signal):

| horizon_s | beta_gap | beta_imb | r2 |
|---|---|---|---|
| 0.1000 | 0.0098 | 0.0243 | 0.0279 |
| 0.2500 | 0.0259 | 0.0543 | 0.0535 |
| 0.5000 | 0.0502 | 0.0997 | 0.0829 |
| 1.0000 | 0.1047 | 0.1728 | 0.1205 |
| 2.0000 | 0.2235 | 0.2724 | 0.1570 |
| 5.0000 | 0.5676 | 0.4372 | 0.1961 |
| 10.0000 | 0.9339 | 0.4369 | 0.1391 |
