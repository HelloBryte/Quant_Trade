# v0 fixed spread (latency 50 ms)

- Duration: 60.0 min, fills: 279 (136 buys / 143 sells), orders sent: 2553, fill ratio: 0.109
- Fill types: {'cross': 128, 'through': 116, 'queue': 35}
- Traded notional: 24,900.05 USDT

| PnL component | USDT | bps of notional |
|---|---:|---:|
| Spread capture | 0.21 | 0.08 |
| Inventory | -4.36 | -1.75 |
| **Gross** | **-4.16** | **-1.67** |
| Fees (as simulated) | -0.00 | |
| **Net** | **-4.16** | |

Break-even maker fee: **-1.67 bps** (gross PnL per unit of notional; any fee above this loses money).

| Fee scenario | Net PnL (USDT) |
|---|---:|
| retail spot (10 bp) | -29.06 |
| retail perp (2 bp) | -9.14 |
| zero fee | -4.16 |
| MM rebate (-0.5 bp) | -2.91 |

| Markout horizon | fill | 0.1s | 0.5s | 1s | 2s | 5s | 10s | 30s | 60s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bps | 0.08 | -0.49 | -0.74 | -0.87 | -0.94 | -1.22 | -1.37 | -1.63 | -1.65 |
| s.e. | 0.03 | 0.03 | 0.05 | 0.07 | 0.09 | 0.15 | 0.23 | 0.43 | 0.56 |

- Inventory: mean |lots| 2.91, max |lots| 6.06
- Gross PnL std per minute: 0.227 USDT, max drawdown: 4.174 USDT


