# v1 Avellaneda-Stoikov (latency 50 ms)

- Duration: 60.0 min, fills: 123 (59 buys / 64 sells), orders sent: 2793, fill ratio: 0.044
- Fill types: {'cross': 61, 'through': 48, 'queue': 14}
- Traded notional: 11,599.97 USDT

| PnL component | USDT | bps of notional |
|---|---:|---:|
| Spread capture | 0.03 | 0.03 |
| Inventory | -2.41 | -2.08 |
| **Gross** | **-2.38** | **-2.05** |
| Fees (as simulated) | -0.00 | |
| **Net** | **-2.38** | |

Break-even maker fee: **-2.05 bps** (gross PnL per unit of notional; any fee above this loses money).

| Fee scenario | Net PnL (USDT) |
|---|---:|
| retail spot (10 bp) | -13.98 |
| retail perp (2 bp) | -4.70 |
| zero fee | -2.38 |
| MM rebate (-0.5 bp) | -1.80 |

| Markout horizon | fill | 0.1s | 0.5s | 1s | 2s | 5s | 10s | 30s | 60s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bps | 0.03 | -0.51 | -0.70 | -0.78 | -0.98 | -1.18 | -1.34 | -1.70 | -2.08 |
| s.e. | 0.03 | 0.05 | 0.08 | 0.09 | 0.12 | 0.19 | 0.26 | 0.44 | 0.60 |

- Inventory: mean |lots| 0.59, max |lots| 4.03
- Gross PnL std per minute: 0.094 USDT, max drawdown: 2.384 USDT


