# HERALD V5 — V3 backbone + A10 sector head

## Architecture
- V3 backbone: dynamic A_t, GRUCell, QuarterlyGRU, regime — unchanged
- Sector head: softmax(Linear(h_t, 9)) → real A10 proportions
- KL loss on real SIDE A10 sector proportions (replaces FLORES proxy)
- Final sector: final_total × sector_proportions[:, s]

| Run | Total WMAPE | vs Ridge AR | vs HERALD V3 |
|---|---:|---:|---:|
| Ridge AR | 0.0668 | — | — |
| HERALD V3 full (ref) | 0.0261 | -0.0407 | — |
| V5 fixed_geo_mob_only_seed_0 | 0.0310 | -0.0358 | +0.0049 |
| V5 fixed_geo_mob_only_seed_42 | 0.0273 | -0.0395 | +0.0012 |
| V5 fixed_geo_mob_only_seed_7 | 0.0307 | -0.0361 | +0.0046 |
| V5 full_seed_0 | 0.0282 | -0.0386 | +0.0021 |
| V5 full_seed_42 | 0.0350 | -0.0318 | +0.0089 |
| V5 full_seed_7 | 0.0283 | -0.0385 | +0.0022 |
| V5 no_quarterly_seed_0 | 0.0309 | -0.0359 | +0.0048 |
| V5 no_quarterly_seed_42 | 0.0321 | -0.0347 | +0.0060 |
| V5 no_quarterly_seed_7 | 0.0301 | -0.0367 | +0.0040 |
| V5 no_regime_seed_0 | 0.0280 | -0.0388 | +0.0019 |
| V5 no_regime_seed_42 | 0.0330 | -0.0338 | +0.0069 |
| V5 no_regime_seed_7 | 0.0286 | -0.0382 | +0.0025 |
| V5 no_sector_head_seed_0 | 0.0347 | -0.0321 | +0.0086 |
| V5 no_sector_head_seed_42 | 0.0406 | -0.0262 | +0.0145 |
| V5 no_sector_head_seed_7 | 0.0294 | -0.0374 | +0.0033 |
| V5 no_smooth_seed_0 | 0.0317 | -0.0351 | +0.0056 |
| V5 no_smooth_seed_42 | 0.0355 | -0.0313 | +0.0094 |
| V5 no_smooth_seed_7 | 0.0392 | -0.0276 | +0.0131 |
| V5 self_only_seed_0 | 0.0312 | -0.0356 | +0.0051 |
| V5 self_only_seed_42 | 0.0381 | -0.0287 | +0.0120 |
| V5 self_only_seed_7 | 0.0336 | -0.0332 | +0.0075 |
| V5 static_adaptive_seed_0 | 0.0320 | -0.0348 | +0.0059 |
| V5 static_adaptive_seed_42 | 0.0243 | -0.0425 | -0.0018 |
| V5 static_adaptive_seed_7 | 0.0377 | -0.0291 | +0.0116 |

## Per-year total WMAPE — full_seed_0

| Year | WMAPE |
|---:|---:|
| 2021 | 0.022720 |
| 2022 | 0.023518 |
| 2023 | 0.031542 |
| 2024 | 0.035081 |

## Per-sector WMAPE — full_seed_0
Mean across sectors: 0.17762

| Sector | WMAPE |
|---|---:|
| MN | 0.09921 |
| RU | 0.10602 |
| OQ | 0.13238 |
| GI | 0.17034 |
| FZ | 0.18188 |
| JZ | 0.19321 |
| KZ | 0.21503 |
| LZ | 0.23004 |
| BE | 0.27051 |

## Mean predicted sector proportions (last fold)

| Sector | Predicted proportion |
|---|---:|
| GI | 0.2910 |
| MN | 0.2031 |
| RU | 0.1150 |
| OQ | 0.0944 |
| FZ | 0.0940 |
| BE | 0.0906 |
| LZ | 0.0418 |
| JZ | 0.0386 |
| KZ | 0.0315 |
