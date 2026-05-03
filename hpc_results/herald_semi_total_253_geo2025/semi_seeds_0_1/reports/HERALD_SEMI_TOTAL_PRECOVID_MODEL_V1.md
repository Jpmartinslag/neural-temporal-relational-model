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
| V6 full_total_h64_semi_mask0.10_precovid_seed_0 | 0.0714 | +0.0047 | +0.0454 |
| V6 full_total_h64_semi_mask0.10_precovid_seed_1 | 0.0565 | -0.0103 | +0.0304 |

## Per-year total WMAPE — full_total_h64_semi_mask0.10_precovid_seed_1

| Year | WMAPE |
|---:|---:|
| 2016 | 0.111919 |
| 2017 | 0.059419 |
| 2018 | 0.019189 |
| 2019 | 0.035334 |

## Per-sector WMAPE — full_total_h64_semi_mask0.10_precovid_seed_1
Mean across sectors: 0.21132

| Sector | WMAPE |
|---|---:|
| RU | 0.12665 |
| GI | 0.13830 |
| MN | 0.16016 |
| OQ | 0.18179 |
| FZ | 0.22952 |
| KZ | 0.23973 |
| JZ | 0.24890 |
| LZ | 0.28633 |
| BE | 0.29051 |

## Mean predicted sector proportions (last fold)

| Sector | Predicted proportion |
|---|---:|
| GI | 0.3438 |
| MN | 0.1730 |
| OQ | 0.1143 |
| RU | 0.1051 |
| FZ | 0.1014 |
| BE | 0.0643 |
| LZ | 0.0395 |
| KZ | 0.0306 |
| JZ | 0.0280 |

## Graph deltas — full_total_h64_semi_mask0.10_precovid_seed_1

| Transition index | regime_delta | adj_delta |
|---:|---:|---:|
| 1 | 0.000000 | 0.391952 |
| 2 | 0.524640 | 1.072955 |
| 3 | 1.289755 | 2.248311 |
| 4 | 1.270932 | 1.502139 |
| 5 | 2.133833 | 1.012770 |
| 6 | 0.321391 | 0.707511 |
| 7 | 1.213145 | 1.010437 |
