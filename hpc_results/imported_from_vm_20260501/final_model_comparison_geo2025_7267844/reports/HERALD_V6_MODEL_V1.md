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
| V6 full_final_geo2025_gate2.0_seed_0 | 0.0310 | -0.0358 | +0.0049 |
| V6 full_final_geo2025_gate2.0_seed_1 | 0.0360 | -0.0308 | +0.0099 |
| V6 full_final_geo2025_gate2.0_seed_123 | 0.0335 | -0.0333 | +0.0074 |
| V6 full_final_geo2025_gate2.0_seed_13 | 0.0292 | -0.0376 | +0.0031 |
| V6 full_final_geo2025_gate2.0_seed_42 | 0.0500 | -0.0168 | +0.0239 |
| V6 full_final_geo2025_gate2.0_seed_7 | 0.0253 | -0.0415 | -0.0008 |
| V6 full_final_geo2025_gate2.0_seed_99 | 0.0226 | -0.0442 | -0.0035 |

## Per-year total WMAPE — full_final_geo2025_gate2.0_seed_123

| Year | WMAPE |
|---:|---:|
| 2021 | 0.037948 |
| 2022 | 0.025236 |
| 2023 | 0.023214 |
| 2024 | 0.032083 |
| 2025 | 0.048840 |

## Per-sector WMAPE — full_final_geo2025_gate2.0_seed_123
Mean across sectors: 0.21985

| Sector | WMAPE |
|---|---:|
| RU | 0.12924 |
| OQ | 0.14940 |
| MN | 0.16375 |
| GI | 0.17174 |
| FZ | 0.22854 |
| LZ | 0.24192 |
| KZ | 0.24400 |
| BE | 0.30356 |
| JZ | 0.34649 |

## Mean predicted sector proportions (last fold)

| Sector | Predicted proportion |
|---|---:|
| GI | 0.2815 |
| MN | 0.1776 |
| RU | 0.1216 |
| BE | 0.1141 |
| OQ | 0.0973 |
| FZ | 0.0915 |
| LZ | 0.0463 |
| JZ | 0.0365 |
| KZ | 0.0337 |

## Graph deltas — full_final_geo2025_gate2.0_seed_123

| Transition index | regime_delta | adj_delta |
|---:|---:|---:|
| 1 | 0.000000 | 0.013633 |
| 2 | 0.327871 | 0.018531 |
| 3 | 0.806026 | 0.039011 |
| 4 | 0.794263 | 0.041080 |
| 5 | 1.333529 | 0.036587 |
| 6 | 0.200852 | 0.039628 |
| 7 | 0.758150 | 0.051906 |
| 8 | 1.302211 | 0.070677 |
| 9 | 3.748621 | 0.330588 |
| 10 | 2.976783 | 0.420116 |
| 11 | 2.339062 | 0.362356 |
| 12 | 0.372314 | 0.044380 |
| 13 | 1.546832 | 0.229669 |
