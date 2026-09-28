# v1 Avellaneda-Stoikov (latency 50 ms)

- Duration: 60.0 min, fills: 206 (120 buys / 86 sells), orders sent: 4523, fill ratio: 0.046
- Fill types: {'queue': 106, 'cross': 97, 'through': 3}
- Traded notional: 12,569.07 USDT

| PnL component | USDT | bps of notional |
|---|---:|---:|
| Spread capture | -0.29 | -0.23 |
| Inventory | -1.27 | -1.01 |
| **Gross** | **-1.55** | **-1.24** |
| Fees (as simulated) | -0.00 | |
| **Net** | **-1.55** | |

Break-even maker fee: **-1.24 bps** (gross PnL per unit of notional; any fee above this loses money).

| Fee scenario | Net PnL (USDT) |
|---|---:|
| retail spot (10 bp) | -14.12 |
| retail perp (2 bp) | -4.07 |
| zero fee | -1.55 |
| MM rebate (-0.5 bp) | -0.93 |

| Markout horizon | fill | 0.1s | 0.5s | 1s | 2s | 5s | 10s | 30s | 60s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bps | -0.23 | -0.51 | -0.75 | -0.77 | -0.90 | -1.14 | -0.76 | -0.75 | -0.84 |
| s.e. | 0.03 | 0.05 | 0.09 | 0.10 | 0.14 | 0.20 | 0.26 | 0.46 | 0.57 |

- Inventory: mean |lots| 0.39, max |lots| 2.49
- Gross PnL std per minute: 0.045 USDT, max drawdown: 1.568 USDT


