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
| V6 full_total_h64_semi_mask0.10_precovid_seed_17 | 0.0594 | -0.0074 | +0.0333 |
| V6 full_total_h64_semi_mask0.10_precovid_seed_42 | 0.0670 | +0.0002 | +0.0409 |

## Per-year total WMAPE — full_total_h64_semi_mask0.10_precovid_seed_42

| Year | WMAPE |
|---:|---:|
| 2016 | 0.171828 |
| 2017 | 0.036150 |
| 2018 | 0.023364 |
| 2019 | 0.036821 |

## Per-sector WMAPE — full_total_h64_semi_mask0.10_precovid_seed_42
Mean across sectors: 0.23581

| Sector | WMAPE |
|---|---:|
| RU | 0.13821 |
| GI | 0.16961 |
| MN | 0.18101 |
| OQ | 0.18384 |
| KZ | 0.23940 |
| FZ | 0.25370 |
| JZ | 0.27053 |
| LZ | 0.31004 |
| BE | 0.37592 |

## Mean predicted sector proportions (last fold)

| Sector | Predicted proportion |
|---|---:|
| GI | 0.3302 |
| MN | 0.1818 |
| OQ | 0.1141 |
| RU | 0.1072 |
| FZ | 0.1010 |
| BE | 0.0617 |
| LZ | 0.0425 |
| KZ | 0.0314 |
| JZ | 0.0303 |

## Graph deltas — full_total_h64_semi_mask0.10_precovid_seed_42

| Transition index | regime_delta | adj_delta |
|---:|---:|---:|
| 1 | 0.000000 | 0.287720 |
| 2 | 0.524640 | 0.900539 |
| 3 | 1.289755 | 2.286448 |
| 4 | 1.270932 | 2.201139 |
| 5 | 2.133833 | 1.877722 |
| 6 | 0.321391 | 1.031616 |
| 7 | 1.213145 | 1.288814 |
