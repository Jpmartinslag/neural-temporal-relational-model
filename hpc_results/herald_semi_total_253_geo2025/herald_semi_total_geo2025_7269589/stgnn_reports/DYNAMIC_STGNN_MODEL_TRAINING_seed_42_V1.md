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
| dcrnn_residual | 0.053735 |
| dynamic_stgnn_residual | 0.053856 |
| graph_wavenet_residual | 0.086549 |

## Per-Year WMAPE

| model | target_year | wmape | n |
|---|---:|---:|---:|
| dcrnn_residual | 2021 | 0.061748 | 280 |
| dcrnn_residual | 2022 | 0.079123 | 280 |
| dcrnn_residual | 2023 | 0.072687 | 280 |
| dcrnn_residual | 2024 | 0.026252 | 280 |
| dcrnn_residual | 2025 | 0.028866 | 280 |
| dynamic_stgnn_residual | 2021 | 0.061251 | 280 |
| dynamic_stgnn_residual | 2022 | 0.079040 | 280 |
| dynamic_stgnn_residual | 2023 | 0.072518 | 280 |
| dynamic_stgnn_residual | 2024 | 0.026354 | 280 |
| dynamic_stgnn_residual | 2025 | 0.030117 | 280 |
| graph_wavenet_residual | 2021 | 0.140637 | 280 |
| graph_wavenet_residual | 2022 | 0.036124 | 280 |
| graph_wavenet_residual | 2023 | 0.069116 | 280 |
| graph_wavenet_residual | 2024 | 0.143256 | 280 |
| graph_wavenet_residual | 2025 | 0.043610 | 280 |
