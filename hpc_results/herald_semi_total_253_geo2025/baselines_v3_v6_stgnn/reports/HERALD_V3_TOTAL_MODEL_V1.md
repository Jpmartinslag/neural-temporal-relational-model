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
| HERALD V3 full_total_geo2025_seed_0 | 0.0288 | -0.0380 | -0.0322 | +0.0017 |
| HERALD V3 full_total_geo2025_seed_1 | 0.0317 | -0.0351 | -0.0293 | +0.0046 |
| HERALD V3 full_total_geo2025_seed_123 | 0.0255 | -0.0413 | -0.0355 | -0.0016 |
| HERALD V3 full_total_geo2025_seed_13 | 0.0397 | -0.0271 | -0.0213 | +0.0126 |
| HERALD V3 full_total_geo2025_seed_17 | 0.0282 | -0.0386 | -0.0328 | +0.0011 |
| HERALD V3 full_total_geo2025_seed_2025 | 0.0312 | -0.0356 | -0.0298 | +0.0041 |
| HERALD V3 full_total_geo2025_seed_42 | 0.0374 | -0.0294 | -0.0236 | +0.0103 |
| HERALD V3 full_total_geo2025_seed_7 | 0.0493 | -0.0175 | -0.0117 | +0.0222 |
| HERALD V3 full_total_geo2025_seed_77 | 0.0316 | -0.0352 | -0.0294 | +0.0045 |
| HERALD V3 full_total_geo2025_seed_99 | 0.0327 | -0.0341 | -0.0283 | +0.0056 |

## Per-year WMAPE — full_total_geo2025_seed_2025

| Year | WMAPE | N |
|---:|---:|---:|
| 2021 | 0.038459 | 280 |
| 2022 | 0.024330 | 280 |
| 2023 | 0.023362 | 280 |
| 2024 | 0.024769 | 280 |
| 2025 | 0.044916 | 280 |

## Adjacency Diagnostics

| Fold | Smooth Mean | Density (last t) | γ_geo | γ_mob |
|---:|---:|---:|---:|---:|
| 2021 | 0.000438 | 0.0327 | 0.2778 | 1.1837 |
| 2022 | 0.000362 | 0.0357 | 0.1320 | 1.2009 |
| 2023 | 0.000338 | 0.0190 | 0.8504 | 1.0414 |
| 2024 | 0.000131 | 0.0357 | 0.1639 | 1.0171 |
| 2025 | 0.000388 | 0.0190 | 1.0059 | 1.0178 |

## Gate Diagnostics (mean gate value by year, last fold)

| Year | Mean g_t |
|---:|---:|
| 2019 | 0.78683 |
| 2020 | 0.77888 |
| 2021 | 0.86041 |
| 2022 | 0.73028 |
| 2024 | 0.78197 |
