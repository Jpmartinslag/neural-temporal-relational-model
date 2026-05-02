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
| dynamic_stgnn_residual | 0.061155 |
| dcrnn_residual | 0.061274 |
| graph_wavenet_residual | 0.122960 |

## Per-Year WMAPE

| model | target_year | wmape | n |
|---|---:|---:|---:|
| dcrnn_residual | 2021 | 0.061534 | 280 |
| dcrnn_residual | 2022 | 0.079060 | 280 |
| dcrnn_residual | 2023 | 0.072546 | 280 |
| dcrnn_residual | 2024 | 0.031957 | 280 |
| dynamic_stgnn_residual | 2021 | 0.061048 | 280 |
| dynamic_stgnn_residual | 2022 | 0.079191 | 280 |
| dynamic_stgnn_residual | 2023 | 0.072530 | 280 |
| dynamic_stgnn_residual | 2024 | 0.031852 | 280 |
| graph_wavenet_residual | 2021 | 0.280075 | 280 |
| graph_wavenet_residual | 2022 | 0.046768 | 280 |
| graph_wavenet_residual | 2023 | 0.106557 | 280 |
| graph_wavenet_residual | 2024 | 0.058439 | 280 |
