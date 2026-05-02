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
| dynamic_stgnn_residual | 0.061205 |
| dcrnn_residual | 0.061478 |
| graph_wavenet_residual | 0.113949 |

## Per-Year WMAPE

| model | target_year | wmape | n |
|---|---:|---:|---:|
| dcrnn_residual | 2021 | 0.061853 | 280 |
| dcrnn_residual | 2022 | 0.079170 | 280 |
| dcrnn_residual | 2023 | 0.072668 | 280 |
| dcrnn_residual | 2024 | 0.032221 | 280 |
| dynamic_stgnn_residual | 2021 | 0.061098 | 280 |
| dynamic_stgnn_residual | 2022 | 0.078994 | 280 |
| dynamic_stgnn_residual | 2023 | 0.072570 | 280 |
| dynamic_stgnn_residual | 2024 | 0.032160 | 280 |
| graph_wavenet_residual | 2021 | 0.203145 | 280 |
| graph_wavenet_residual | 2022 | 0.030010 | 280 |
| graph_wavenet_residual | 2023 | 0.143650 | 280 |
| graph_wavenet_residual | 2024 | 0.078991 | 280 |
