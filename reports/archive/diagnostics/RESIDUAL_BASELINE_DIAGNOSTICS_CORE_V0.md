# Residual Baseline Diagnostics Core v0

Data: 2026-04-17

## Objective

Audit whether the residual improvement is broad or concentrated in a few high-volume or high-volatility `ZE2020` zones.

Strategies audited:

- Best fixed no-REI residual after audit: `ridge log / engineered_target / lambda=0.5`.
- Conservative selector: `ridge_level` until two prior test years exist, then prior-best residual model.

## Per-Year Behavior

Best fixed no-REI residual:

| test_year | persistence_wmape | model_wmape | wmape_delta_vs_persistence | abs_error_reduction_sum |
| :--- | :--- | :--- | :--- | :--- |
| 2021 | 14.317 | 8.866 | 5.451 | 60327.890 |
| 2022 | 3.369 | 4.465 | -1.096 | -12264.446 |
| 2023 | 3.566 | 9.284 | -5.718 | -63120.959 |
| 2024 | 9.470 | 3.855 | 5.615 | 68451.322 |

Conservative selector:

| test_year | persistence_wmape | model_wmape | wmape_delta_vs_persistence | abs_error_reduction_sum |
| :--- | :--- | :--- | :--- | :--- |
| 2021 | 14.317 | 6.510 | 7.807 | 86412.132 |
| 2022 | 3.369 | 9.807 | -6.438 | -72050.054 |
| 2023 | 3.566 | 13.189 | -9.623 | -106228.319 |
| 2024 | 9.470 | 8.379 | 1.091 | 13302.143 |

## Volume Stratification

Best fixed no-REI residual:

| volume_group | persistence_wmape | model_wmape | wmape_delta_vs_persistence | actual_sum |
| :--- | :--- | :--- | :--- | :--- |
| bottom_50pct | 8.950 | 7.658 | 1.292 | 600047.000 |
| middle_40pct | 8.519 | 7.601 | 0.918 | 1481562.000 |
| top_10pct | 6.932 | 5.634 | 1.299 | 2467349.000 |

## Volatility Stratification

Best fixed no-REI residual:

| volatility_group | persistence_wmape | model_wmape | wmape_delta_vs_persistence | actual_sum |
| :--- | :--- | :--- | :--- | :--- |
| high_volatility | 7.126 | 6.042 | 1.084 | 3061348.000 |
| low_volatility | 9.533 | 8.052 | 1.481 | 600510.000 |
| medium_volatility | 8.520 | 7.245 | 1.276 | 887100.000 |

## Interpretation

- The fixed residual model improves `2021` and `2024` versus persistence, but worsens `2022` and `2023`.
- The average gain is driven by large improvements in shock/rebound years, especially `2021` and `2024`.
- The fixed residual model improves all volume groups, including the top 10% by pre-test volume.
- The fixed residual model improves all volatility groups, with strongest relative value in high-volatility zones.
- The gain improves `223` zones and worsens `57`, but is concentrated in magnitude: Paris alone contributes `54.4%` of total absolute-error reduction, and the top 10 improving zones contribute `69.1%`.
- The conservative selector still suffers in `2022` because it defaults to `ridge_level` before enough prior test years exist.
- Region-level clustering is not audited here because region metadata is not included in the prediction artifact.

## Decision

REI-backed residuals are excluded here. The best remaining fixed residual is weaker and remains exploratory.

The conservative selector is the more defensible operational protocol, but it still needs more test years or a stronger prior selection rule.

Next step:

- Inspect top improving and worsening zones manually.
- Keep REI banned from candidate baselines until timing/vintage and aggregation issues are resolved.
- Keep `STGNN` postponed.
