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
| dynamic_stgnn_residual | 0.053603 |
| dcrnn_residual | 0.053698 |
| graph_wavenet_residual | 0.104740 |

## Per-Year WMAPE

| model | target_year | wmape | n |
|---|---:|---:|---:|
| dcrnn_residual | 2021 | 0.061873 | 280 |
| dcrnn_residual | 2022 | 0.079173 | 280 |
| dcrnn_residual | 2023 | 0.072542 | 280 |
| dcrnn_residual | 2024 | 0.026384 | 280 |
| dcrnn_residual | 2025 | 0.028518 | 280 |
| dynamic_stgnn_residual | 2021 | 0.061148 | 280 |
| dynamic_stgnn_residual | 2022 | 0.078955 | 280 |
| dynamic_stgnn_residual | 2023 | 0.072541 | 280 |
| dynamic_stgnn_residual | 2024 | 0.026544 | 280 |
| dynamic_stgnn_residual | 2025 | 0.028827 | 280 |
| graph_wavenet_residual | 2021 | 0.147012 | 280 |
| graph_wavenet_residual | 2022 | 0.060716 | 280 |
| graph_wavenet_residual | 2023 | 0.120390 | 280 |
| graph_wavenet_residual | 2024 | 0.093488 | 280 |
| graph_wavenet_residual | 2025 | 0.102096 | 280 |
