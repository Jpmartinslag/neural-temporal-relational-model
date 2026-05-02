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
| dynamic_stgnn_residual | 0.053522 |
| dcrnn_residual | 0.053690 |
| graph_wavenet_residual | 0.121760 |

## Per-Year WMAPE

| model | target_year | wmape | n |
|---|---:|---:|---:|
| dcrnn_residual | 2021 | 0.061767 | 280 |
| dcrnn_residual | 2022 | 0.079114 | 280 |
| dcrnn_residual | 2023 | 0.072563 | 280 |
| dcrnn_residual | 2024 | 0.026448 | 280 |
| dcrnn_residual | 2025 | 0.028560 | 280 |
| dynamic_stgnn_residual | 2021 | 0.061169 | 280 |
| dynamic_stgnn_residual | 2022 | 0.079021 | 280 |
| dynamic_stgnn_residual | 2023 | 0.072446 | 280 |
| dynamic_stgnn_residual | 2024 | 0.026249 | 280 |
| dynamic_stgnn_residual | 2025 | 0.028726 | 280 |
| graph_wavenet_residual | 2021 | 0.148899 | 280 |
| graph_wavenet_residual | 2022 | 0.158066 | 280 |
| graph_wavenet_residual | 2023 | 0.154972 | 280 |
| graph_wavenet_residual | 2024 | 0.092641 | 280 |
| graph_wavenet_residual | 2025 | 0.054223 | 280 |
