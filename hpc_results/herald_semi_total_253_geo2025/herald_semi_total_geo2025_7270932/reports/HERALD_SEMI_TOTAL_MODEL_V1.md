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
| V6 full_total_h32_semi_mask0.10_random_seed_77 | 0.0411 | -0.0257 | +0.0150 |
| V6 full_total_h32_semi_mask0.10_random_seed_99 | 0.0369 | -0.0299 | +0.0108 |
| V6 full_total_h64_semi_mask0.05_random_seed_77 | 0.0296 | -0.0372 | +0.0035 |
| V6 full_total_h64_semi_mask0.05_random_seed_99 | 0.0363 | -0.0305 | +0.0102 |
| V6 full_total_h64_semi_mask0.0_control_seed_77 | 0.0327 | -0.0341 | +0.0066 |
| V6 full_total_h64_semi_mask0.0_control_seed_99 | 0.0368 | -0.0300 | +0.0107 |
| V6 full_total_h64_semi_mask0.10_block_seed_77 | 0.0316 | -0.0352 | +0.0054 |
| V6 full_total_h64_semi_mask0.10_block_seed_99 | 0.0447 | -0.0221 | +0.0186 |
| V6 full_total_h64_semi_mask0.10_random_lam0.01_total_seed_77 | 0.0288 | -0.0380 | +0.0027 |
| V6 full_total_h64_semi_mask0.10_random_lam0.01_total_seed_99 | 0.0379 | -0.0289 | +0.0118 |
| V6 full_total_h64_semi_mask0.10_random_lam0.05_a10_seed_77 | 0.0298 | -0.0370 | +0.0037 |
| V6 full_total_h64_semi_mask0.10_random_lam0.05_a10_seed_99 | 0.0376 | -0.0292 | +0.0115 |
| V6 full_total_h64_semi_mask0.10_random_lam0.05_total_a10_seed_77 | 0.0333 | -0.0335 | +0.0072 |
| V6 full_total_h64_semi_mask0.10_random_lam0.05_total_a10_seed_99 | 0.0363 | -0.0305 | +0.0102 |
| V6 full_total_h64_semi_mask0.10_random_lam0.05_total_seed_77 | 0.0333 | -0.0335 | +0.0072 |
| V6 full_total_h64_semi_mask0.10_random_lam0.05_total_seed_99 | 0.0363 | -0.0305 | +0.0102 |
| V6 full_total_h64_semi_mask0.10_random_lam0.10_total_seed_77 | 0.0334 | -0.0334 | +0.0073 |
| V6 full_total_h64_semi_mask0.10_random_lam0.10_total_seed_99 | 0.0410 | -0.0258 | +0.0149 |
| V6 full_total_h64_semi_mask0.10_random_seed_77 | 0.0298 | -0.0370 | +0.0037 |
| V6 full_total_h64_semi_mask0.10_random_seed_99 | 0.0376 | -0.0292 | +0.0115 |
| V6 full_total_h64_semi_mask0.10_random_warmup0_seed_77 | 0.0310 | -0.0358 | +0.0049 |
| V6 full_total_h64_semi_mask0.10_random_warmup0_seed_99 | 0.0311 | -0.0357 | +0.0050 |
| V6 full_total_h64_semi_mask0.10_spatial_block_seed_77 | 0.0365 | -0.0303 | +0.0104 |
| V6 full_total_h64_semi_mask0.10_spatial_block_seed_99 | 0.0353 | -0.0315 | +0.0092 |
| V6 full_total_h64_semi_mask0.15_random_seed_77 | 0.0340 | -0.0328 | +0.0079 |
| V6 full_total_h64_semi_mask0.15_random_seed_99 | 0.0368 | -0.0300 | +0.0107 |
| V6 full_total_h64_semi_mask0.20_block_seed_77 | 0.0292 | -0.0376 | +0.0031 |
| V6 full_total_h64_semi_mask0.20_block_seed_99 | 0.0464 | -0.0204 | +0.0203 |
| V6 full_total_h64_semi_mask0.20_random_seed_77 | 0.0354 | -0.0314 | +0.0093 |
| V6 full_total_h64_semi_mask0.20_random_seed_99 | 0.0358 | -0.0310 | +0.0097 |
| V6 full_total_h64_semi_mask0.20_spatial_block_seed_77 | 0.0312 | -0.0356 | +0.0051 |
| V6 full_total_h64_semi_mask0.20_spatial_block_seed_99 | 0.0477 | -0.0191 | +0.0216 |
| V6 full_total_h64_semi_mask0.30_random_seed_77 | 0.0325 | -0.0343 | +0.0064 |
| V6 full_total_h64_semi_mask0.30_random_seed_99 | 0.0324 | -0.0344 | +0.0063 |

## Per-year total WMAPE — full_total_h64_semi_mask0.10_random_warmup0_seed_99

| Year | WMAPE |
|---:|---:|
| 2021 | 0.030578 |
| 2022 | 0.028106 |
| 2023 | 0.029470 |
| 2024 | 0.033106 |
| 2025 | 0.034467 |

## Per-sector WMAPE — full_total_h64_semi_mask0.10_random_warmup0_seed_99
Mean across sectors: 0.22679

| Sector | WMAPE |
|---|---:|
| RU | 0.10851 |
| OQ | 0.11754 |
| MN | 0.11830 |
| GI | 0.20524 |
| FZ | 0.20640 |
| LZ | 0.26058 |
| BE | 0.27505 |
| KZ | 0.34425 |
| JZ | 0.40528 |

## Mean predicted sector proportions (last fold)

| Sector | Predicted proportion |
|---|---:|
| GI | 0.2698 |
| MN | 0.1964 |
| RU | 0.1235 |
| BE | 0.0990 |
| FZ | 0.0954 |
| OQ | 0.0931 |
| LZ | 0.0470 |
| JZ | 0.0418 |
| KZ | 0.0340 |

## Graph deltas — full_total_h64_semi_mask0.10_random_warmup0_seed_99

| Transition index | regime_delta | adj_delta |
|---:|---:|---:|
| 1 | 0.000000 | 0.016920 |
| 2 | 0.327871 | 0.018695 |
| 3 | 0.806026 | 0.029195 |
| 4 | 0.794263 | 0.029302 |
| 5 | 1.333529 | 0.045198 |
| 6 | 0.200852 | 0.032969 |
| 7 | 0.758150 | 0.058593 |
| 8 | 1.302211 | 0.061140 |
| 9 | 3.748621 | 0.358793 |
| 10 | 2.976783 | 0.311597 |
| 11 | 2.339062 | 0.211698 |
| 12 | 0.372314 | 0.033313 |
| 13 | 1.546832 | 0.110531 |
