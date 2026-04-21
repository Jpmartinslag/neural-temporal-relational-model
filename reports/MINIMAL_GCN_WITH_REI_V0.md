# Minimal GCN With REI v0

First heavy structural candidate prepared for an external machine with PyTorch.

- feature_set: `['side_creations_lag_1', 'nb_com', 'rei_cfe_microentrepreneurs_created_n_1_lag_1']`
- hidden_dim: `16`
- epochs: `400`
- mean_delta vs rei_created_baseline: `69.462`
- worsened_years: `[2021, 2022, 2023, 2024]`
- strictly_better_with_tolerance: `False`
- prediction_output: `data/processed/minimal_gcn_with_rei_predictions_v0.csv`
