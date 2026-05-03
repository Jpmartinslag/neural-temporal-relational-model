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
| V6 full_total_h32_no_semi_seed_0 | 0.0301 | -0.0367 | +0.0040 |
| V6 full_total_h32_no_semi_seed_1 | 0.0346 | -0.0322 | +0.0085 |
| V6 full_total_h32_no_semi_seed_123 | 0.0320 | -0.0348 | +0.0059 |
| V6 full_total_h32_no_semi_seed_13 | 0.0307 | -0.0361 | +0.0046 |
| V6 full_total_h32_no_semi_seed_17 | 0.0350 | -0.0318 | +0.0089 |
| V6 full_total_h32_no_semi_seed_2025 | 0.0384 | -0.0284 | +0.0123 |
| V6 full_total_h32_no_semi_seed_42 | 0.0513 | -0.0155 | +0.0252 |
| V6 full_total_h32_no_semi_seed_7 | 0.0252 | -0.0416 | -0.0009 |
| V6 full_total_h32_no_semi_seed_77 | 0.0347 | -0.0321 | +0.0086 |
| V6 full_total_h32_no_semi_seed_99 | 0.0241 | -0.0427 | -0.0020 |
| V6 full_total_h64_no_semi_seed_0 | 0.0267 | -0.0401 | +0.0006 |
| V6 full_total_h64_no_semi_seed_1 | 0.0312 | -0.0356 | +0.0051 |
| V6 full_total_h64_no_semi_seed_123 | 0.0334 | -0.0334 | +0.0073 |
| V6 full_total_h64_no_semi_seed_13 | 0.0272 | -0.0396 | +0.0011 |
| V6 full_total_h64_no_semi_seed_17 | 0.0323 | -0.0345 | +0.0062 |
| V6 full_total_h64_no_semi_seed_2025 | 0.0340 | -0.0328 | +0.0079 |
| V6 full_total_h64_no_semi_seed_42 | 0.0298 | -0.0370 | +0.0037 |
| V6 full_total_h64_no_semi_seed_7 | 0.0262 | -0.0406 | +0.0001 |
| V6 full_total_h64_no_semi_seed_77 | 0.0294 | -0.0374 | +0.0033 |
| V6 full_total_h64_no_semi_seed_99 | 0.0427 | -0.0241 | +0.0166 |

## Per-year total WMAPE — full_total_h64_no_semi_seed_2025

| Year | WMAPE |
|---:|---:|
| 2021 | 0.037342 |
| 2022 | 0.017947 |
| 2023 | 0.036903 |
| 2024 | 0.026323 |
| 2025 | 0.051250 |

## Per-sector WMAPE — full_total_h64_no_semi_seed_2025
Mean across sectors: 0.20232

| Sector | WMAPE |
|---|---:|
| MN | 0.10878 |
| RU | 0.11552 |
| OQ | 0.12267 |
| GI | 0.18317 |
| FZ | 0.20414 |
| LZ | 0.25282 |
| KZ | 0.26487 |
| BE | 0.27344 |
| JZ | 0.29548 |

## Mean predicted sector proportions (last fold)

| Sector | Predicted proportion |
|---|---:|
| GI | 0.2512 |
| MN | 0.1965 |
| RU | 0.1244 |
| BE | 0.1164 |
| OQ | 0.0950 |
| FZ | 0.0935 |
| LZ | 0.0505 |
| JZ | 0.0371 |
| KZ | 0.0353 |

## Graph deltas — full_total_h64_no_semi_seed_2025

| Transition index | regime_delta | adj_delta |
|---:|---:|---:|
| 1 | 0.000000 | 0.006749 |
| 2 | 0.327871 | 0.012254 |
| 3 | 0.806026 | 0.027833 |
| 4 | 0.794263 | 0.026862 |
| 5 | 1.333529 | 0.031050 |
| 6 | 0.200852 | 0.020507 |
| 7 | 0.758150 | 0.026826 |
| 8 | 1.302211 | 0.042545 |
| 9 | 3.748621 | 0.261571 |
| 10 | 2.976783 | 0.265912 |
| 11 | 2.339062 | 0.118666 |
| 12 | 0.372314 | 0.021442 |
| 13 | 1.546832 | 0.087927 |
