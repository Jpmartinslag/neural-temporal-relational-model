# HERALD Phase 3B — Tutor Signal Audit

No model training here. This screens whether available macro signals have enough temporal shape to justify more GPU runs.

## Inputs

- Macro file: `data/processed/phase2h_macro_annual_features_v1.csv`
- Panel file: `data/processed/dynamic_stgnn_feature_panel_phase2h_macro_v1.csv`
- Rule inherited from Phase 2H: `target_year=t` receives annual monthly mean observed in `t-1`.

## Target Shape

| target_year | side_total | side_growth | side_growth_change |
| --- | --- | --- | --- |
| 2018.0000 | 795205.0000 | 0.1317 | 0.0505 |
| 2019.0000 | 915980.0000 | 0.1519 | 0.0201 |
| 2020.0000 | 948339.0000 | 0.0353 | -0.1166 |
| 2021.0000 | 1106794.0000 | 0.1671 | 0.1318 |
| 2022.0000 | 1119168.0000 | 0.0112 | -0.1559 |
| 2023.0000 | 1103907.0000 | -0.0136 | -0.0248 |
| 2024.0000 | 1202669.0000 | 0.0895 | 0.1031 |
| 2025.0000 | 1268677.0000 | 0.0549 | -0.0346 |

## Signal Screen

| signal | n_years | z_2021_vs_train_to_2020 | z_2022_vs_train_to_2020 | shock_signal_strength | rebound_separation | corr_with_side_growth | screening_verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| fr_climat_affaires_t_minus_1 | 13 | -2.0478 | 0.8665 | 2.0478 | 2.9143 | 0.1217 | candidate |
| fr_climat_emploi_t_minus_1 | 13 | -2.8679 | 0.1319 | 2.8679 | 2.9998 | -0.0391 | candidate |
| fr_bdf_conj_services_climate_t_minus_1 | 13 | -2.1733 | 0.1752 | 2.1733 | 2.3485 | 0.0020 | candidate |
| fr_bdf_gstix_comp_t_minus_1 | 13 | 3.9853 | 6.0316 | 3.9853 | 2.0463 | 0.0605 | candidate |

## Reading

- Candidate signals worth training: fr_climat_affaires_t_minus_1, fr_climat_emploi_t_minus_1, fr_bdf_conj_services_climate_t_minus_1, fr_bdf_gstix_comp_t_minus_1.
- Keep permutation falsification mandatory for any next battery.
- Do not advance to cross-attention until a tutor signal beats its permuted control.

