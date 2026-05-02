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
| V6 contrast_loss_seed_0 | 0.0301 | -0.0367 | +0.0040 |
| V6 contrast_loss_seed_1 | 0.0287 | -0.0381 | +0.0026 |
| V6 contrast_loss_seed_123 | 0.0303 | -0.0365 | +0.0042 |
| V6 contrast_loss_seed_13 | 0.0306 | -0.0362 | +0.0045 |
| V6 contrast_loss_seed_42 | 0.0309 | -0.0359 | +0.0048 |
| V6 contrast_loss_seed_7 | 0.0262 | -0.0406 | +0.0001 |
| V6 contrast_loss_seed_99 | 0.0308 | -0.0360 | +0.0047 |
| V6 fixed_geo_mob_only_seed_0 | 0.0325 | -0.0343 | +0.0064 |
| V6 fixed_geo_mob_only_seed_1 | 0.0314 | -0.0354 | +0.0053 |
| V6 fixed_geo_mob_only_seed_123 | 0.0332 | -0.0336 | +0.0071 |
| V6 fixed_geo_mob_only_seed_13 | 0.0311 | -0.0357 | +0.0050 |
| V6 fixed_geo_mob_only_seed_42 | 0.0281 | -0.0387 | +0.0020 |
| V6 fixed_geo_mob_only_seed_7 | 0.0279 | -0.0389 | +0.0018 |
| V6 fixed_geo_mob_only_seed_99 | 0.0242 | -0.0426 | -0.0019 |
| V6 full_best_seed_0 | 0.0262 | -0.0406 | +0.0001 |
| V6 full_best_seed_1 | 0.0335 | -0.0333 | +0.0074 |
| V6 full_best_seed_123 | 0.0285 | -0.0383 | +0.0024 |
| V6 full_best_seed_13 | 0.0303 | -0.0365 | +0.0042 |
| V6 full_best_seed_17 | 0.0277 | -0.0391 | +0.0016 |
| V6 full_best_seed_3 | 0.0295 | -0.0373 | +0.0034 |
| V6 full_best_seed_42 | 0.0319 | -0.0349 | +0.0058 |
| V6 full_best_seed_7 | 0.0208 | -0.0460 | -0.0053 |
| V6 full_best_seed_77 | 0.0223 | -0.0445 | -0.0038 |
| V6 full_best_seed_99 | 0.0248 | -0.0420 | -0.0013 |
| V6 full_gate0.0_seed_0 | 0.0247 | -0.0421 | -0.0014 |
| V6 full_gate1.0_seed_0 | 0.0301 | -0.0367 | +0.0040 |
| V6 full_gate2.0_seed_0 | 0.0232 | -0.0436 | -0.0029 |
| V6 full_hidden32_seed_0 | 0.0301 | -0.0367 | +0.0040 |
| V6 full_hidden64_seed_0 | 0.0275 | -0.0393 | +0.0014 |
| V6 full_seed_0 | 0.0301 | -0.0367 | +0.0040 |
| V6 full_seed_1 | 0.0287 | -0.0381 | +0.0026 |
| V6 full_seed_123 | 0.0303 | -0.0365 | +0.0042 |
| V6 full_seed_13 | 0.0306 | -0.0362 | +0.0045 |
| V6 full_seed_42 | 0.0309 | -0.0359 | +0.0048 |
| V6 full_seed_7 | 0.0262 | -0.0406 | +0.0001 |
| V6 full_seed_99 | 0.0308 | -0.0360 | +0.0047 |
| V6 full_smooth0.005_contrast0.01_seed_0 | 0.0342 | -0.0326 | +0.0081 |
| V6 full_smooth0.005_contrast0.05_seed_0 | 0.0342 | -0.0326 | +0.0081 |
| V6 full_smooth0.005_contrast0.0_seed_0 | 0.0342 | -0.0326 | +0.0081 |
| V6 full_smooth0.01_contrast0.01_seed_0 | 0.0301 | -0.0367 | +0.0040 |
| V6 full_smooth0.01_contrast0.05_seed_0 | 0.0301 | -0.0367 | +0.0040 |
| V6 full_smooth0.01_contrast0.0_seed_0 | 0.0301 | -0.0367 | +0.0040 |
| V6 full_smooth0.05_contrast0.01_seed_0 | 0.0380 | -0.0288 | +0.0119 |
| V6 full_smooth0.05_contrast0.05_seed_0 | 0.0380 | -0.0288 | +0.0119 |
| V6 full_smooth0.05_contrast0.0_seed_0 | 0.0380 | -0.0288 | +0.0119 |
| V6 full_topk10_seed_0 | 0.0301 | -0.0367 | +0.0040 |
| V6 full_topk15_seed_0 | 0.0308 | -0.0360 | +0.0047 |
| V6 full_topk5_seed_0 | 0.0333 | -0.0335 | +0.0072 |
| V6 no_quarterly_seed_0 | 0.0282 | -0.0386 | +0.0021 |
| V6 no_quarterly_seed_1 | 0.0316 | -0.0352 | +0.0055 |
| V6 no_quarterly_seed_123 | 0.0280 | -0.0388 | +0.0019 |
| V6 no_quarterly_seed_13 | 0.0389 | -0.0279 | +0.0128 |
| V6 no_quarterly_seed_42 | 0.0214 | -0.0454 | -0.0047 |
| V6 no_quarterly_seed_7 | 0.0304 | -0.0364 | +0.0043 |
| V6 no_quarterly_seed_99 | 0.0301 | -0.0367 | +0.0040 |
| V6 no_regime_in_graph_seed_0 | 0.0297 | -0.0371 | +0.0036 |
| V6 no_regime_in_graph_seed_1 | 0.0278 | -0.0390 | +0.0017 |
| V6 no_regime_in_graph_seed_123 | 0.0294 | -0.0374 | +0.0033 |
| V6 no_regime_in_graph_seed_13 | 0.0351 | -0.0317 | +0.0090 |
| V6 no_regime_in_graph_seed_42 | 0.0331 | -0.0337 | +0.0070 |
| V6 no_regime_in_graph_seed_7 | 0.0293 | -0.0375 | +0.0032 |
| V6 no_regime_in_graph_seed_99 | 0.0293 | -0.0375 | +0.0032 |
| V6 no_sector_head_seed_0 | 0.0301 | -0.0367 | +0.0040 |
| V6 no_sector_head_seed_1 | 0.0287 | -0.0381 | +0.0026 |
| V6 no_sector_head_seed_123 | 0.0303 | -0.0365 | +0.0042 |
| V6 no_sector_head_seed_13 | 0.0306 | -0.0362 | +0.0045 |
| V6 no_sector_head_seed_42 | 0.0309 | -0.0359 | +0.0048 |
| V6 no_sector_head_seed_7 | 0.0262 | -0.0406 | +0.0001 |
| V6 no_sector_head_seed_99 | 0.0308 | -0.0360 | +0.0047 |
| V6 no_smooth_no_contrast_seed_0 | 0.0345 | -0.0323 | +0.0084 |
| V6 no_smooth_no_contrast_seed_1 | 0.0290 | -0.0378 | +0.0029 |
| V6 no_smooth_no_contrast_seed_123 | 0.0286 | -0.0382 | +0.0025 |
| V6 no_smooth_no_contrast_seed_13 | 0.0306 | -0.0362 | +0.0045 |
| V6 no_smooth_no_contrast_seed_42 | 0.0323 | -0.0345 | +0.0062 |
| V6 no_smooth_no_contrast_seed_7 | 0.0319 | -0.0349 | +0.0058 |
| V6 no_smooth_no_contrast_seed_99 | 0.0299 | -0.0369 | +0.0038 |
| V6 regime_exclusive_seed_0 | 0.0281 | -0.0387 | +0.0020 |
| V6 regime_exclusive_seed_1 | 0.0342 | -0.0326 | +0.0081 |
| V6 regime_exclusive_seed_123 | 0.0371 | -0.0297 | +0.0110 |
| V6 regime_exclusive_seed_13 | 0.0273 | -0.0395 | +0.0012 |
| V6 regime_exclusive_seed_42 | 0.0236 | -0.0432 | -0.0025 |
| V6 regime_exclusive_seed_7 | 0.0229 | -0.0439 | -0.0032 |
| V6 regime_exclusive_seed_99 | 0.0252 | -0.0416 | -0.0009 |
| V6 self_only_seed_0 | 0.0265 | -0.0403 | +0.0004 |
| V6 self_only_seed_1 | 0.0259 | -0.0409 | -0.0002 |
| V6 self_only_seed_123 | 0.0315 | -0.0353 | +0.0054 |
| V6 self_only_seed_13 | 0.0291 | -0.0377 | +0.0030 |
| V6 self_only_seed_42 | 0.0326 | -0.0342 | +0.0065 |
| V6 self_only_seed_7 | 0.0285 | -0.0383 | +0.0024 |
| V6 self_only_seed_99 | 0.0240 | -0.0428 | -0.0021 |
| V6 static_adaptive_seed_0 | 0.0327 | -0.0341 | +0.0066 |
| V6 static_adaptive_seed_1 | 0.0292 | -0.0376 | +0.0031 |
| V6 static_adaptive_seed_123 | 0.0383 | -0.0285 | +0.0122 |
| V6 static_adaptive_seed_13 | 0.0368 | -0.0300 | +0.0107 |
| V6 static_adaptive_seed_42 | 0.0280 | -0.0388 | +0.0019 |
| V6 static_adaptive_seed_7 | 0.0368 | -0.0300 | +0.0107 |
| V6 static_adaptive_seed_99 | 0.0597 | -0.0071 | +0.0336 |

