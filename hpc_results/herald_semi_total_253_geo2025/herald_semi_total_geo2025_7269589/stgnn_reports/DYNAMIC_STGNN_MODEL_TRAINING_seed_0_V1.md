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
| dynamic_stgnn_residual | 0.053665 |
| dcrnn_residual | 0.053729 |
| graph_wavenet_residual | 0.081684 |

## Per-Year WMAPE

| model | target_year | wmape | n |
|---|---:|---:|---:|
| dcrnn_residual | 2021 | 0.061907 | 280 |
| dcrnn_residual | 2022 | 0.079266 | 280 |
| dcrnn_residual | 2023 | 0.072520 | 280 |
| dcrnn_residual | 2024 | 0.026137 | 280 |
| dcrnn_residual | 2025 | 0.028817 | 280 |
| dynamic_stgnn_residual | 2021 | 0.061079 | 280 |
| dynamic_stgnn_residual | 2022 | 0.079129 | 280 |
| dynamic_stgnn_residual | 2023 | 0.072559 | 280 |
| dynamic_stgnn_residual | 2024 | 0.026372 | 280 |
| dynamic_stgnn_residual | 2025 | 0.029186 | 280 |
| graph_wavenet_residual | 2021 | 0.163508 | 280 |
| graph_wavenet_residual | 2022 | 0.054292 | 280 |
| graph_wavenet_residual | 2023 | 0.115300 | 280 |
| graph_wavenet_residual | 2024 | 0.044075 | 280 |
| graph_wavenet_residual | 2025 | 0.031243 | 280 |
