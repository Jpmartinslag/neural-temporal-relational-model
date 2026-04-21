# Final REI Created Baseline v0

Final operational artifact fitted on all available observed years.

- model: `final_rei_created_baseline_v0`
- feature_set: `['side_creations_lag_1', 'nb_com', 'rei_cfe_microentrepreneurs_created_n_1_lag_1']`
- train_years: `[2018, 2019, 2020, 2021, 2022, 2023, 2024]`
- rows: `1960`
- alpha: `6.158482110660261`
- in_sample_wmape: `5.307`
- artifact_output: `data/processed/final_rei_created_baseline_artifact_v0.json`
- fitted_values_output: `data/processed/final_rei_created_baseline_fitted_values_v0.csv`

| feature | mean | std | coefficient |
| --- | ---: | ---: | ---: |
| side_creations_lag_1 | 3414.303571 | 11550.249757 | 12511.277490 |
| nb_com | 122.807143 | 87.196608 | 11.015025 |
| rei_cfe_microentrepreneurs_created_n_1_lag_1 | 576.836310 | 2730.093949 | -448.820668 |
