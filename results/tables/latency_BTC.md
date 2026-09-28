# Sweep: binance BTCUSDT

Data: binance_BTCUSDT_60m.jsonl.gz, minutes 20 to end. Shared params: {'k': 1.0, 'gamma': 0.05, 'fixed.half_spread_bps': 1.0, 'as_signal.beta_gap': 0.0, 'as_signal.beta_imb': 0.25}. Maker fee as simulated: 0.0 bp.

| strategy | latency ms | fills | spread capture bp | inventory bp | gross = break-even fee bp | gross USDT | markout 5s bp (± s.e.) | mean abs lots |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| v0 fixed spread | 5 | 50 | 0.17 | -0.59 | -0.42 | -0.21 | -0.84 ± 0.18 | 1.12 |
| v1 Avellaneda-Stoikov | 5 | 30 | 0.07 | -0.42 | -0.35 | -0.10 | -0.85 ± 0.21 | 0.22 |
| v2 AS + signals | 5 | 13 | 0.16 | -1.66 | -1.49 | -0.15 | -1.66 ± 0.39 | 0.08 |
| v0 fixed spread | 50 | 121 | 0.11 | -1.34 | -1.23 | -1.24 | -0.94 ± 0.12 | 3.15 |
| v1 Avellaneda-Stoikov | 50 | 69 | 0.03 | -1.63 | -1.59 | -1.08 | -1.05 ± 0.14 | 0.61 |
| v2 AS + signals | 50 | 53 | 0.07 | -1.07 | -1.00 | -0.53 | -0.94 ± 0.17 | 0.47 |
| v0 fixed spread | 200 | 133 | 0.05 | -1.85 | -1.81 | -2.10 | -1.02 ± 0.12 | 2.88 |
| v1 Avellaneda-Stoikov | 200 | 106 | -0.01 | -1.49 | -1.50 | -1.59 | -1.02 ± 0.13 | 0.89 |
| v2 AS + signals | 200 | 90 | -0.01 | -1.09 | -1.11 | -0.92 | -1.03 ± 0.15 | 0.62 |
| v0 fixed spread | 500 | 137 | 0.01 | -1.88 | -1.87 | -2.28 | -1.01 ± 0.11 | 3.17 |
| v1 Avellaneda-Stoikov | 500 | 110 | -0.06 | -1.46 | -1.52 | -1.67 | -1.07 ± 0.11 | 0.95 |
| v2 AS + signals | 500 | 94 | -0.04 | -1.03 | -1.07 | -1.01 | -0.98 ± 0.14 | 0.69 |




