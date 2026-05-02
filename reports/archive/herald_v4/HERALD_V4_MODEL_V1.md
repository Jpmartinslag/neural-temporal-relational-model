# HERALD V4 — Sectoral Dynamic Graph

## Architecture
- **Sectoral output**: predict creations per A10 sector (9) × zone
- **Sector-specific gates (N,9)**: each sector has its own self/neighbor balance
- **Regime shifts Q_t**: non-redundant — covid/rebound exclusive to regime_t
- **Concat node embedding**: no signal interference in e_t
- **Gate bias -1.0**: starts neighbor-favoring

## Results (total = sum of sectors)

| Run | Total WMAPE | vs Ridge AR | vs HERALD V3 |
|---|---:|---:|---:|
| Ridge AR | 0.0668 | — | — |
| HERALD V3 full (ref) | 0.0261 | -0.0407 | — |
| HERALD V4 fixed_geo_mob_only_seed_0 | 0.0514 | -0.0154 | +0.0253 |
| HERALD V4 fixed_geo_mob_only_seed_42 | 0.0532 | -0.0136 | +0.0271 |
| HERALD V4 fixed_geo_mob_only_seed_7 | 0.0525 | -0.0143 | +0.0264 |
| HERALD V4 full_h64_seed_0 | 0.0661 | -0.0007 | +0.0400 |
| HERALD V4 full_h64_seed_42 | 0.0624 | -0.0044 | +0.0363 |
| HERALD V4 full_h64_seed_7 | 0.0679 | +0.0011 | +0.0418 |
| HERALD V4 full_hidden16_seed_0 | 0.0611 | -0.0057 | +0.0350 |
| HERALD V4 full_hidden64_seed_0 | 0.0507 | -0.0161 | +0.0246 |
| HERALD V4 full_seed_0 | 0.0479 | -0.0189 | +0.0218 |
| HERALD V4 full_seed_42 | 0.0407 | -0.0261 | +0.0146 |
| HERALD V4 full_seed_7 | 0.0525 | -0.0143 | +0.0264 |
| HERALD V4 full_smooth001_seed_0 | 0.0582 | -0.0086 | +0.0321 |
| HERALD V4 full_smooth05_seed_0 | 0.0500 | -0.0168 | +0.0239 |
| HERALD V4 full_topk20_seed_0 | 0.0509 | -0.0159 | +0.0248 |
| HERALD V4 full_topk5_seed_0 | 0.0535 | -0.0133 | +0.0274 |
| HERALD V4 no_quarterly_seed_0 | 0.0622 | -0.0046 | +0.0361 |
| HERALD V4 no_quarterly_seed_42 | 0.0462 | -0.0206 | +0.0201 |
| HERALD V4 no_quarterly_seed_7 | 0.0697 | +0.0029 | +0.0436 |
| HERALD V4 no_regime_seed_0 | 0.0645 | -0.0023 | +0.0384 |
| HERALD V4 no_regime_seed_42 | 0.0501 | -0.0167 | +0.0240 |
| HERALD V4 no_regime_seed_7 | 0.0559 | -0.0109 | +0.0298 |
| HERALD V4 no_sector_gate_h64_seed_0 | 0.0730 | +0.0062 | +0.0469 |
| HERALD V4 no_sector_gate_h64_seed_42 | 0.0663 | -0.0005 | +0.0402 |
| HERALD V4 no_sector_gate_h64_seed_7 | 0.0652 | -0.0016 | +0.0391 |
| HERALD V4 no_sector_gate_seed_0 | 0.0473 | -0.0195 | +0.0212 |
| HERALD V4 no_sector_gate_seed_42 | 0.0475 | -0.0193 | +0.0214 |
| HERALD V4 no_sector_gate_seed_7 | 0.0489 | -0.0179 | +0.0228 |
| HERALD V4 no_smooth_seed_0 | 0.0552 | -0.0116 | +0.0291 |
| HERALD V4 no_smooth_seed_42 | 0.0559 | -0.0109 | +0.0298 |
| HERALD V4 no_smooth_seed_7 | 0.0580 | -0.0088 | +0.0319 |
| HERALD V4 self_only_h64_seed_0 | 0.0676 | +0.0008 | +0.0415 |
| HERALD V4 self_only_h64_seed_42 | 0.0653 | -0.0015 | +0.0392 |
| HERALD V4 self_only_h64_seed_7 | 0.0654 | -0.0014 | +0.0393 |
| HERALD V4 self_only_seed_0 | 0.0466 | -0.0202 | +0.0205 |
| HERALD V4 self_only_seed_42 | 0.0436 | -0.0232 | +0.0175 |
| HERALD V4 self_only_seed_7 | 0.0492 | -0.0176 | +0.0231 |
| HERALD V4 static_adaptive_seed_0 | 0.0623 | -0.0045 | +0.0362 |
| HERALD V4 static_adaptive_seed_42 | 0.0544 | -0.0124 | +0.0283 |
| HERALD V4 static_adaptive_seed_7 | 0.0685 | +0.0017 | +0.0424 |

## Per-sector WMAPE — full_hidden64_seed_0

| Sector | Mean WMAPE | Gate self-weight |
|---|---:|---:|
| OQ | 0.10210 | 0.8277 |
| FZ | 0.10673 | 0.8362 |
| BE | 0.11106 | 0.8963 |
| MN | 0.12366 | 0.9152 |
| JZ | 0.14095 | 0.9215 |
| RU | 0.16323 | 0.8829 |
| KZ | 0.18375 | 0.8523 |
| GI | 0.21975 | 0.8868 |
| LZ | 0.22305 | 0.9126 |

## Adjacency Dynamics (last fold)

| Year transition | Smooth ||A_t - A_{t-1}||² |
|---|---:|
| →2013 | 0.000152 |
| →2014 | 0.000157 |
| →2015 | 0.000268 |
| →2016 | 0.000329 |
| →2017 | 0.000448 |
| →2018 | 0.000583 |
| →2019 | 0.000601 |
| →2020 | 0.000657 ← COVID |
| →2021 | 0.000677 ← rebound |
| →2022 | 0.000857 |
| →2023 | 0.000650 |
| →2024 | 0.021991 |
