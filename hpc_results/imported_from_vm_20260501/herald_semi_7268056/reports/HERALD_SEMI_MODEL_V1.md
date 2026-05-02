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
| V6 full_semi_mask0.05_seed_0 | 0.0422 | -0.0246 | +0.0161 |
| V6 full_semi_mask0.05_seed_13 | 0.0323 | -0.0345 | +0.0062 |
| V6 full_semi_mask0.05_seed_42 | 0.0481 | -0.0187 | +0.0220 |
| V6 full_semi_mask0.05_seed_7 | 0.0308 | -0.0360 | +0.0047 |
| V6 full_semi_mask0.05_seed_99 | 0.0377 | -0.0291 | +0.0116 |
| V6 full_semi_mask0.0_seed_0 | 0.0280 | -0.0388 | +0.0019 |
| V6 full_semi_mask0.0_seed_1 | 0.0323 | -0.0345 | +0.0062 |
| V6 full_semi_mask0.0_seed_11 | 0.0432 | -0.0236 | +0.0171 |
| V6 full_semi_mask0.0_seed_123 | 0.0319 | -0.0349 | +0.0058 |
| V6 full_semi_mask0.0_seed_13 | 0.0307 | -0.0361 | +0.0046 |
| V6 full_semi_mask0.0_seed_17 | 0.0325 | -0.0343 | +0.0064 |
| V6 full_semi_mask0.0_seed_19 | 0.0424 | -0.0244 | +0.0163 |
| V6 full_semi_mask0.0_seed_2 | 0.0375 | -0.0293 | +0.0114 |
| V6 full_semi_mask0.0_seed_23 | 0.0261 | -0.0407 | -0.0000 |
| V6 full_semi_mask0.0_seed_3 | 0.0315 | -0.0353 | +0.0054 |
| V6 full_semi_mask0.0_seed_42 | 0.0484 | -0.0184 | +0.0223 |
| V6 full_semi_mask0.0_seed_5 | 0.0423 | -0.0245 | +0.0162 |
| V6 full_semi_mask0.0_seed_7 | 0.0265 | -0.0403 | +0.0004 |
| V6 full_semi_mask0.0_seed_77 | 0.0351 | -0.0317 | +0.0090 |
| V6 full_semi_mask0.0_seed_99 | 0.0225 | -0.0443 | -0.0036 |
| V6 full_semi_mask0.10_block_seed_0 | 0.0279 | -0.0389 | +0.0018 |
| V6 full_semi_mask0.10_block_seed_13 | 0.0534 | -0.0134 | +0.0273 |
| V6 full_semi_mask0.10_block_seed_42 | 0.0418 | -0.0250 | +0.0157 |
| V6 full_semi_mask0.10_block_seed_7 | 0.0328 | -0.0340 | +0.0067 |
| V6 full_semi_mask0.10_block_seed_99 | 0.0324 | -0.0344 | +0.0063 |
| V6 full_semi_mask0.10_h64_seed_0 | 0.0281 | -0.0387 | +0.0020 |
| V6 full_semi_mask0.10_h64_seed_13 | 0.0196 | -0.0472 | -0.0065 |
| V6 full_semi_mask0.10_h64_seed_42 | 0.0353 | -0.0315 | +0.0092 |
| V6 full_semi_mask0.10_h64_seed_7 | 0.0306 | -0.0362 | +0.0045 |
| V6 full_semi_mask0.10_h64_seed_99 | 0.0378 | -0.0290 | +0.0117 |
| V6 full_semi_mask0.10_seed_0 | 0.0331 | -0.0337 | +0.0070 |
| V6 full_semi_mask0.10_seed_1 | 0.0302 | -0.0366 | +0.0041 |
| V6 full_semi_mask0.10_seed_11 | 0.0340 | -0.0328 | +0.0079 |
| V6 full_semi_mask0.10_seed_123 | 0.0417 | -0.0251 | +0.0156 |
| V6 full_semi_mask0.10_seed_13 | 0.0350 | -0.0318 | +0.0089 |
| V6 full_semi_mask0.10_seed_17 | 0.0314 | -0.0354 | +0.0053 |
| V6 full_semi_mask0.10_seed_19 | 0.0371 | -0.0297 | +0.0110 |
| V6 full_semi_mask0.10_seed_2 | 0.0494 | -0.0174 | +0.0233 |
| V6 full_semi_mask0.10_seed_23 | 0.0459 | -0.0209 | +0.0198 |
| V6 full_semi_mask0.10_seed_3 | 0.0434 | -0.0234 | +0.0173 |
| V6 full_semi_mask0.10_seed_42 | 0.0426 | -0.0242 | +0.0165 |
| V6 full_semi_mask0.10_seed_5 | 0.0426 | -0.0242 | +0.0165 |
| V6 full_semi_mask0.10_seed_7 | 0.0299 | -0.0369 | +0.0038 |
| V6 full_semi_mask0.10_seed_77 | 0.0375 | -0.0293 | +0.0114 |
| V6 full_semi_mask0.10_seed_99 | 0.0360 | -0.0308 | +0.0099 |
| V6 full_semi_mask0.15_seed_0 | 0.0367 | -0.0301 | +0.0106 |
| V6 full_semi_mask0.15_seed_13 | 0.0341 | -0.0327 | +0.0080 |
| V6 full_semi_mask0.15_seed_42 | 0.0418 | -0.0250 | +0.0157 |
| V6 full_semi_mask0.15_seed_7 | 0.0253 | -0.0415 | -0.0008 |
| V6 full_semi_mask0.15_seed_99 | 0.0382 | -0.0286 | +0.0121 |
| V6 full_semi_mask0.20_seed_0 | 0.0338 | -0.0330 | +0.0077 |
| V6 full_semi_mask0.20_seed_13 | 0.0406 | -0.0262 | +0.0145 |
| V6 full_semi_mask0.20_seed_42 | 0.0370 | -0.0298 | +0.0109 |
| V6 full_semi_mask0.20_seed_7 | 0.0249 | -0.0420 | -0.0013 |
| V6 full_semi_mask0.20_seed_99 | 0.0373 | -0.0295 | +0.0112 |
| V6 full_semi_mask0.30_seed_0 | 0.0354 | -0.0314 | +0.0093 |
| V6 full_semi_mask0.30_seed_13 | 0.0393 | -0.0275 | +0.0132 |
| V6 full_semi_mask0.30_seed_42 | 0.0315 | -0.0353 | +0.0054 |
| V6 full_semi_mask0.30_seed_7 | 0.0308 | -0.0360 | +0.0047 |
| V6 full_semi_mask0.30_seed_99 | 0.0345 | -0.0323 | +0.0084 |