## Per-year total WMAPE — full_best_seed_123

| Year | WMAPE |
|---:|---:|
| 2021 | 0.034978 |
| 2022 | 0.025886 |
| 2023 | 0.020670 |
| 2024 | 0.032627 |

## Per-sector WMAPE — full_best_seed_123
Mean across sectors: 0.21854

| Sector | WMAPE |
|---|---:|
| RU | 0.13451 |
| MN | 0.14344 |
| OQ | 0.16737 |
| GI | 0.18723 |
| FZ | 0.21354 |
| KZ | 0.24476 |
| LZ | 0.25579 |
| BE | 0.29761 |
| JZ | 0.32264 |

## Mean predicted sector proportions (last fold)

| Sector | Predicted proportion |
|---|---:|
| GI | 0.2966 |
| MN | 0.1854 |
| RU | 0.1166 |
| FZ | 0.0988 |
| OQ | 0.0944 |
| BE | 0.0879 |
| LZ | 0.0469 |
| JZ | 0.0372 |
| KZ | 0.0362 |

## Graph deltas — full_best_seed_123

| Transition index | regime_delta | adj_delta |
|---:|---:|---:|
| 1 | 0.000000 | 0.014204 |
| 2 | 0.326696 | 0.023268 |
| 3 | 0.803136 | 0.044011 |
| 4 | 0.791415 | 0.031870 |
| 5 | 1.328747 | 0.040251 |
| 6 | 0.200132 | 0.036685 |
| 7 | 0.755431 | 0.036152 |
| 8 | 1.301127 | 0.047950 |
| 9 | 3.742351 | 0.550733 |
| 10 | 2.969695 | 0.475411 |
| 11 | 2.330674 | 0.096631 |
| 12 | 0.370979 | 0.068800 |
