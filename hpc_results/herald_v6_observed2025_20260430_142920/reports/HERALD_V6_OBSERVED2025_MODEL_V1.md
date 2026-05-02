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
| V6 full_observed2025_gate2_seed_0 | 0.0328 | -0.0340 | +0.0067 |
| V6 full_observed2025_gate2_seed_1 | 0.0329 | -0.0339 | +0.0068 |
| V6 full_observed2025_gate2_seed_123 | 0.0305 | -0.0363 | +0.0044 |
| V6 full_observed2025_gate2_seed_13 | 0.0353 | -0.0315 | +0.0092 |
| V6 full_observed2025_gate2_seed_42 | 0.0489 | -0.0179 | +0.0228 |
| V6 full_observed2025_gate2_seed_7 | 0.0232 | -0.0436 | -0.0029 |
| V6 full_observed2025_gate2_seed_99 | 0.0249 | -0.0419 | -0.0012 |

## Per-year total WMAPE — full_observed2025_gate2_seed_123

| Year | WMAPE |
|---:|---:|
| 2021 | 0.034466 |
| 2022 | 0.027782 |
| 2023 | 0.020422 |
| 2024 | 0.033200 |
| 2025 | 0.036429 |

## Per-sector WMAPE — full_observed2025_gate2_seed_123
Mean across sectors: 0.2164

| Sector | WMAPE |
|---|---:|
| RU | 0.13144 |
| MN | 0.15385 |
| OQ | 0.15535 |
| GI | 0.16703 |
| FZ | 0.22392 |
| LZ | 0.24524 |
| KZ | 0.24582 |
| BE | 0.30004 |
| JZ | 0.32492 |

## Mean predicted sector proportions (last fold)

| Sector | Predicted proportion |
|---|---:|
| GI | 0.2735 |
| MN | 0.1878 |
| RU | 0.1228 |
| BE | 0.1173 |
| OQ | 0.0920 |
| FZ | 0.0897 |
| LZ | 0.0463 |
| JZ | 0.0369 |
| KZ | 0.0337 |

## Graph deltas — full_observed2025_gate2_seed_123

| Transition index | regime_delta | adj_delta |
|---:|---:|---:|
| 1 | 0.000000 | 0.011160 |
| 2 | 0.327871 | 0.017858 |
| 3 | 0.806026 | 0.032997 |
| 4 | 0.794263 | 0.029015 |
| 5 | 1.333529 | 0.033389 |
| 6 | 0.200852 | 0.034428 |
| 7 | 0.758150 | 0.034981 |
| 8 | 1.302211 | 0.048052 |
| 9 | 3.748621 | 0.504745 |
| 10 | 2.976783 | 0.552921 |
| 11 | 2.339062 | 0.344220 |
| 12 | 0.372314 | 0.043012 |
| 13 | 1.769992 | 0.076772 |
