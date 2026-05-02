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
| V6 full_total_h32_semi_mask0.10_random_seed_0 | 0.0340 | -0.0328 | +0.0079 |
| V6 full_total_h32_semi_mask0.10_random_seed_1 | 0.0403 | -0.0265 | +0.0142 |
| V6 full_total_h64_semi_mask0.05_random_seed_0 | 0.0286 | -0.0382 | +0.0025 |
| V6 full_total_h64_semi_mask0.05_random_seed_1 | 0.0366 | -0.0302 | +0.0105 |
| V6 full_total_h64_semi_mask0.0_control_seed_0 | 0.0267 | -0.0401 | +0.0006 |
| V6 full_total_h64_semi_mask0.0_control_seed_1 | 0.0312 | -0.0356 | +0.0051 |
| V6 full_total_h64_semi_mask0.10_block_seed_0 | 0.0258 | -0.0410 | -0.0003 |
| V6 full_total_h64_semi_mask0.10_block_seed_1 | 0.0409 | -0.0259 | +0.0148 |
| V6 full_total_h64_semi_mask0.10_random_lam0.01_total_seed_0 | 0.0265 | -0.0403 | +0.0004 |
| V6 full_total_h64_semi_mask0.10_random_lam0.01_total_seed_1 | 0.0424 | -0.0244 | +0.0163 |
| V6 full_total_h64_semi_mask0.10_random_lam0.05_a10_seed_0 | 0.0261 | -0.0407 | -0.0000 |
| V6 full_total_h64_semi_mask0.10_random_lam0.05_a10_seed_1 | 0.0415 | -0.0253 | +0.0154 |
| V6 full_total_h64_semi_mask0.10_random_lam0.05_total_a10_seed_0 | 0.0293 | -0.0375 | +0.0032 |
| V6 full_total_h64_semi_mask0.10_random_lam0.05_total_a10_seed_1 | 0.0442 | -0.0226 | +0.0181 |
| V6 full_total_h64_semi_mask0.10_random_lam0.05_total_seed_0 | 0.0293 | -0.0375 | +0.0032 |
| V6 full_total_h64_semi_mask0.10_random_lam0.05_total_seed_1 | 0.0442 | -0.0226 | +0.0181 |
| V6 full_total_h64_semi_mask0.10_random_lam0.10_total_seed_0 | 0.0300 | -0.0368 | +0.0039 |
| V6 full_total_h64_semi_mask0.10_random_lam0.10_total_seed_1 | 0.0427 | -0.0241 | +0.0166 |
| V6 full_total_h64_semi_mask0.10_random_seed_0 | 0.0261 | -0.0407 | -0.0000 |
| V6 full_total_h64_semi_mask0.10_random_seed_1 | 0.0415 | -0.0253 | +0.0154 |
| V6 full_total_h64_semi_mask0.10_random_warmup0_seed_0 | 0.0301 | -0.0367 | +0.0040 |
| V6 full_total_h64_semi_mask0.10_random_warmup0_seed_1 | 0.0342 | -0.0326 | +0.0081 |
| V6 full_total_h64_semi_mask0.10_spatial_block_seed_0 | 0.0345 | -0.0323 | +0.0084 |
| V6 full_total_h64_semi_mask0.10_spatial_block_seed_1 | 0.0471 | -0.0197 | +0.0210 |
| V6 full_total_h64_semi_mask0.15_random_seed_0 | 0.0269 | -0.0399 | +0.0008 |
| V6 full_total_h64_semi_mask0.15_random_seed_1 | 0.0436 | -0.0232 | +0.0175 |
| V6 full_total_h64_semi_mask0.20_block_seed_0 | 0.0276 | -0.0392 | +0.0015 |
| V6 full_total_h64_semi_mask0.20_block_seed_1 | 0.0357 | -0.0311 | +0.0096 |
| V6 full_total_h64_semi_mask0.20_random_seed_0 | 0.0272 | -0.0396 | +0.0011 |
| V6 full_total_h64_semi_mask0.20_random_seed_1 | 0.0361 | -0.0307 | +0.0100 |
| V6 full_total_h64_semi_mask0.20_spatial_block_seed_0 | 0.0357 | -0.0311 | +0.0096 |
| V6 full_total_h64_semi_mask0.20_spatial_block_seed_1 | 0.0574 | -0.0094 | +0.0313 |
| V6 full_total_h64_semi_mask0.30_random_seed_0 | 0.0321 | -0.0347 | +0.0060 |
| V6 full_total_h64_semi_mask0.30_random_seed_1 | 0.0378 | -0.0290 | +0.0117 |

## Per-year total WMAPE — full_total_h64_semi_mask0.10_random_warmup0_seed_1

| Year | WMAPE |
|---:|---:|
| 2021 | 0.038179 |
| 2022 | 0.018489 |
| 2023 | 0.021894 |
| 2024 | 0.036369 |
| 2025 | 0.055846 |

## Per-sector WMAPE — full_total_h64_semi_mask0.10_random_warmup0_seed_1
Mean across sectors: 0.23547

| Sector | WMAPE |
|---|---:|
| RU | 0.11380 |
| OQ | 0.11921 |
| MN | 0.12365 |
| FZ | 0.20355 |
| GI | 0.21222 |
| BE | 0.25946 |
| LZ | 0.28365 |
| KZ | 0.36604 |
| JZ | 0.43765 |

## Mean predicted sector proportions (last fold)

| Sector | Predicted proportion |
|---|---:|
| GI | 0.2801 |
| MN | 0.1937 |
| RU | 0.1197 |
| BE | 0.1014 |
| FZ | 0.0964 |
| OQ | 0.0938 |
| LZ | 0.0449 |
| JZ | 0.0383 |
| KZ | 0.0317 |

## Graph deltas — full_total_h64_semi_mask0.10_random_warmup0_seed_1

| Transition index | regime_delta | adj_delta |
|---:|---:|---:|
| 1 | 0.000000 | 0.010389 |
| 2 | 0.327871 | 0.012911 |
| 3 | 0.806026 | 0.027506 |
| 4 | 0.794263 | 0.022337 |
| 5 | 1.333529 | 0.051056 |
| 6 | 0.200852 | 0.025899 |
| 7 | 0.758150 | 0.035252 |
| 8 | 1.302211 | 0.057673 |
| 9 | 3.748621 | 0.703402 |
| 10 | 2.976783 | 0.614262 |
| 11 | 2.339062 | 0.169464 |
| 12 | 0.372314 | 0.029812 |
| 13 | 1.546832 | 0.122162 |
