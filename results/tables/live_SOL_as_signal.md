# v2 AS + signals (latency 50 ms)

- Duration: 60.0 min, fills: 184 (90 buys / 94 sells), orders sent: 5227, fill ratio: 0.035
- Fill types: {'queue': 97, 'cross': 81, 'through': 6}
- Traded notional: 11,222.06 USDT

| PnL component | USDT | bps of notional |
|---|---:|---:|
| Spread capture | -0.23 | -0.21 |
| Inventory | -1.43 | -1.28 |
| **Gross** | **-1.67** | **-1.49** |
| Fees (as simulated) | -0.00 | |
| **Net** | **-1.67** | |

Break-even maker fee: **-1.49 bps** (gross PnL per unit of notional; any fee above this loses money).

| Fee scenario | Net PnL (USDT) |
|---|---:|
| retail spot (10 bp) | -12.89 |
| retail perp (2 bp) | -3.91 |
| zero fee | -1.67 |
| MM rebate (-0.5 bp) | -1.11 |

| Markout horizon | fill | 0.1s | 0.5s | 1s | 2s | 5s | 10s | 30s | 60s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bps | -0.21 | -0.68 | -0.99 | -1.05 | -1.28 | -1.45 | -1.20 | -1.24 | -1.07 |
| s.e. | 0.04 | 0.05 | 0.09 | 0.11 | 0.16 | 0.20 | 0.29 | 0.50 | 0.71 |

- Inventory: mean |lots| 0.31, max |lots| 2.08
- Gross PnL std per minute: 0.043 USDT, max drawdown: 1.667 USDT


