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
| V6 full_semi_mask0.10_precovid_seed_0 | 0.0557 | -0.0111 | +0.0296 |
| V6 full_semi_mask0.10_precovid_seed_13 | 0.0582 | -0.0086 | +0.0321 |
| V6 full_semi_mask0.10_precovid_seed_42 | 0.0606 | -0.0062 | +0.0345 |
| V6 full_semi_mask0.10_precovid_seed_7 | 0.0603 | -0.0065 | +0.0342 |
| V6 full_semi_mask0.10_precovid_seed_99 | 0.0545 | -0.0123 | +0.0284 |

## Per-year total WMAPE — full_semi_mask0.10_precovid_seed_99

| Year | WMAPE |
|---:|---:|
| 2016 | 0.108041 |
| 2017 | 0.049468 |
| 2018 | 0.028132 |
| 2019 | 0.032528 |

## Per-sector WMAPE — full_semi_mask0.10_precovid_seed_99
Mean across sectors: 0.23066

| Sector | WMAPE |
|---|---:|
| GI | 0.12347 |
| RU | 0.12664 |
| MN | 0.15045 |
| OQ | 0.20135 |
| KZ | 0.25206 |
| FZ | 0.26423 |
| LZ | 0.28384 |
| JZ | 0.31679 |
| BE | 0.35707 |

## Mean predicted sector proportions (last fold)

| Sector | Predicted proportion |
|---|---:|
| GI | 0.3231 |
| MN | 0.1792 |
| OQ | 0.1183 |
| FZ | 0.1044 |
| RU | 0.1038 |
| BE | 0.0668 |
| LZ | 0.0416 |
| KZ | 0.0324 |
| JZ | 0.0305 |

## Graph deltas — full_semi_mask0.10_precovid_seed_99

| Transition index | regime_delta | adj_delta |
|---:|---:|---:|
| 1 | 0.000000 | 0.374161 |
| 2 | 0.524640 | 1.124510 |
| 3 | 1.289755 | 2.135677 |
| 4 | 1.270932 | 1.649642 |
| 5 | 2.133833 | 1.747474 |
| 6 | 0.321391 | 0.849328 |
| 7 | 1.213145 | 1.675668 |
