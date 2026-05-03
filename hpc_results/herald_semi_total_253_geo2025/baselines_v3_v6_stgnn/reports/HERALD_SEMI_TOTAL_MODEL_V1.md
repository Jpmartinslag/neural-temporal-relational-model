# HERALD V6 — dynamic graph + A10 sector head

## Architecture
- Regime-exclusive covid/rebound flags by default
- e_t from concat([annual, quarterly, h]) + projection
- Dynamic A_t with regime shifts in queries and keys
- Conditional graph smooth/contrast loss
- Gate excludes regime and starts from configurable bias
- Sector head uses concat([h_t, stop_gradient(total_resid)])
- Final sector: final_total × sector_proportions[:, s]

| Run | Total WMAPE | vs Ridge AR | vs HERALD V3 |
|---|---:|---:|---:|
| Ridge AR | 0.0668 | — | — |
| HERALD V3 full (ref) | 0.0261 | -0.0407 | — |
| V6 full_total_h32_semi_mask0.10_random_seed_0 | 0.0340 | -0.0328 | +0.0079 |
| V6 full_total_h32_semi_mask0.10_random_seed_1 | 0.0403 | -0.0265 | +0.0142 |

## Per-year total WMAPE — full_total_h32_semi_mask0.10_random_seed_1

| Year | WMAPE |
|---:|---:|
| 2021 | 0.035935 |
| 2022 | 0.034313 |
| 2023 | 0.033012 |
| 2024 | 0.024392 |
| 2025 | 0.073628 |

## Per-sector WMAPE — full_total_h32_semi_mask0.10_random_seed_1
Mean across sectors: 0.24003

| Sector | WMAPE |
|---|---:|
| RU | 0.12367 |
| OQ | 0.14598 |
| MN | 0.16114 |
| GI | 0.20442 |
| FZ | 0.20926 |
| LZ | 0.25446 |
| BE | 0.27551 |
| KZ | 0.35085 |
| JZ | 0.43495 |

## Mean predicted sector proportions (last fold)

| Sector | Predicted proportion |
|---|---:|
| GI | 0.2967 |
| MN | 0.1869 |
| RU | 0.1161 |
| FZ | 0.0999 |
| OQ | 0.0966 |
| BE | 0.0896 |
| LZ | 0.0447 |
| JZ | 0.0361 |
| KZ | 0.0333 |

## Graph deltas — full_total_h32_semi_mask0.10_random_seed_1

| Transition index | regime_delta | adj_delta |
|---:|---:|---:|
| 1 | 0.000000 | 0.013173 |
| 2 | 0.327871 | 0.034812 |
| 3 | 0.806026 | 0.067112 |
| 4 | 0.794263 | 0.038367 |
| 5 | 1.333529 | 0.031412 |
| 6 | 0.200852 | 0.036901 |
| 7 | 0.758150 | 0.034713 |
| 8 | 1.302211 | 0.058491 |
| 9 | 3.748621 | 0.236225 |
| 10 | 2.976783 | 0.231742 |
| 11 | 2.339062 | 0.058877 |
| 12 | 0.372314 | 0.033142 |
| 13 | 1.546832 | 0.083836 |
