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
| HERALD V3 full_final_geo2025_seed_0 | 0.0284 | -0.0384 | -0.0326 | +0.0013 |
| HERALD V3 full_final_geo2025_seed_1 | 0.0318 | -0.0350 | -0.0292 | +0.0047 |
| HERALD V3 full_final_geo2025_seed_123 | 0.0258 | -0.0410 | -0.0352 | -0.0013 |
| HERALD V3 full_final_geo2025_seed_13 | 0.0401 | -0.0267 | -0.0209 | +0.0130 |
| HERALD V3 full_final_geo2025_seed_42 | 0.0370 | -0.0298 | -0.0240 | +0.0099 |
| HERALD V3 full_final_geo2025_seed_7 | 0.0498 | -0.0170 | -0.0112 | +0.0227 |
| HERALD V3 full_final_geo2025_seed_99 | 0.0323 | -0.0345 | -0.0287 | +0.0052 |

## Per-year WMAPE — full_final_geo2025_seed_123

| Year | WMAPE | N |
|---:|---:|---:|
| 2021 | 0.036270 | 280 |
| 2022 | 0.024084 | 280 |
| 2023 | 0.023262 | 280 |
| 2024 | 0.025605 | 280 |
| 2025 | 0.019695 | 280 |

## Adjacency Diagnostics

| Fold | Smooth Mean | Density (last t) | γ_geo | γ_mob |
|---:|---:|---:|---:|---:|
| 2021 | 0.001054 | 0.0320 | 0.2906 | 1.1783 |
| 2022 | 0.000372 | 0.0353 | 0.2204 | 1.1087 |
| 2023 | 0.000384 | 0.0357 | 0.0060 | 1.1322 |
| 2024 | 0.000187 | 0.0357 | 0.0526 | 1.1416 |
| 2025 | 0.000320 | 0.0357 | 0.0502 | 1.1209 |

## Gate Diagnostics (mean gate value by year, last fold)

| Year | Mean g_t |
|---:|---:|
| 2019 | 0.95897 |
| 2020 | 0.95632 |
| 2021 | 0.96350 |
| 2022 | 0.92816 |
| 2024 | 0.91165 |
