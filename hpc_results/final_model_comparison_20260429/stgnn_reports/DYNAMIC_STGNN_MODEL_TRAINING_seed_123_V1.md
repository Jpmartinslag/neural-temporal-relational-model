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
| dynamic_stgnn_residual | 0.061303 |
| dcrnn_residual | 0.061401 |
| graph_wavenet_residual | 0.114339 |

## Per-Year WMAPE

| model | target_year | wmape | n |
|---|---:|---:|---:|
| dcrnn_residual | 2021 | 0.061805 | 280 |
| dcrnn_residual | 2022 | 0.079114 | 280 |
| dcrnn_residual | 2023 | 0.072563 | 280 |
| dcrnn_residual | 2024 | 0.032121 | 280 |
| dynamic_stgnn_residual | 2021 | 0.061042 | 280 |
| dynamic_stgnn_residual | 2022 | 0.079542 | 280 |
| dynamic_stgnn_residual | 2023 | 0.072515 | 280 |
| dynamic_stgnn_residual | 2024 | 0.032113 | 280 |
| graph_wavenet_residual | 2021 | 0.126180 | 280 |
| graph_wavenet_residual | 2022 | 0.025902 | 280 |
| graph_wavenet_residual | 2023 | 0.187516 | 280 |
| graph_wavenet_residual | 2024 | 0.117761 | 280 |
