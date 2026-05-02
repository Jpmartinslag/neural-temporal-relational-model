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
| dcrnn_residual | 0.053664 |
| dynamic_stgnn_residual | 0.053970 |
| graph_wavenet_residual | 0.095282 |

## Per-Year WMAPE

| model | target_year | wmape | n |
|---|---:|---:|---:|
| dcrnn_residual | 2021 | 0.061466 | 280 |
| dcrnn_residual | 2022 | 0.079313 | 280 |
| dcrnn_residual | 2023 | 0.072599 | 280 |
| dcrnn_residual | 2024 | 0.026248 | 280 |
| dcrnn_residual | 2025 | 0.028695 | 280 |
| dynamic_stgnn_residual | 2021 | 0.061175 | 280 |
| dynamic_stgnn_residual | 2022 | 0.078996 | 280 |
| dynamic_stgnn_residual | 2023 | 0.072491 | 280 |
| dynamic_stgnn_residual | 2024 | 0.026124 | 280 |
| dynamic_stgnn_residual | 2025 | 0.031062 | 280 |
| graph_wavenet_residual | 2021 | 0.148996 | 280 |
| graph_wavenet_residual | 2022 | 0.061173 | 280 |
| graph_wavenet_residual | 2023 | 0.119155 | 280 |
| graph_wavenet_residual | 2024 | 0.091239 | 280 |
| graph_wavenet_residual | 2025 | 0.055845 | 280 |
