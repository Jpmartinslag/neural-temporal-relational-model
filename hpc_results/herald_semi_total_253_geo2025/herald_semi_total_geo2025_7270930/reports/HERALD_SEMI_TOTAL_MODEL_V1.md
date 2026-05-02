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
| V6 full_total_h32_semi_mask0.10_random_seed_13 | 0.0348 | -0.0320 | +0.0087 |
| V6 full_total_h32_semi_mask0.10_random_seed_7 | 0.0263 | -0.0405 | +0.0002 |
| V6 full_total_h64_semi_mask0.05_random_seed_13 | 0.0245 | -0.0423 | -0.0016 |
| V6 full_total_h64_semi_mask0.05_random_seed_7 | 0.0324 | -0.0344 | +0.0063 |
| V6 full_total_h64_semi_mask0.0_control_seed_13 | 0.0272 | -0.0396 | +0.0011 |
| V6 full_total_h64_semi_mask0.0_control_seed_7 | 0.0262 | -0.0406 | +0.0001 |
| V6 full_total_h64_semi_mask0.10_block_seed_13 | 0.0370 | -0.0298 | +0.0109 |
| V6 full_total_h64_semi_mask0.10_block_seed_7 | 0.0257 | -0.0411 | -0.0004 |
| V6 full_total_h64_semi_mask0.10_random_lam0.01_total_seed_13 | 0.0254 | -0.0414 | -0.0007 |
| V6 full_total_h64_semi_mask0.10_random_lam0.01_total_seed_7 | 0.0310 | -0.0358 | +0.0049 |
| V6 full_total_h64_semi_mask0.10_random_lam0.05_a10_seed_13 | 0.0262 | -0.0406 | +0.0001 |
| V6 full_total_h64_semi_mask0.10_random_lam0.05_a10_seed_7 | 0.0324 | -0.0344 | +0.0063 |
| V6 full_total_h64_semi_mask0.10_random_lam0.05_total_a10_seed_13 | 0.0253 | -0.0415 | -0.0008 |
| V6 full_total_h64_semi_mask0.10_random_lam0.05_total_a10_seed_7 | 0.0312 | -0.0356 | +0.0051 |
| V6 full_total_h64_semi_mask0.10_random_lam0.05_total_seed_13 | 0.0253 | -0.0415 | -0.0008 |
| V6 full_total_h64_semi_mask0.10_random_lam0.05_total_seed_7 | 0.0312 | -0.0356 | +0.0051 |
| V6 full_total_h64_semi_mask0.10_random_lam0.10_total_seed_13 | 0.0243 | -0.0425 | -0.0018 |
| V6 full_total_h64_semi_mask0.10_random_lam0.10_total_seed_7 | 0.0299 | -0.0369 | +0.0038 |
| V6 full_total_h64_semi_mask0.10_random_seed_13 | 0.0262 | -0.0406 | +0.0001 |
| V6 full_total_h64_semi_mask0.10_random_seed_7 | 0.0324 | -0.0344 | +0.0063 |
| V6 full_total_h64_semi_mask0.10_random_warmup0_seed_13 | 0.0296 | -0.0372 | +0.0035 |
| V6 full_total_h64_semi_mask0.10_random_warmup0_seed_7 | 0.0316 | -0.0352 | +0.0055 |
| V6 full_total_h64_semi_mask0.10_spatial_block_seed_13 | 0.0357 | -0.0311 | +0.0096 |
| V6 full_total_h64_semi_mask0.10_spatial_block_seed_7 | 0.0603 | -0.0065 | +0.0342 |
| V6 full_total_h64_semi_mask0.15_random_seed_13 | 0.0244 | -0.0424 | -0.0017 |
| V6 full_total_h64_semi_mask0.15_random_seed_7 | 0.0294 | -0.0374 | +0.0033 |
| V6 full_total_h64_semi_mask0.20_block_seed_13 | 0.0324 | -0.0344 | +0.0063 |
| V6 full_total_h64_semi_mask0.20_block_seed_7 | 0.0250 | -0.0418 | -0.0011 |
| V6 full_total_h64_semi_mask0.20_random_seed_13 | 0.0258 | -0.0410 | -0.0003 |
| V6 full_total_h64_semi_mask0.20_random_seed_7 | 0.0298 | -0.0370 | +0.0037 |
| V6 full_total_h64_semi_mask0.20_spatial_block_seed_13 | 0.0278 | -0.0390 | +0.0017 |
| V6 full_total_h64_semi_mask0.20_spatial_block_seed_7 | 0.0529 | -0.0139 | +0.0268 |
| V6 full_total_h64_semi_mask0.30_random_seed_13 | 0.0236 | -0.0432 | -0.0025 |
| V6 full_total_h64_semi_mask0.30_random_seed_7 | 0.0306 | -0.0362 | +0.0045 |

## Per-year total WMAPE — full_total_h64_semi_mask0.10_random_warmup0_seed_13

| Year | WMAPE |
|---:|---:|
| 2021 | 0.032246 |
| 2022 | 0.024404 |
| 2023 | 0.025985 |
| 2024 | 0.026807 |
| 2025 | 0.038471 |

## Per-sector WMAPE — full_total_h64_semi_mask0.10_random_warmup0_seed_13
Mean across sectors: 0.23646

| Sector | WMAPE |
|---|---:|
| RU | 0.11485 |
| MN | 0.11542 |
| OQ | 0.13568 |
| GI | 0.22201 |
| FZ | 0.23511 |
| LZ | 0.24691 |
| BE | 0.28308 |
| KZ | 0.35020 |
| JZ | 0.42485 |

## Mean predicted sector proportions (last fold)

| Sector | Predicted proportion |
|---|---:|
| GI | 0.2826 |
| MN | 0.1905 |
| RU | 0.1194 |
| BE | 0.1005 |
| FZ | 0.0986 |
| OQ | 0.0925 |
| LZ | 0.0461 |
| JZ | 0.0374 |
| KZ | 0.0323 |

## Graph deltas — full_total_h64_semi_mask0.10_random_warmup0_seed_13

| Transition index | regime_delta | adj_delta |
|---:|---:|---:|
| 1 | 0.000000 | 0.011503 |
| 2 | 0.327871 | 0.018059 |
| 3 | 0.806026 | 0.029719 |
| 4 | 0.794263 | 0.024444 |
| 5 | 1.333529 | 0.031782 |
| 6 | 0.200852 | 0.026567 |
| 7 | 0.758150 | 0.036981 |
| 8 | 1.302211 | 0.056567 |
| 9 | 3.748621 | 0.451918 |
| 10 | 2.976783 | 0.454919 |
| 11 | 2.339062 | 0.179244 |
| 12 | 0.372314 | 0.031554 |
| 13 | 1.546832 | 0.106733 |
