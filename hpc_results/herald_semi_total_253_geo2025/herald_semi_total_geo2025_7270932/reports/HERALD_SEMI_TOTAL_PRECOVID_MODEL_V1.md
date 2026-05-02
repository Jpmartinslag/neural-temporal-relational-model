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
| V6 full_total_h64_semi_mask0.10_precovid_seed_77 | 0.0634 | -0.0034 | +0.0373 |
| V6 full_total_h64_semi_mask0.10_precovid_seed_99 | 0.0561 | -0.0107 | +0.0300 |

## Per-year total WMAPE — full_total_h64_semi_mask0.10_precovid_seed_99

| Year | WMAPE |
|---:|---:|
| 2016 | 0.106891 |
| 2017 | 0.059103 |
| 2018 | 0.025503 |
| 2019 | 0.033087 |

## Per-sector WMAPE — full_total_h64_semi_mask0.10_precovid_seed_99
Mean across sectors: 0.22768

| Sector | WMAPE |
|---|---:|
| RU | 0.13027 |
| MN | 0.14602 |
| GI | 0.14910 |
| OQ | 0.18990 |
| FZ | 0.24171 |
| KZ | 0.28606 |
| JZ | 0.28988 |
| BE | 0.29813 |
| LZ | 0.31808 |

## Mean predicted sector proportions (last fold)

| Sector | Predicted proportion |
|---|---:|
| GI | 0.3465 |
| MN | 0.1803 |
| OQ | 0.1130 |
| RU | 0.1022 |
| FZ | 0.1004 |
| BE | 0.0619 |
| LZ | 0.0361 |
| KZ | 0.0300 |
| JZ | 0.0296 |

## Graph deltas — full_total_h64_semi_mask0.10_precovid_seed_99

| Transition index | regime_delta | adj_delta |
|---:|---:|---:|
| 1 | 0.000000 | 0.222579 |
| 2 | 0.524640 | 0.856607 |
| 3 | 1.289755 | 2.547978 |
| 4 | 1.270932 | 2.146933 |
| 5 | 2.133833 | 1.604576 |
| 6 | 0.321391 | 0.892209 |
| 7 | 1.213145 | 0.977085 |
