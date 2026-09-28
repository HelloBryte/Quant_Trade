# v0 fixed spread (latency 50 ms)

- Duration: 60.0 min, fills: 682 (365 buys / 317 sells), orders sent: 4049, fill ratio: 0.168
- Fill types: {'queue': 327, 'cross': 318, 'through': 37}
- Traded notional: 42,370.05 USDT

| PnL component | USDT | bps of notional |
|---|---:|---:|
| Spread capture | -0.85 | -0.20 |
| Inventory | -5.66 | -1.34 |
| **Gross** | **-6.52** | **-1.54** |
| Fees (as simulated) | -0.00 | |
| **Net** | **-6.52** | |

Break-even maker fee: **-1.54 bps** (gross PnL per unit of notional; any fee above this loses money).

| Fee scenario | Net PnL (USDT) |
|---|---:|
| retail spot (10 bp) | -48.89 |
| retail perp (2 bp) | -14.99 |
| zero fee | -6.52 |
| MM rebate (-0.5 bp) | -4.40 |

| Markout horizon | fill | 0.1s | 0.5s | 1s | 2s | 5s | 10s | 30s | 60s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bps | -0.20 | -0.67 | -0.92 | -1.00 | -1.09 | -1.18 | -1.26 | -1.90 | -1.82 |
| s.e. | 0.02 | 0.03 | 0.05 | 0.06 | 0.09 | 0.14 | 0.19 | 0.38 | 0.48 |

- Inventory: mean |lots| 3.16, max |lots| 6.88
- Gross PnL std per minute: 0.380 USDT, max drawdown: 6.803 USDT


