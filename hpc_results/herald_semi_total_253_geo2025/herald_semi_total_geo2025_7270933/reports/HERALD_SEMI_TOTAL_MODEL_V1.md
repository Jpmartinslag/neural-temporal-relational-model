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
| V6 full_total_h32_semi_mask0.10_random_seed_123 | 0.0368 | -0.0300 | +0.0107 |
| V6 full_total_h32_semi_mask0.10_random_seed_2025 | 0.0515 | -0.0153 | +0.0254 |
| V6 full_total_h64_semi_mask0.05_random_seed_123 | 0.0327 | -0.0341 | +0.0066 |
| V6 full_total_h64_semi_mask0.05_random_seed_2025 | 0.0310 | -0.0358 | +0.0049 |
| V6 full_total_h64_semi_mask0.0_control_seed_123 | 0.0305 | -0.0363 | +0.0044 |
| V6 full_total_h64_semi_mask0.0_control_seed_2025 | 0.0321 | -0.0347 | +0.0060 |
| V6 full_total_h64_semi_mask0.10_block_seed_123 | 0.0430 | -0.0238 | +0.0169 |
| V6 full_total_h64_semi_mask0.10_block_seed_2025 | 0.0344 | -0.0324 | +0.0083 |
| V6 full_total_h64_semi_mask0.10_random_lam0.01_total_seed_123 | 0.0379 | -0.0289 | +0.0118 |
| V6 full_total_h64_semi_mask0.10_random_lam0.01_total_seed_2025 | 0.0361 | -0.0307 | +0.0100 |
| V6 full_total_h64_semi_mask0.10_random_lam0.05_a10_seed_123 | 0.0363 | -0.0305 | +0.0102 |
| V6 full_total_h64_semi_mask0.10_random_lam0.05_a10_seed_2025 | 0.0370 | -0.0298 | +0.0109 |
| V6 full_total_h64_semi_mask0.10_random_lam0.05_total_a10_seed_123 | 0.0351 | -0.0317 | +0.0090 |
| V6 full_total_h64_semi_mask0.10_random_lam0.05_total_a10_seed_2025 | 0.0321 | -0.0347 | +0.0060 |
| V6 full_total_h64_semi_mask0.10_random_lam0.05_total_seed_123 | 0.0351 | -0.0317 | +0.0090 |
| V6 full_total_h64_semi_mask0.10_random_lam0.05_total_seed_2025 | 0.0321 | -0.0347 | +0.0060 |
| V6 full_total_h64_semi_mask0.10_random_lam0.10_total_seed_123 | 0.0351 | -0.0317 | +0.0090 |
| V6 full_total_h64_semi_mask0.10_random_lam0.10_total_seed_2025 | 0.0331 | -0.0337 | +0.0070 |
| V6 full_total_h64_semi_mask0.10_random_seed_123 | 0.0363 | -0.0305 | +0.0102 |
| V6 full_total_h64_semi_mask0.10_random_seed_2025 | 0.0370 | -0.0298 | +0.0109 |
| V6 full_total_h64_semi_mask0.10_random_warmup0_seed_123 | 0.0311 | -0.0357 | +0.0050 |
| V6 full_total_h64_semi_mask0.10_random_warmup0_seed_2025 | 0.0321 | -0.0347 | +0.0060 |
| V6 full_total_h64_semi_mask0.10_spatial_block_seed_123 | 0.0528 | -0.0140 | +0.0267 |
| V6 full_total_h64_semi_mask0.10_spatial_block_seed_2025 | 0.0451 | -0.0217 | +0.0190 |
| V6 full_total_h64_semi_mask0.15_random_seed_123 | 0.0379 | -0.0289 | +0.0118 |
| V6 full_total_h64_semi_mask0.15_random_seed_2025 | 0.0362 | -0.0306 | +0.0101 |
| V6 full_total_h64_semi_mask0.20_block_seed_123 | 0.0358 | -0.0310 | +0.0097 |
| V6 full_total_h64_semi_mask0.20_block_seed_2025 | 0.0359 | -0.0309 | +0.0098 |
| V6 full_total_h64_semi_mask0.20_random_seed_123 | 0.0397 | -0.0271 | +0.0136 |
| V6 full_total_h64_semi_mask0.20_random_seed_2025 | 0.0323 | -0.0345 | +0.0062 |
| V6 full_total_h64_semi_mask0.20_spatial_block_seed_123 | 0.0569 | -0.0099 | +0.0308 |
| V6 full_total_h64_semi_mask0.20_spatial_block_seed_2025 | 0.0650 | -0.0018 | +0.0389 |
| V6 full_total_h64_semi_mask0.30_random_seed_123 | 0.0335 | -0.0333 | +0.0074 |
| V6 full_total_h64_semi_mask0.30_random_seed_2025 | 0.0316 | -0.0352 | +0.0055 |

## Per-year total WMAPE — full_total_h64_semi_mask0.10_random_warmup0_seed_2025

| Year | WMAPE |
|---:|---:|
| 2021 | 0.049058 |
| 2022 | 0.025435 |
| 2023 | 0.025120 |
| 2024 | 0.032602 |
| 2025 | 0.028439 |

## Per-sector WMAPE — full_total_h64_semi_mask0.10_random_warmup0_seed_2025
Mean across sectors: 0.23237

| Sector | WMAPE |
|---|---:|
| MN | 0.08987 |
| OQ | 0.12549 |
| RU | 0.13598 |
| FZ | 0.19245 |
| GI | 0.22343 |
| LZ | 0.26755 |
| BE | 0.29045 |
| KZ | 0.36227 |
| JZ | 0.40383 |

## Mean predicted sector proportions (last fold)

| Sector | Predicted proportion |
|---|---:|
| GI | 0.2647 |
| MN | 0.2012 |
| RU | 0.1185 |
| BE | 0.1097 |
| FZ | 0.0934 |
| OQ | 0.0896 |
| LZ | 0.0489 |
| JZ | 0.0396 |
| KZ | 0.0345 |

## Graph deltas — full_total_h64_semi_mask0.10_random_warmup0_seed_2025

| Transition index | regime_delta | adj_delta |
|---:|---:|---:|
| 1 | 0.000000 | 0.022256 |
| 2 | 0.327871 | 0.025324 |
| 3 | 0.806026 | 0.035440 |
| 4 | 0.794263 | 0.051268 |
| 5 | 1.333529 | 0.058588 |
| 6 | 0.200852 | 0.024382 |
| 7 | 0.758150 | 0.039098 |
| 8 | 1.302211 | 0.059688 |
| 9 | 3.748621 | 0.213817 |
| 10 | 2.976783 | 0.223159 |
| 11 | 2.339062 | 0.141173 |
| 12 | 0.372314 | 0.038206 |
| 13 | 1.546832 | 0.146839 |
