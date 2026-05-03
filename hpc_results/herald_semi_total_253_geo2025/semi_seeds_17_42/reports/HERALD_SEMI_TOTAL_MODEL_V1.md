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
| V6 full_total_h32_semi_mask0.10_random_seed_17 | 0.0358 | -0.0310 | +0.0097 |
| V6 full_total_h32_semi_mask0.10_random_seed_42 | 0.0418 | -0.0250 | +0.0157 |
| V6 full_total_h64_semi_mask0.05_random_seed_17 | 0.0445 | -0.0223 | +0.0184 |
| V6 full_total_h64_semi_mask0.05_random_seed_42 | 0.0310 | -0.0358 | +0.0049 |
| V6 full_total_h64_semi_mask0.0_control_seed_17 | 0.0323 | -0.0345 | +0.0062 |
| V6 full_total_h64_semi_mask0.0_control_seed_42 | 0.0298 | -0.0370 | +0.0037 |
| V6 full_total_h64_semi_mask0.10_block_seed_17 | 0.0301 | -0.0367 | +0.0040 |
| V6 full_total_h64_semi_mask0.10_block_seed_42 | 0.0336 | -0.0332 | +0.0075 |
| V6 full_total_h64_semi_mask0.10_random_lam0.01_total_seed_17 | 0.0381 | -0.0287 | +0.0120 |
| V6 full_total_h64_semi_mask0.10_random_lam0.01_total_seed_42 | 0.0356 | -0.0312 | +0.0095 |
| V6 full_total_h64_semi_mask0.10_random_lam0.05_a10_seed_17 | 0.0393 | -0.0275 | +0.0132 |
| V6 full_total_h64_semi_mask0.10_random_lam0.05_a10_seed_42 | 0.0352 | -0.0316 | +0.0091 |
| V6 full_total_h64_semi_mask0.10_random_lam0.05_total_a10_seed_17 | 0.0393 | -0.0275 | +0.0132 |
| V6 full_total_h64_semi_mask0.10_random_lam0.05_total_a10_seed_42 | 0.0347 | -0.0321 | +0.0086 |
| V6 full_total_h64_semi_mask0.10_random_lam0.05_total_seed_17 | 0.0393 | -0.0275 | +0.0132 |
| V6 full_total_h64_semi_mask0.10_random_lam0.05_total_seed_42 | 0.0347 | -0.0321 | +0.0086 |
| V6 full_total_h64_semi_mask0.10_random_lam0.10_total_seed_17 | 0.0353 | -0.0315 | +0.0092 |
| V6 full_total_h64_semi_mask0.10_random_lam0.10_total_seed_42 | 0.0342 | -0.0326 | +0.0081 |
| V6 full_total_h64_semi_mask0.10_random_seed_17 | 0.0393 | -0.0275 | +0.0132 |
| V6 full_total_h64_semi_mask0.10_random_seed_42 | 0.0352 | -0.0316 | +0.0091 |
| V6 full_total_h64_semi_mask0.10_random_warmup0_seed_17 | 0.0384 | -0.0284 | +0.0123 |
| V6 full_total_h64_semi_mask0.10_random_warmup0_seed_42 | 0.0254 | -0.0414 | -0.0007 |
| V6 full_total_h64_semi_mask0.10_spatial_block_seed_17 | 0.0482 | -0.0186 | +0.0221 |
| V6 full_total_h64_semi_mask0.10_spatial_block_seed_42 | 0.0578 | -0.0090 | +0.0317 |
| V6 full_total_h64_semi_mask0.15_random_seed_17 | 0.0411 | -0.0257 | +0.0150 |
| V6 full_total_h64_semi_mask0.15_random_seed_42 | 0.0353 | -0.0315 | +0.0092 |
| V6 full_total_h64_semi_mask0.20_block_seed_17 | 0.0318 | -0.0350 | +0.0057 |
| V6 full_total_h64_semi_mask0.20_block_seed_42 | 0.0327 | -0.0341 | +0.0066 |
| V6 full_total_h64_semi_mask0.20_random_seed_17 | 0.0340 | -0.0328 | +0.0079 |
| V6 full_total_h64_semi_mask0.20_random_seed_42 | 0.0334 | -0.0334 | +0.0073 |
| V6 full_total_h64_semi_mask0.20_spatial_block_seed_17 | 0.0467 | -0.0201 | +0.0206 |
| V6 full_total_h64_semi_mask0.20_spatial_block_seed_42 | 0.0667 | -0.0001 | +0.0406 |
| V6 full_total_h64_semi_mask0.30_random_seed_17 | 0.0352 | -0.0316 | +0.0091 |
| V6 full_total_h64_semi_mask0.30_random_seed_42 | 0.0346 | -0.0322 | +0.0085 |

## Per-year total WMAPE — full_total_h64_semi_mask0.10_random_warmup0_seed_42

| Year | WMAPE |
|---:|---:|
| 2021 | 0.034191 |
| 2022 | 0.018657 |
| 2023 | 0.026349 |
| 2024 | 0.027952 |
| 2025 | 0.019963 |

## Per-sector WMAPE — full_total_h64_semi_mask0.10_random_warmup0_seed_42
Mean across sectors: 0.24289

| Sector | WMAPE |
|---|---:|
| MN | 0.09886 |
| RU | 0.12034 |
| OQ | 0.13919 |
| FZ | 0.20137 |
| GI | 0.24871 |
| BE | 0.26795 |
| LZ | 0.26799 |
| KZ | 0.37855 |
| JZ | 0.46305 |

## Mean predicted sector proportions (last fold)

| Sector | Predicted proportion |
|---|---:|
| GI | 0.2779 |
| MN | 0.2031 |
| RU | 0.1173 |
| FZ | 0.0963 |
| BE | 0.0961 |
| OQ | 0.0933 |
| LZ | 0.0454 |
| JZ | 0.0386 |
| KZ | 0.0321 |

## Graph deltas — full_total_h64_semi_mask0.10_random_warmup0_seed_42

| Transition index | regime_delta | adj_delta |
|---:|---:|---:|
| 1 | 0.000000 | 0.012883 |
| 2 | 0.327871 | 0.018015 |
| 3 | 0.806026 | 0.029641 |
| 4 | 0.794263 | 0.026684 |
| 5 | 1.333529 | 0.036389 |
| 6 | 0.200852 | 0.032096 |
| 7 | 0.758150 | 0.039417 |
| 8 | 1.302211 | 0.056603 |
| 9 | 3.748621 | 0.231262 |
| 10 | 2.976783 | 0.207524 |
| 11 | 2.339062 | 0.108530 |
| 12 | 0.372314 | 0.028382 |
| 13 | 1.546832 | 0.138236 |