## Per-year total WMAPE — full_semi_mask0.10_h64_seed_99

| Year | WMAPE |
|---:|---:|
| 2021 | 0.032529 |
| 2022 | 0.027711 |
| 2023 | 0.032273 |
| 2024 | 0.036553 |
| 2025 | 0.060173 |

## Per-sector WMAPE — full_semi_mask0.10_h64_seed_99
Mean across sectors: 0.20099

| Sector | WMAPE |
|---|---:|
| RU | 0.10875 |
| OQ | 0.10888 |
| MN | 0.10903 |
| GI | 0.17490 |
| FZ | 0.19371 |
| LZ | 0.23498 |
| BE | 0.25664 |
| KZ | 0.27496 |
| JZ | 0.34706 |

## Mean predicted sector proportions (last fold)

| Sector | Predicted proportion |
|---|---:|
| GI | 0.2705 |
| MN | 0.2091 |
| RU | 0.1222 |
| BE | 0.1149 |
| OQ | 0.0919 |
| FZ | 0.0895 |
| LZ | 0.0394 |
| JZ | 0.0349 |
| KZ | 0.0277 |

## Graph deltas — full_semi_mask0.10_h64_seed_99

| Transition index | regime_delta | adj_delta |
|---:|---:|---:|
| 1 | 0.000000 | 0.008425 |
| 2 | 0.327871 | 0.017824 |
| 3 | 0.806026 | 0.028233 |
| 4 | 0.794263 | 0.025012 |
| 5 | 1.333529 | 0.040016 |
| 6 | 0.200852 | 0.018658 |
| 7 | 0.758150 | 0.026917 |
| 8 | 1.302211 | 0.046021 |
| 9 | 3.748621 | 0.319746 |
| 10 | 2.976783 | 0.270716 |
| 11 | 2.339062 | 0.140798 |
| 12 | 0.372314 | 0.023325 |
| 13 | 1.546832 | 0.040834 |
