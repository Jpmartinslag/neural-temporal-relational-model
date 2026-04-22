# Activation Rule Diagnostics Core v0

> Methodological precedence note: use [METHODOLOGICAL_POSITIONING_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/METHODOLOGICAL_POSITIONING_V0.md) as the current canonical framing. If this report conflicts with it, the methodological positioning document prevails.


Data: 2026-04-20

## Objective

Audit the current best no-REI activation rule as a diagnostic artifact, not as an operational baseline.

Best rule audited:

- Stable side: `ridge_level_lag_only`
- Residual side: `huber_absolute_sitadel_only_lambda_0_5`
- Fallback: `stable`
- Rule: `national_acceleration_abs`
- Min prior years: `1`

## Per-Year Threshold Trace

| test_year | threshold | activation_rate | wmape | reason |
| :--- | :--- | :--- | :--- | :--- |
| 2021 | NA | 0.000 | 6.510 | default_stable_until_1_prior_years |
| 2022 | 0.117 | 1.000 | 5.436 | best_prior_wmape |
| 2023 | 0.117 | 1.000 | 5.900 | best_prior_wmape |
| 2024 | 0.117 | 0.000 | 4.103 | best_prior_wmape |

## Leave-One-Year-Out Threshold Audit

| heldout_year | selected_threshold | train_wmape | heldout_wmape | heldout_activation_rate |
| :--- | :--- | :--- | :--- | :--- |
| 2021 | 0.025 | 5.113 | 9.565 | 1.000 |
| 2022 | 0.117 | 5.458 | 5.436 | 1.000 |
| 2023 | 0.117 | 5.309 | 5.900 | 1.000 |
| 2024 | 0.117 | 5.947 | 4.103 | 0.000 |

Threshold range: `0.0917358232599399`.

## Volume Stratification

| volume_group | rule_wmape | persistence_wmape | stable_wmape | aer_vs_persistence | aer_vs_stable | improved_zones_vs_persistence | worsened_zones_vs_persistence |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| bottom_50pct | 5.639 | 8.950 | 10.804 | 19868.599 | 30994.257 | 128 | 12 |
| middle_40pct | 6.316 | 8.519 | 8.699 | 32638.673 | 35300.957 | 110 | 2 |
| top_10pct | 4.889 | 6.932 | 6.125 | 50423.338 | 30495.003 | 27 | 1 |

## Per-Year Comparison

| test_year | rule_wmape | persistence_wmape | stable_wmape | aer_vs_persistence | aer_vs_stable |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 2021 | 6.510 | 14.317 | 6.510 | 86412.132 | 0.000 |
| 2022 | 5.436 | 3.369 | 9.807 | -23132.468 | 48917.587 |
| 2023 | 5.900 | 3.566 | 10.237 | -25771.474 | 47872.631 |
| 2024 | 4.103 | 9.470 | 4.103 | 65422.420 | 0.000 |

## Concentration Risk

- Positive AER top-1 share vs persistence: `29.428%`
- Positive AER top-10 share vs persistence: `43.015%`

## Decision

- This diagnostic must compare against both persistence and the stable side.
- A future activation rule must show positive AER vs persistence in at least two volume groups.
- A future activation rule must keep Paris/top-zone concentration below the project threshold.
- A future activation rule must have a stable LOYO threshold trace.
- The current `5.49%` activation result remains downgraded to stress-test diagnostic until these criteria are met.
