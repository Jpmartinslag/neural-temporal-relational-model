# Dynamic STGNN Model Training — V1

## Methodological Notes

- All neural models predict residuals over `Ridge_AR`.
- Training residuals use leave-one-year-out Ridge predictions inside the training window.
- Default Huber delta is 500 to match the observed residual scale.
- `graph_wavenet_residual` uses only learned adaptive adjacency by design.
- `dynamic_stgnn_residual` mixes self, geo, mobility, and adaptive graphs with a year-context global gate.
- The V1 gate is dynamic over time but not zone-specific; this is an intentional simplification.

## Mean WMAPE

| model | mean_wmape |
|---|---|
| dcrnn_residual | 0.053723 |
| dynamic_stgnn_residual | 0.053729 |
| graph_wavenet_residual | 0.128819 |

## Per-Year WMAPE

| model | target_year | wmape | n |
|---|---:|---:|---:|
| dcrnn_residual | 2021 | 0.061962 | 280 |
| dcrnn_residual | 2022 | 0.079075 | 280 |
| dcrnn_residual | 2023 | 0.072525 | 280 |
| dcrnn_residual | 2024 | 0.026448 | 280 |
| dcrnn_residual | 2025 | 0.028603 | 280 |
| dynamic_stgnn_residual | 2021 | 0.061300 | 280 |
| dynamic_stgnn_residual | 2022 | 0.079078 | 280 |
| dynamic_stgnn_residual | 2023 | 0.072540 | 280 |
| dynamic_stgnn_residual | 2024 | 0.026341 | 280 |
| dynamic_stgnn_residual | 2025 | 0.029386 | 280 |
| graph_wavenet_residual | 2021 | 0.162298 | 280 |
| graph_wavenet_residual | 2022 | 0.244606 | 280 |
| graph_wavenet_residual | 2023 | 0.102131 | 280 |
| graph_wavenet_residual | 2024 | 0.098189 | 280 |
| graph_wavenet_residual | 2025 | 0.036872 | 280 |
