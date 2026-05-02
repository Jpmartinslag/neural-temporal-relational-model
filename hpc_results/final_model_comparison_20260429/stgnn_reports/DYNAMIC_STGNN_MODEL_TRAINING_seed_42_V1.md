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
| dynamic_stgnn_residual | 0.060929 |
| dcrnn_residual | 0.061356 |
| graph_wavenet_residual | 0.132290 |

## Per-Year WMAPE

| model | target_year | wmape | n |
|---|---:|---:|---:|
| dcrnn_residual | 2021 | 0.061740 | 280 |
| dcrnn_residual | 2022 | 0.079121 | 280 |
| dcrnn_residual | 2023 | 0.072687 | 280 |
| dcrnn_residual | 2024 | 0.031875 | 280 |
| dynamic_stgnn_residual | 2021 | 0.061137 | 280 |
| dynamic_stgnn_residual | 2022 | 0.079081 | 280 |
| dynamic_stgnn_residual | 2023 | 0.072436 | 280 |
| dynamic_stgnn_residual | 2024 | 0.031062 | 280 |
| graph_wavenet_residual | 2021 | 0.156096 | 280 |
| graph_wavenet_residual | 2022 | 0.092810 | 280 |
| graph_wavenet_residual | 2023 | 0.115973 | 280 |
| graph_wavenet_residual | 2024 | 0.164280 | 280 |
