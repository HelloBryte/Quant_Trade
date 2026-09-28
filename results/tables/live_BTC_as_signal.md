# v2 AS + signals (latency 50 ms)

- Duration: 60.0 min, fills: 99 (45 buys / 54 sells), orders sent: 3483, fill ratio: 0.028
- Fill types: {'cross': 52, 'through': 36, 'queue': 11}
- Traded notional: 8,999.99 USDT

| PnL component | USDT | bps of notional |
|---|---:|---:|
| Spread capture | 0.03 | 0.03 |
| Inventory | -1.67 | -1.85 |
| **Gross** | **-1.64** | **-1.82** |
| Fees (as simulated) | -0.00 | |
| **Net** | **-1.64** | |

Break-even maker fee: **-1.82 bps** (gross PnL per unit of notional; any fee above this loses money).

| Fee scenario | Net PnL (USDT) |
|---|---:|
| retail spot (10 bp) | -10.64 |
| retail perp (2 bp) | -3.44 |
| zero fee | -1.64 |
| MM rebate (-0.5 bp) | -1.19 |

| Markout horizon | fill | 0.1s | 0.5s | 1s | 2s | 5s | 10s | 30s | 60s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bps | 0.03 | -0.55 | -0.84 | -0.95 | -1.12 | -1.30 | -1.42 | -1.54 | -1.99 |
| s.e. | 0.04 | 0.06 | 0.11 | 0.12 | 0.16 | 0.24 | 0.34 | 0.52 | 0.70 |

- Inventory: mean |lots| 0.58, max |lots| 2.02
- Gross PnL std per minute: 0.054 USDT, max drawdown: 1.644 USDT


