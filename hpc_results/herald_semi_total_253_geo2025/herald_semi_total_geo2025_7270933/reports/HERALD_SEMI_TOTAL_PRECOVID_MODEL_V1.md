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
| V6 full_total_h64_semi_mask0.10_precovid_seed_123 | 0.0826 | +0.0158 | +0.0565 |
| V6 full_total_h64_semi_mask0.10_precovid_seed_2025 | 0.0555 | -0.0113 | +0.0294 |

## Per-year total WMAPE — full_total_h64_semi_mask0.10_precovid_seed_2025

| Year | WMAPE |
|---:|---:|
| 2016 | 0.110608 |
| 2017 | 0.056497 |
| 2018 | 0.021124 |
| 2019 | 0.033633 |

## Per-sector WMAPE — full_total_h64_semi_mask0.10_precovid_seed_2025
Mean across sectors: 0.2035

| Sector | WMAPE |
|---|---:|
| RU | 0.10483 |
| MN | 0.13087 |
| GI | 0.14451 |
| OQ | 0.16624 |
| KZ | 0.22619 |
| FZ | 0.23457 |
| JZ | 0.24452 |
| LZ | 0.27297 |
| BE | 0.30683 |

## Mean predicted sector proportions (last fold)

| Sector | Predicted proportion |
|---|---:|
| GI | 0.3436 |
| MN | 0.1803 |
| OQ | 0.1180 |
| RU | 0.1027 |
| FZ | 0.1025 |
| BE | 0.0622 |
| LZ | 0.0347 |
| JZ | 0.0290 |
| KZ | 0.0270 |

## Graph deltas — full_total_h64_semi_mask0.10_precovid_seed_2025

| Transition index | regime_delta | adj_delta |
|---:|---:|---:|
| 1 | 0.000000 | 0.336566 |
| 2 | 0.524640 | 0.908242 |
| 3 | 1.289755 | 2.187147 |
| 4 | 1.270932 | 2.483119 |
| 5 | 2.133833 | 2.125211 |
| 6 | 0.321391 | 1.164199 |
| 7 | 1.213145 | 1.256940 |
