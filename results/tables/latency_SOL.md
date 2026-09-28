# Sweep: binance SOLUSDT

Data: binance_SOLUSDT_60m.jsonl.gz, minutes 20 to end. Shared params: {'k': 1.0, 'gamma': 0.05, 'fixed.half_spread_bps': 1.0, 'as_signal.beta_gap': 0.08, 'as_signal.beta_imb': 0.6}. Maker fee as simulated: 0.0 bp.

| strategy | latency ms | fills | spread capture bp | inventory bp | gross = break-even fee bp | gross USDT | markout 5s bp (± s.e.) | mean abs lots |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| v0 fixed spread | 5 | 99 | -0.30 | -0.42 | -0.71 | -0.52 | -0.81 ± 0.23 | 2.45 |
| v1 Avellaneda-Stoikov | 5 | 43 | -0.33 | -0.94 | -1.27 | -0.49 | -0.44 ± 0.42 | 0.35 |
| v2 AS + signals | 5 | 63 | -0.30 | -0.53 | -0.83 | -0.35 | -0.74 ± 0.38 | 0.19 |
| v0 fixed spread | 50 | 270 | -0.24 | -0.46 | -0.70 | -1.29 | -0.97 ± 0.14 | 3.10 |
| v1 Avellaneda-Stoikov | 50 | 139 | -0.25 | -0.89 | -1.14 | -1.05 | -1.08 ± 0.23 | 0.44 |
| v2 AS + signals | 50 | 155 | -0.25 | -0.42 | -0.67 | -0.57 | -0.97 ± 0.20 | 0.50 |
| v0 fixed spread | 200 | 389 | -0.25 | -1.74 | -1.99 | -4.58 | -1.25 ± 0.13 | 2.84 |
| v1 Avellaneda-Stoikov | 200 | 272 | -0.22 | -1.06 | -1.28 | -1.92 | -1.29 ± 0.16 | 0.60 |
| v2 AS + signals | 200 | 241 | -0.25 | -0.84 | -1.09 | -1.45 | -1.01 ± 0.15 | 0.56 |
| v0 fixed spread | 500 | 463 | -0.23 | -1.60 | -1.83 | -5.10 | -1.46 ± 0.11 | 2.80 |
| v1 Avellaneda-Stoikov | 500 | 341 | -0.23 | -0.91 | -1.15 | -1.99 | -0.92 ± 0.14 | 0.61 |
| v2 AS + signals | 500 | 333 | -0.24 | -0.76 | -1.00 | -1.76 | -0.94 ± 0.13 | 0.60 |




