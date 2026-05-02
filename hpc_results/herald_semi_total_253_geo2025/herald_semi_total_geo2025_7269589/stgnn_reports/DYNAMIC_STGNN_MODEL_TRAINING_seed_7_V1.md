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
| dcrnn_residual | 0.053775 |
| dynamic_stgnn_residual | 0.054195 |
| graph_wavenet_residual | 0.170071 |

## Per-Year WMAPE

| model | target_year | wmape | n |
|---|---:|---:|---:|
| dcrnn_residual | 2021 | 0.061776 | 280 |
| dcrnn_residual | 2022 | 0.079593 | 280 |
| dcrnn_residual | 2023 | 0.072637 | 280 |
| dcrnn_residual | 2024 | 0.026121 | 280 |
| dcrnn_residual | 2025 | 0.028747 | 280 |
| dynamic_stgnn_residual | 2021 | 0.060988 | 280 |
| dynamic_stgnn_residual | 2022 | 0.078885 | 280 |
| dynamic_stgnn_residual | 2023 | 0.072488 | 280 |
| dynamic_stgnn_residual | 2024 | 0.026255 | 280 |
| dynamic_stgnn_residual | 2025 | 0.032356 | 280 |
| graph_wavenet_residual | 2021 | 0.176147 | 280 |
| graph_wavenet_residual | 2022 | 0.238234 | 280 |
| graph_wavenet_residual | 2023 | 0.085683 | 280 |
| graph_wavenet_residual | 2024 | 0.262666 | 280 |
| graph_wavenet_residual | 2025 | 0.087628 | 280 |
