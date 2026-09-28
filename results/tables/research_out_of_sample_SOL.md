# Signal research: binance SOLUSDT (2026-09-28T12:20:26+00:00)

Grid: 47,964 samples at 50 ms (40.0 min).

Lead-lag peak: corr 0.608 at +0 ms (positive = perp moves first). Corr at 0 ms: 0.608.



Predictive regressions (future spot return in bps on the signal at t):

| signal | horizon_s | beta | corr | r2 | t_stat_nonoverlap |
|---|---|---|---|---|---|
| gap_bps | 0.1000 | 0.0437 | 0.1272 | 0.0162 | 19.6017 |
| imbalance | 0.1000 | 0.0886 | 0.2028 | 0.0411 | 31.6646 |
| gap_bps | 0.2500 | 0.0930 | 0.1618 | 0.0262 | 15.8567 |
| imbalance | 0.2500 | 0.1897 | 0.2597 | 0.0674 | 25.9997 |
| gap_bps | 0.5000 | 0.1609 | 0.1882 | 0.0354 | 13.1015 |
| imbalance | 0.5000 | 0.3221 | 0.2963 | 0.0878 | 21.2084 |
| gap_bps | 1.0000 | 0.2620 | 0.2057 | 0.0423 | 10.1573 |
| imbalance | 1.0000 | 0.5150 | 0.3179 | 0.1011 | 16.2022 |
| gap_bps | 2.0000 | 0.4116 | 0.2178 | 0.0475 | 7.6219 |
| imbalance | 2.0000 | 0.7845 | 0.3264 | 0.1065 | 11.7915 |
| gap_bps | 5.0000 | 0.5913 | 0.1822 | 0.0332 | 3.9926 |
| imbalance | 5.0000 | 1.1537 | 0.2792 | 0.0779 | 6.2628 |
| gap_bps | 10.0000 | 0.4585 | 0.0935 | 0.0087 | 1.4235 |
| imbalance | 10.0000 | 1.2373 | 0.1976 | 0.0391 | 3.0573 |

Joint regression on both signals (use these as beta_gap / beta_imb of as_signal):

| horizon_s | beta_gap | beta_imb | r2 |
|---|---|---|---|
| 0.1000 | 0.0176 | 0.0792 | 0.0433 |
| 0.2500 | 0.0371 | 0.1700 | 0.0709 |
| 0.5000 | 0.0667 | 0.2867 | 0.0928 |
| 1.0000 | 0.1124 | 0.4552 | 0.1075 |
| 2.0000 | 0.1865 | 0.6853 | 0.1146 |
| 5.0000 | 0.2583 | 1.0164 | 0.0832 |
| 10.0000 | 0.0649 | 1.2027 | 0.0392 |
