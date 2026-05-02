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
| dcrnn_residual | 0.053651 |
| dynamic_stgnn_residual | 0.053828 |
| graph_wavenet_residual | 0.101092 |

## Per-Year WMAPE

| model | target_year | wmape | n |
|---|---:|---:|---:|
| dcrnn_residual | 2021 | 0.061519 | 280 |
| dcrnn_residual | 2022 | 0.079060 | 280 |
| dcrnn_residual | 2023 | 0.072546 | 280 |
| dcrnn_residual | 2024 | 0.026383 | 280 |
| dcrnn_residual | 2025 | 0.028749 | 280 |
| dynamic_stgnn_residual | 2021 | 0.061158 | 280 |
| dynamic_stgnn_residual | 2022 | 0.079051 | 280 |
| dynamic_stgnn_residual | 2023 | 0.072642 | 280 |
| dynamic_stgnn_residual | 2024 | 0.026271 | 280 |
| dynamic_stgnn_residual | 2025 | 0.030019 | 280 |
| graph_wavenet_residual | 2021 | 0.220293 | 280 |
| graph_wavenet_residual | 2022 | 0.055154 | 280 |
| graph_wavenet_residual | 2023 | 0.133990 | 280 |
| graph_wavenet_residual | 2024 | 0.049958 | 280 |
| graph_wavenet_residual | 2025 | 0.046065 | 280 |
