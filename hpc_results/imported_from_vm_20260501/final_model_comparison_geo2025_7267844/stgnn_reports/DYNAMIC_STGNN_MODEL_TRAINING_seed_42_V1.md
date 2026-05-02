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
| dcrnn_residual | 0.053734 |
| dynamic_stgnn_residual | 0.053855 |
| graph_wavenet_residual | 0.075310 |

## Per-Year WMAPE

| model | target_year | wmape | n |
|---|---:|---:|---:|
| dcrnn_residual | 2021 | 0.061746 | 280 |
| dcrnn_residual | 2022 | 0.079121 | 280 |
| dcrnn_residual | 2023 | 0.072687 | 280 |
| dcrnn_residual | 2024 | 0.026251 | 280 |
| dcrnn_residual | 2025 | 0.028865 | 280 |
| dynamic_stgnn_residual | 2021 | 0.061251 | 280 |
| dynamic_stgnn_residual | 2022 | 0.079040 | 280 |
| dynamic_stgnn_residual | 2023 | 0.072518 | 280 |
| dynamic_stgnn_residual | 2024 | 0.026358 | 280 |
| dynamic_stgnn_residual | 2025 | 0.030111 | 280 |
| graph_wavenet_residual | 2021 | 0.127182 | 280 |
| graph_wavenet_residual | 2022 | 0.035210 | 280 |
| graph_wavenet_residual | 2023 | 0.067865 | 280 |
| graph_wavenet_residual | 2024 | 0.101834 | 280 |
| graph_wavenet_residual | 2025 | 0.044458 | 280 |
