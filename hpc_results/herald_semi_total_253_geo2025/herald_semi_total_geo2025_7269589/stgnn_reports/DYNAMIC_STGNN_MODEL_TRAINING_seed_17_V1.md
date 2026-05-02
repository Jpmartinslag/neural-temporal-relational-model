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
| dcrnn_residual | 0.053747 |
| dynamic_stgnn_residual | 0.054235 |
| graph_wavenet_residual | 0.162478 |

## Per-Year WMAPE

| model | target_year | wmape | n |
|---|---:|---:|---:|
| dcrnn_residual | 2021 | 0.061953 | 280 |
| dcrnn_residual | 2022 | 0.079155 | 280 |
| dcrnn_residual | 2023 | 0.072485 | 280 |
| dcrnn_residual | 2024 | 0.026327 | 280 |
| dcrnn_residual | 2025 | 0.028814 | 280 |
| dynamic_stgnn_residual | 2021 | 0.061020 | 280 |
| dynamic_stgnn_residual | 2022 | 0.078946 | 280 |
| dynamic_stgnn_residual | 2023 | 0.072429 | 280 |
| dynamic_stgnn_residual | 2024 | 0.026138 | 280 |
| dynamic_stgnn_residual | 2025 | 0.032643 | 280 |
| graph_wavenet_residual | 2021 | 0.204781 | 280 |
| graph_wavenet_residual | 2022 | 0.075322 | 280 |
| graph_wavenet_residual | 2023 | 0.197334 | 280 |
| graph_wavenet_residual | 2024 | 0.276177 | 280 |
| graph_wavenet_residual | 2025 | 0.058778 | 280 |
