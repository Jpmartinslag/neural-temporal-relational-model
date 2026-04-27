# HERALD V3 — Dynamic Adaptive Graph

## Architecture
- **V3 key change**: A_t computed per timestep inside GRUCell loop
  (V2 computed adaptive_adj once before the loop — static).
- e_t = relu(annual_proj(x_ann) + q_proj(quarterly_enc(x_q)) + h_proj(h_{t-1}))
- A_t = topk_sparse_softmax(Q_t K_t^T / sqrt(d_k) + γ_geo·log(A_geo) + γ_mob·log(A_mob))
- Gate: g_t = sigmoid(MLP([e_t, m_t, regime_t])) where regime_t = [covid, rebound, growth]
- z_t = g_t * e_t + (1−g_t) * m_t  →  h_t = GRUCell(z_t, h_{t-1})
- Regularization: λ_smooth · mean(||A_t − A_{t-1}||_F²)
- Residual: final_pred = Ridge_AR_pred + neural_residual * zone_std

## Results

| Run | Mean WMAPE | vs Ridge AR | vs STGNN V1 | vs HERALD V2 exp |
|---|---:|---:|---:|---:|
| Ridge AR baseline | 0.0668 | — | — | — |
| Dynamic STGNN V1  | 0.0610 | -0.0058 | — | — |
| HERALD V2 expanding (ref) | 0.0271 | -0.0397 | -0.0339 | — |
| HERALD V3 dynamic_adaptive_no_quarterly_seed_0 | 0.0302 | -0.0366 | -0.0308 | +0.0031 |
| HERALD V3 dynamic_adaptive_no_quarterly_seed_42 | 0.0352 | -0.0316 | -0.0258 | +0.0081 |
| HERALD V3 dynamic_adaptive_no_quarterly_seed_7 | 0.0315 | -0.0353 | -0.0295 | +0.0044 |
| HERALD V3 dynamic_adaptive_no_regime_seed_0 | 0.0241 | -0.0427 | -0.0369 | -0.0030 |
| HERALD V3 dynamic_adaptive_no_regime_seed_42 | 0.0288 | -0.0380 | -0.0322 | +0.0017 |
| HERALD V3 dynamic_adaptive_no_regime_seed_7 | 0.0276 | -0.0392 | -0.0334 | +0.0005 |
| HERALD V3 dynamic_adaptive_no_smooth_seed_0 | 0.0258 | -0.0410 | -0.0352 | -0.0013 |
| HERALD V3 dynamic_adaptive_no_smooth_seed_42 | 0.0288 | -0.0380 | -0.0322 | +0.0017 |
| HERALD V3 dynamic_adaptive_no_smooth_seed_7 | 0.0314 | -0.0354 | -0.0296 | +0.0043 |
| HERALD V3 fixed_geo_mob_only_seed_0 | 0.0262 | -0.0406 | -0.0348 | -0.0009 |
| HERALD V3 fixed_geo_mob_only_seed_42 | 0.0295 | -0.0373 | -0.0315 | +0.0024 |
| HERALD V3 fixed_geo_mob_only_seed_7 | 0.0330 | -0.0338 | -0.0280 | +0.0059 |
| HERALD V3 full_seed_0 | 0.0246 | -0.0422 | -0.0364 | -0.0025 |
| HERALD V3 full_seed_42 | 0.0261 | -0.0407 | -0.0349 | -0.0010 |
| HERALD V3 full_seed_7 | 0.0276 | -0.0392 | -0.0334 | +0.0005 |
| HERALD V3 self_only_seed_0 | 0.0348 | -0.0320 | -0.0262 | +0.0077 |
| HERALD V3 self_only_seed_42 | 0.0276 | -0.0392 | -0.0334 | +0.0005 |
| HERALD V3 self_only_seed_7 | 0.0307 | -0.0361 | -0.0303 | +0.0036 |
| HERALD V3 static_adaptive_seed_0 | 0.0249 | -0.0419 | -0.0361 | -0.0022 |
| HERALD V3 static_adaptive_seed_42 | 0.0270 | -0.0398 | -0.0340 | -0.0001 |
| HERALD V3 static_adaptive_seed_7 | 0.0350 | -0.0318 | -0.0260 | +0.0079 |

## Per-year WMAPE — dynamic_adaptive_no_quarterly_seed_42

| Year | WMAPE | N |
|---:|---:|---:|
| 2021 | 0.031117 | 280 |
| 2022 | 0.023459 | 280 |
| 2023 | 0.044129 | 280 |
| 2024 | 0.041932 | 280 |

## Adjacency Diagnostics

| Fold | Smooth Mean | Density (last t) | γ_geo | γ_mob |
|---:|---:|---:|---:|---:|
| 2021 | 0.000676 | 0.0190 | 1.0058 | 1.1571 |
| 2022 | 0.000281 | 0.0354 | 0.1195 | 1.3149 |
| 2023 | 0.000300 | 0.0357 | 0.0726 | 1.1583 |
| 2024 | 0.000208 | 0.0356 | 0.2176 | 1.0469 |

## Gate Diagnostics (mean gate value by year, last fold)

| Year | Mean g_t |
|---:|---:|
| 2019 | 0.80209 |
| 2020 | 0.85204 |
| 2021 | 0.79276 |
| 2022 | 0.86993 |
| 2024 | 0.78338 |
