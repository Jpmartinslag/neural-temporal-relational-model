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
| dcrnn_residual | 0.053663 |
| dynamic_stgnn_residual | 0.053967 |
| graph_wavenet_residual | 0.096046 |

## Per-Year WMAPE

| model | target_year | wmape | n |
|---|---:|---:|---:|
| dcrnn_residual | 2021 | 0.061471 | 280 |
| dcrnn_residual | 2022 | 0.079308 | 280 |
| dcrnn_residual | 2023 | 0.072599 | 280 |
| dcrnn_residual | 2024 | 0.026247 | 280 |
| dcrnn_residual | 2025 | 0.028692 | 280 |
| dynamic_stgnn_residual | 2021 | 0.061172 | 280 |
| dynamic_stgnn_residual | 2022 | 0.078996 | 280 |
| dynamic_stgnn_residual | 2023 | 0.072491 | 280 |
| dynamic_stgnn_residual | 2024 | 0.026123 | 280 |
| dynamic_stgnn_residual | 2025 | 0.031052 | 280 |
| graph_wavenet_residual | 2021 | 0.149119 | 280 |
| graph_wavenet_residual | 2022 | 0.060465 | 280 |
| graph_wavenet_residual | 2023 | 0.117207 | 280 |
| graph_wavenet_residual | 2024 | 0.094144 | 280 |
| graph_wavenet_residual | 2025 | 0.059295 | 280 |
