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
| V6 full_total_h64_semi_mask0.10_precovid_seed_13 | 0.0562 | -0.0106 | +0.0301 |
| V6 full_total_h64_semi_mask0.10_precovid_seed_7 | 0.0553 | -0.0115 | +0.0292 |

## Per-year total WMAPE — full_total_h64_semi_mask0.10_precovid_seed_13

| Year | WMAPE |
|---:|---:|
| 2016 | 0.100291 |
| 2017 | 0.067082 |
| 2018 | 0.023198 |
| 2019 | 0.034072 |

## Per-sector WMAPE — full_total_h64_semi_mask0.10_precovid_seed_13
Mean across sectors: 0.22279

| Sector | WMAPE |
|---|---:|
| RU | 0.12720 |
| MN | 0.13283 |
| GI | 0.14144 |
| OQ | 0.17498 |
| FZ | 0.22769 |
| JZ | 0.26285 |
| LZ | 0.28242 |
| KZ | 0.31933 |
| BE | 0.33633 |

## Mean predicted sector proportions (last fold)

| Sector | Predicted proportion |
|---|---:|
| GI | 0.3287 |
| MN | 0.1774 |
| OQ | 0.1152 |
| FZ | 0.1069 |
| RU | 0.1045 |
| BE | 0.0635 |
| LZ | 0.0400 |
| JZ | 0.0330 |
| KZ | 0.0308 |

## Graph deltas — full_total_h64_semi_mask0.10_precovid_seed_13

| Transition index | regime_delta | adj_delta |
|---:|---:|---:|
| 1 | 0.000000 | 0.354690 |
| 2 | 0.524640 | 1.014311 |
| 3 | 1.289755 | 1.912556 |
| 4 | 1.270932 | 1.727599 |
| 5 | 2.133833 | 1.489229 |
| 6 | 0.321391 | 1.010751 |
| 7 | 1.213145 | 1.568664 |
