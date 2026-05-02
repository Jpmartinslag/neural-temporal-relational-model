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
| dynamic_stgnn_residual | 0.053653 |
| dcrnn_residual | 0.053800 |
| graph_wavenet_residual | 0.114895 |

## Per-Year WMAPE

| model | target_year | wmape | n |
|---|---:|---:|---:|
| dcrnn_residual | 2021 | 0.061862 | 280 |
| dcrnn_residual | 2022 | 0.079170 | 280 |
| dcrnn_residual | 2023 | 0.072668 | 280 |
| dcrnn_residual | 2024 | 0.026455 | 280 |
| dcrnn_residual | 2025 | 0.028846 | 280 |
| dynamic_stgnn_residual | 2021 | 0.061285 | 280 |
| dynamic_stgnn_residual | 2022 | 0.079169 | 280 |
| dynamic_stgnn_residual | 2023 | 0.072494 | 280 |
| dynamic_stgnn_residual | 2024 | 0.026317 | 280 |
| dynamic_stgnn_residual | 2025 | 0.028999 | 280 |
| graph_wavenet_residual | 2021 | 0.192620 | 280 |
| graph_wavenet_residual | 2022 | 0.037804 | 280 |
| graph_wavenet_residual | 2023 | 0.192077 | 280 |
| graph_wavenet_residual | 2024 | 0.064897 | 280 |
| graph_wavenet_residual | 2025 | 0.087078 | 280 |
